from flask import Blueprint, render_template
import pandas as pd
import plotly.express as px
from utils.db import execute_query
from utils.cache import cache

trend_bp = Blueprint('trend', __name__)


@trend_bp.route('/trend_os')
@cache('trend_os')
def trend_os():
    """OS 트렌드 페이지"""
    sql = """
            SELECT io_os.state AS os
            FROM hli_asset.total_asset ta 
            JOIN hli_asset.info_os io_os ON ta.os = io_os.os
            """
    data = execute_query(sql)

    # 데이터프레임 변환
    columns = [column for column in data[0].keys()] if data else []
    df = pd.DataFrame(data, columns=columns)

    # OS 종류별 자산 수 집계
    os_counts = df['os'].value_counts().reset_index()
    os_counts.columns = ['OS', 'Count']

    # 도넛 그래프 생성
    fig = px.pie(os_counts, values='Count', names='OS', title='OS별 서버수량',
                 hole=0.3)

    graph = fig.to_html(full_html=False)

    return render_template('trend_os.html', graph=graph)


@trend_bp.route('/trend_os_date')
@cache('trend_os_date')
def trend_os_date():
    """OS 트렌드 날짜별 페이지"""
    sql_filtered = """
                SELECT ta.datein,
                       io_os.state AS os
                FROM hli_asset.total_asset ta 
                JOIN hli_asset.info_os io_os ON ta.os = io_os.os
                """
    data = execute_query(sql_filtered)

    # 데이터프레임 변환
    columns = [column for column in data[0].keys()] if data else []
    df = pd.DataFrame(data, columns=columns)

    # 날짜 형식 변환
    df['datein'] = pd.to_datetime(df['datein'])

    # 월별 자산 변화량
    df_grouped = df.groupby([pd.Grouper(key='datein', freq='M'), 'os']).size().reset_index(name='count')
    fig = px.bar(df_grouped, x='datein', y='count', color='os', title='월간 자산 분포',
                 labels={'count': '자산 수량', 'datein': '월'})

    # 월별 데이터 프레임 생성
    all_months = pd.date_range(start=df_grouped['datein'].min(), end=pd.Timestamp.today(), freq='M')
    all_os = df_grouped['os'].unique()

    # 모든 조합 생성
    index = pd.MultiIndex.from_product([all_months, all_os], names=['datein', 'os'])
    df_full = pd.DataFrame(index=index).reset_index()

    # 기존 데이터와 결합
    df_full = df_full.merge(df_grouped, on=['datein', 'os'], how='left').fillna(0)

    # 누적 합계 계산
    df_full['cumulative_count'] = df_full.groupby('os')['count'].cumsum()

    # 그래프 생성
    fig3 = px.bar(df_full, x='datein', y='cumulative_count', color='os',
                  title='월간 누적 자산 분포',
                  labels={'cumulative_count': '자산 수량', 'datein': '월'})

    # 연간 자산 변화량
    df_grouped_yearly = df.groupby([pd.Grouper(key='datein', freq='Y'), 'os']).size().reset_index(name='count')
    fig2 = px.bar(df_grouped_yearly, x='datein', y='count', color='os', title='연간 자산 분포',
                  labels={'count': '자산 수량', 'datein': '연도'})

    # 모든 연도 데이터 프레임 생성
    all_years = pd.date_range(start=df_grouped_yearly['datein'].min(), end=pd.Timestamp.today(), freq='Y')

    # 모든 조합 생성
    index_year = pd.MultiIndex.from_product([all_years, all_os], names=['datein', 'os'])
    df_full_year = pd.DataFrame(index=index_year).reset_index()

    # 기존 데이터와 결합
    df_full_year = df_full_year.merge(df_grouped_yearly, on=['datein', 'os'], how='left').fillna(0)

    # 누적 합계 계산
    df_full_year['cumulative_count'] = df_full_year.groupby('os')['count'].cumsum()

    # 그래프 생성
    fig4 = px.bar(df_full_year, x='datein', y='cumulative_count', color='os',
                  title='연간 누적 자산 분포',
                  labels={'cumulative_count': '자산 수량', 'datein': '연도'})

    # HTML로 그래프 렌더링
    graph1 = fig.to_html(full_html=False)
    graph2 = fig2.to_html(full_html=False)
    graph3 = fig3.to_html(full_html=False)
    graph4 = fig4.to_html(full_html=False)

    return render_template('trend_os_date.html', graph1=graph1, graph2=graph2, graph3=graph3, graph4=graph4)
