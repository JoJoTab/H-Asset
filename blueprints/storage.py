from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, flash
import pandas as pd
import numpy as np
import plotly.express as px
from utils.db import execute_query, get_db_connection
from datetime import datetime
from utils.cache import cache

storage_bp = Blueprint('storage', __name__)


@storage_bp.route('/storage', methods=['GET', 'POST'])
def storage():
    """스토리지 관리 페이지"""
    connection = get_db_connection()
    data1 = {}
    data2 = []
    end_date = None
    start_date = None
    error_message = None
    graph_html_tl = ""
    graph_html_use = ""

    try:
        with connection.cursor() as cursor:
            # 전체 데이터 조회
            sql = "SELECT DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP FROM total_storage"
            cursor.execute(sql)
            result = cursor.fetchall()

            # 가장 최근 날짜 가져오기
            sql_recent_date = """SELECT MAX(DATEIN) AS end_date FROM total_storage"""
            sql_yesterday_date = """SELECT DATE_SUB(MAX(DATEIN), INTERVAL 1 DAY) AS start_date FROM total_storage"""
            cursor.execute(sql_recent_date)
            end_date = cursor.fetchone()['end_date']
            cursor.execute(sql_yesterday_date)
            start_date = cursor.fetchone()['start_date']

            if request.method == 'POST':
                start_date = request.form.get('start_date')
                end_date = request.form.get('end_date')

            # 데이터 조회
            sql_data = """
                        SELECT STORAGE, PID, DATEIN, AV_CAP, TP_CAP, TL_CAP 
                        FROM total_storage 
                        WHERE DATEIN BETWEEN %s AND %s
                        """
            cursor.execute(sql_data, (start_date, end_date))
            date_range_data = cursor.fetchall()

            # 스토리지별로 날짜별 데이터를 저장할 딕셔너리 초기화
            data_for_plot = {}

            for row in date_range_data:
                date = row['DATEIN']
                storage = row['STORAGE']

                # 할당률 및 사용률 계산
                tl_rate = row['TL_CAP'] * 100 / row['TP_CAP'] if row['TP_CAP'] > 0 else 0
                use_rate = (row['TP_CAP'] - row['AV_CAP']) * 100 / row['TL_CAP'] if row['TL_CAP'] > 0 else 0

                # 날짜별로 스토리지 데이터를 누적
                if storage not in data_for_plot:
                    data_for_plot[storage] = {}

                if date not in data_for_plot[storage]:
                    data_for_plot[storage][date] = {
                        'tl_rates': [],
                        'use_rates': []
                    }

                data_for_plot[storage][date]['tl_rates'].append(tl_rate)
                data_for_plot[storage][date]['use_rates'].append(use_rate)

            # 최종 데이터 구조화
            final_data_for_plot = {'dates': [], 'storages': [], 'tl_rates': [], 'use_rates': []}
            for storage, date_data in data_for_plot.items():
                for date, rates in date_data.items():
                    avg_tl_rate = sum(rates['tl_rates']) / len(rates['tl_rates']) if rates['tl_rates'] else 0
                    avg_use_rate = sum(rates['use_rates']) / len(rates['use_rates']) if rates['use_rates'] else 0

                    final_data_for_plot['dates'].append(date)
                    final_data_for_plot['storages'].append(storage)
                    final_data_for_plot['tl_rates'].append(avg_tl_rate)
                    final_data_for_plot['use_rates'].append(avg_use_rate)

            # DataFrame 생성
            df = pd.DataFrame(final_data_for_plot)

            # 할당률 꺾은선 그래프 생성
            fig_tl = px.line(df, x='dates', y='tl_rates', color='storages',
                             labels={'tl_rates': '할당률 (%)', 'dates': '날짜'})

            # 사용률 꺾은선 그래프 생성
            fig_use = px.line(df, x='dates', y='use_rates', color='storages',
                              labels={'use_rates': '사용률 (%)', 'dates': '날짜'})

            # 그래프 HTML 코드로 변환
            graph_html_tl = fig_tl.to_html(full_html=False)
            graph_html_use = fig_use.to_html(full_html=False)

            if not date_range_data:
                # 시작 날짜와 종료 날짜의 데이터 유무 검사
                sql_check_data = """SELECT DATEIN FROM total_storage WHERE DATEIN IN (%s, %s)"""
                cursor.execute(sql_check_data, (start_date, end_date))
                existing_dates = {row['DATEIN'] for row in cursor.fetchall()}

                if end_date not in existing_dates:
                    error_message = '종료 날짜에 데이터가 없습니다.'
            else:
                # 데이터 비교 로직
                filtered_data = [row for row in date_range_data if row['DATEIN'].strftime('%Y-%m-%d') == end_date]
                for recent in filtered_data:
                    storage = recent['STORAGE']
                    pid = recent['PID']
                    if storage not in data1:
                        data1[storage] = {}

                    data1[storage][pid] = {
                        'AV_CAP': recent['AV_CAP'] / 1024 / 1024,  # TB로 변환
                        'TP_CAP': recent['TP_CAP'] / 1024 / 1024,
                        'TL_CAP': recent['TL_CAP'] / 1024 / 1024,
                        'AV_CAP_diff': None,  # 초기화
                        'TP_CAP_diff': None,
                        'TL_CAP_diff': None,
                        'TL_RATE': recent['TL_CAP'] * 100 / recent['TP_CAP'] if recent['TP_CAP'] > 0 else 0,
                        'USE_RATE': (recent['TP_CAP'] - recent['AV_CAP']) * 100 / recent['TL_CAP'] if recent[
                                                                                                          'TL_CAP'] > 0 else 0
                    }
                filtered_data = [row for row in date_range_data if row['DATEIN'].strftime('%Y-%m-%d') == start_date]
                for yesterday in filtered_data:
                    storage = yesterday['STORAGE']
                    pid = yesterday['PID']
                    if storage in data1 and pid in data1[storage]:
                        # 차이 계산
                        diff = round(data1[storage][pid]['AV_CAP'] - (yesterday['AV_CAP'] / 1024 / 1024), 2)
                        data1[storage][pid]['AV_CAP_diff'] = f"({diff:+})"  # 차이를 포맷팅
                        diff = round(data1[storage][pid]['TP_CAP'] - (yesterday['TP_CAP'] / 1024 / 1024), 2)
                        data1[storage][pid]['TP_CAP_diff'] = f"({diff:+})"  # 차이를 포맷팅
                        diff = round(data1[storage][pid]['TL_CAP'] - (yesterday['TL_CAP'] / 1024 / 1024), 2)
                        data1[storage][pid]['TL_CAP_diff'] = f"({diff:+})"  # 차이를 포맷팅

            # MB를 TB로 변환하여 결과에 추가
            for row in result:
                row['AV_CAP'] = round(row['AV_CAP'] / 1024 / 1024, 2)  # TB 단위로 변환
                row['TP_CAP'] = round(row['TP_CAP'] / 1024 / 1024, 2)
                row['TL_CAP'] = round(row['TL_CAP'] / 1024 / 1024, 2)
                data2.append(row)

    finally:
        connection.close()

    return render_template('storage.html', data1=data1, data2=data2, latest_date=end_date,
                           start_date=start_date, end_date=end_date, error_message=error_message,
                           graph_html_tl=graph_html_tl, graph_html_use=graph_html_use)


@storage_bp.route('/storage_upload', methods=['POST'])
def storage_upload():
    """스토리지 데이터 업로드 처리"""
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    content = file.read().decode('utf-8').splitlines()
    date = content[0].strip()  # 첫 번째 줄에서 날짜 추출
    storage_type = None

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            for line in content[1:]:
                line = line.strip()
                if line.startswith("VSP") or line.startswith("F800") or line.startswith("DR_"):  # 스토리지 종류 확인
                    storage_type = line  # 스토리지 종류 저장
                elif line.startswith("PID"):
                    continue  # 헤더는 무시
                elif line and storage_type:  # 데이터 줄 처리
                    data = line.split()
                    if len(data) > 10:  # 유효한 데이터인지 확인
                        pid = data[0]
                        av_cap = data[3]
                        tp_cap = data[4]
                        tl_cap = data[10]

                        # 데이터 삽입
                        sql = "INSERT INTO total_storage (DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP) VALUES (%s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, (date, storage_type, pid, av_cap, tp_cap, tl_cap))

            connection.commit()
    finally:
        connection.close()

    # 성공적으로 처리된 후 적절한 응답을 반환
    return redirect(url_for('storage.storage'))
