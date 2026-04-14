from flask import Flask, render_template, redirect, url_for, request, send_file, jsonify, session, flash
# from flask_ckeditor import CKEditor
import pandas as pd
import numpy as np
import openpyxl
import plotly.express as px
import os
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired

from config import Config
from blueprints.asset import asset_bp
from blueprints.storage import storage_bp
from blueprints.rack import rack_bp
from blueprints.file import file_bp
from blueprints.trend import trend_bp
from blueprints.service import service_bp
from blueprints.database import database_bp
from blueprints.backup import backup_bp, setup_auto_backup_history
from blueprints.vmware import vmware_bp
from blueprints.firewall import firewall_bp

from utils.db import (
    init_db_pool, close_db_pool,
    get_all_storage, get_storage_latest_dates, get_storage_by_date_range,
    check_storage_dates, insert_storage_row,
    get_all_assets,
    get_asset_os_list, get_asset_os_with_date,
    get_distinct_loc1, get_rack_info_by_locs, upsert_rack_info,
    get_physical_asset_locs, get_all_rack_info, get_rack_assets,
    get_locations_by_floor_column, get_columns_by_floor,
    insert_assets_bulk, insert_rv_assets_bulk,
    get_assets_with_info, get_assets_for_graph,
    get_info_options, get_asset_with_options,
    lookup_info_code, insert_asset, update_asset, delete_asset,
)
from utils.auto_register import setup_auto_register
from utils.auto_storage import setup_auto_storage

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config.from_object(Config)
app.secret_key = 'your_secret_key_here'  # 세션을 위한 시크릿 키 설정

# CKEditor 초기화
# ckeditor = CKEditor(app)
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_HEIGHT'] = 400
app.config['CKEDITOR_FILE_UPLOADER'] = 'service.upload_image'  # 이미지 업로드 라우트

# 블루프린트 등록
app.register_blueprint(asset_bp, url_prefix='/')
app.register_blueprint(trend_bp)
app.register_blueprint(rack_bp)
app.register_blueprint(file_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(service_bp, url_prefix='/service')
app.register_blueprint(database_bp, url_prefix='/database')
app.register_blueprint(backup_bp, ur_plrefix='/backup')
app.register_blueprint(vmware_bp, url_prefix='/vmware')
app.register_blueprint(firewall_bp, url_prefix='/firewall')

setup_auto_register()
setup_auto_storage()
setup_auto_backup_history()

# 비동기 함수 호출 제거
@app.before_first_request
def setup():
    init_db_pool()
    from utils.firewall_collector import start_scheduler
    start_scheduler()
    print("애플리케이션 초기화 완료")

@app.teardown_appcontext
def teardown(exception):
    # 비동기 함수를 동기 함수로 변경
    close_db_pool()

@app.route('/')
@app.route('/index')
def main_index():
    # 비동기 함수를 직접 호출하지 않고 동기 버전의 함수 호출
    return redirect(url_for('asset.index'))


def get_data():
    data = get_all_assets()
    df = pd.DataFrame(data)

    # 날짜 형식 변환 (오류를 피하기 위해 errors='coerce' 사용)
    df['datein'] = pd.to_datetime(df['datein'], errors='coerce')

    # 개수 계산
    total_assets = df[df['isoper'].isin([0, 1, 2])]
    total_servers = df[total_assets['domain'] == 0]
    print(len(total_servers), len(df), len(total_servers['isvm']))
    physical_servers = df[total_servers['isvm'] == 0]
    virtual_servers = df[total_servers['isvm'] == 1]
    current_year_assets = df[pd.to_datetime(total_assets['datein']).dt.year == pd.to_datetime('now').year]
    current_month_assets = df[pd.to_datetime(total_assets['datein']).dt.month == pd.to_datetime('now').month]
    oper_assets = df[total_servers['oper'] == 0]
    qa_assets = df[total_servers['oper'] == 1]
    dev_assets = df[total_servers['oper'] == 2]
    dr_assets = df[total_servers['oper'] == 4]
    current_year = pd.to_datetime('now').year
    current_month = pd.to_datetime('now').month

    return {
        "total_assets": total_assets.shape[0],
        "total_servers": total_servers.shape[0],
        "physical_servers": physical_servers.shape[0],
        "virtual_servers": virtual_servers.shape[0],
        "current_year_assets": current_year_assets.shape[0],
        "current_month_assets": current_month_assets.shape[0],
        "oper_assets": oper_assets.shape[0],
        "qa_assets": qa_assets.shape[0],
        "dev_assets": dev_assets.shape[0],
        "dr_assets": dr_assets.shape[0],
        "current_year": current_year,
        "current_month": current_month
    }


@app.route('/storage', methods=['GET', 'POST'])
def storage():
    data1 = {}
    data2 = []
    error_message = None
    graph_html_tl = ''
    graph_html_use = ''

    result = get_all_storage()
    end_date, start_date = get_storage_latest_dates()

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

    print(start_date, end_date)

    date_range_data = get_storage_by_date_range(start_date, end_date)
    date_range_data = get_storage_by_date_range(start_date, end_date)

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
        existing_dates = {row['DATEIN'] for row in check_storage_dates(start_date, end_date)}

        # if start_date not in existing_dates:
        #     error_message = '시작 날짜에 데이터가 없습니다.'
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
                'USE_RATE': (recent['TP_CAP'] - recent['AV_CAP']) * 100 / recent['TL_CAP'] if recent['TL_CAP'] > 0 else 0
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

    return render_template('storage.html', data1=data1, data2=data2, latest_date=end_date,
                           start_date=start_date, end_date=end_date, error_message=error_message,
                           graph_html_tl=graph_html_tl, graph_html_use=graph_html_use)


@app.route('/storage_upload', methods=['POST'])
def storage_upload():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    content = file.read().decode('utf-8').splitlines()
    date = content[0].strip()  # 첫 번째 줄에서 날짜 추출
    storage_type = None

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
                insert_storage_row(date, storage_type, pid, av_cap, tp_cap, tl_cap)

    print(date, storage_type, pid, av_cap, tp_cap, tl_cap)

    # 성공적으로 처리된 후 적절한 응답을 반환
    return redirect(url_for('storage'))

@app.route('/trend_os')
def trend_os():
    data = get_asset_os_list()
    df = pd.DataFrame(data)

    # OS 종류별 자산 수 집계
    os_counts = df['os'].value_counts().reset_index()
    os_counts.columns = ['OS', 'Count']

    # 도넛 그래프 생성
    fig = px.pie(os_counts, values='Count', names='OS', title='OS별 서버수량',
                 hole=0.3)

    graph = fig.to_html(full_html=False)

    return render_template('trend_os.html', graph=graph)

@app.route('/trend_os_date')
def trend_os_date():
    data = get_asset_os_with_date()
    df = pd.DataFrame(data)

    # 날짜 형식 변환
    df['datein'] = pd.to_datetime(df['datein'])

    # 월별 자산 변화량
    df_grouped = df.groupby([pd.Grouper(key='datein', freq='ME'), 'os']).size().reset_index(name='count')
    fig = px.bar(df_grouped, x='datein', y='count', color='os', title='월간 자산 분포',
                 labels={'count': '자산 수량', 'datein': '월'})

    # 월별 데이터 프레임 생성
    all_months = pd.date_range(start=df_grouped['datein'].min(), end=pd.Timestamp.today(), freq='ME')
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
    df_grouped_yearly = df.groupby([pd.Grouper(key='datein', freq='YE'), 'os']).size().reset_index(name='count')
    fig2 = px.bar(df_grouped_yearly, x='datein', y='count', color='os', title='연간 자산 분포',
                 labels={'count': '자산 수량', 'datein': '연도'})

    # 모든 연도 데이터 프레임 생성
    all_years = pd.date_range(start=df_grouped_yearly['datein'].min(), end=pd.Timestamp.today(), freq='YE')

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


@app.route('/racklayout_edit', methods=['GET', 'POST'])
def racklayout_edit():
    if request.method == 'POST':
        loc = request.form.get('update')  # 수정 버튼을 통해 전달된 loc 값
        if loc:
            rackname = request.form.get(f'rackname_{loc}', '')
            rackenable = int(request.form.get(f'rackenable_{loc}', 1))
            upsert_rack_info(loc, rackname, rackenable)

    # loc1 정보 조회
    loc_data = get_distinct_loc1()
    loc_list = sorted([row['loc1'] for row in loc_data if row['loc1'] is not None])

    current_data = get_rack_info_by_locs(loc_list)

    # 데이터 사전 생성
    current_dict = {row['loc']: (row['rackname'], row['rackenable']) for row in current_data}

    return render_template('racklayout_edit.html', loc_list=loc_list, current_dict=current_dict)


@app.route('/racklayout', methods=['GET'])
def racklayout():
    data = get_physical_asset_locs()
    df = pd.DataFrame(data, columns=['loc1'])
    df = df.dropna(subset=['loc1'])

    df['loc1'] = df['loc1'].apply(lambda x: x[:-4] + x[-3:-2] + '-' + x[-2:])

    floors = set()
    floor_columns = {}

    for loc in df['loc1']:
        parts = loc.split('-')
        if len(parts) < 3:
            continue  # 형식이 올바르지 않으면 건너뜀

        floor = parts[0]
        column = parts[1]  # R01, L01 등

        floors.add(floor)
        if floor not in floor_columns:
            floor_columns[floor] = set()
        floor_columns[floor].add(column)

    # 랙 정보 가져오기
    rack_info_data = get_all_rack_info()
    df_rack = pd.DataFrame(rack_info_data)
    df_rack['loc'] = df_rack['loc'].apply(lambda x: x[:-4] + x[-3:-2] + '-' + x[-2:])
    rack_info_dict = {row['loc']: (row['rackname'], row['rackenable']) for index, row in df_rack.iterrows()}

    # 클릭 가능한 슬롯 생성
    equipment_data = {}
    for floor in floors:
        for column in floor_columns[floor]:
            for loc in range(0, 16):  # 00~15 (0부터 시작)
                loc_string = '{0:02d}'.format(loc)
                loc_key = "{}-{}-{}".format(floor, column, loc_string)
                equipment_data[loc_key] = loc_key in df['loc1'].values
        if floor in floor_columns:
            # R과 L로 분리
            r_items = [item for item in floor_columns[floor] if item.endswith('R')]
            l_items = [item for item in floor_columns[floor] if item.endswith('L')]

            # R과 L 각각 정렬
            r_items.sort(key=lambda x: (int(x[:-1]), x))  # 숫자 오름차순 정렬
            l_items.sort(key=lambda x: (int(x[:-1]), x))  # 숫자 오름차순 정렬

            sorted_items = r_items + l_items
            floor_columns[floor] = sorted_items
    return render_template('racklayout.html', equipment_data=equipment_data, floors=sorted(floors),
                           floor_columns=floor_columns, rack_info_dict=rack_info_dict)


@app.route('/rack_export', methods=['GET', 'POST'])
def rack_export():
    # 현재 테이블 데이터 가져오기
    data = get_rack_assets()
    df = pd.DataFrame(data)

    # loc1의 값이 없는 행 제거
    df = df.dropna(subset=['loc1'])

    selected_floor = request.form.get('floor')
    selected_column = request.form.get('column')
    selected_location = request.form.get('location')

    filtered_df = df[df['loc1'] == f"{selected_floor}-{selected_column}-{selected_location}"]
    filtered_df = filtered_df[['loc2', 'model', 'servername', 'charge', 'usize']]

    # loc2 범위 설정
    loc2_range = range(1, 43)

    # 현재 loc2 값
    existing_loc2 = filtered_df['loc2'].unique()

    # 추가할 데이터프레임 생성
    new_rows = []

    # loc2가 없는 값에 대한 데이터 추가
    for loc2 in loc2_range:
        if loc2 not in existing_loc2:
            # loc2에 해당하는 데이터 추가
            new_row = {'loc2': loc2, 'model': '', 'servername': '', 'charge': '', 'usize': ''}
            new_rows.append(new_row)

    # 새로운 행들을 데이터프레임으로 변환
    new_rows_df = pd.DataFrame(new_rows)

    # 기존 데이터프레임과 새로운 행들을 결합
    filtered_df = pd.concat([filtered_df, new_rows_df], ignore_index=True)

    # loc2 기준으로 내림차순 정렬
    filtered_df.sort_values(by='loc2', ascending=False, inplace=True)
    filtered_df.reset_index(drop=True, inplace=True)

    template_path = 'static/excel/template_rack.xlsx'
    # 엑셀 템플릿 파일 열기
    workbook = openpyxl.load_workbook(template_path)
    sheet = workbook.active  # 기본 시트 선택

    # 데이터 삽입 시작 위치 설정
    start_row = 4
    start_col = 2

    sheet.cell(row=2, column=2).value = f"{selected_floor}-{selected_column}-{selected_location}"

    # 데이터 삽입
    for loc2 in filtered_df['loc2'].unique():  # loc2의 고유 값으로 반복
        rows = filtered_df[filtered_df['loc2'] == loc2]  # loc2에 해당하는 모든 행 선택

        for i, row in rows.iterrows():  # 각 행을 반복
            for j, col in enumerate(filtered_df.columns):  # 열 인덱스 사용
                if j == 0: continue
                cell = sheet.cell(row=start_row + loc2, column=start_col + j)

                # 기존 값이 있을 경우 개행하여 추가
                if cell.value:
                    # cell.value가 int인 경우 문자열로 변환
                    if isinstance(cell.value, int):
                        cell.value = str(cell.value)
                    cell.value += f"\n{row[col]}"  # 여기서 row[col]을 추가
                else:
                    cell.value = row[col]  # 첫 번째 값 설정

    # 셀의 높이를 자동 조정하기 위해 개행 설정
    for row in sheet.iter_rows(min_row=start_row, max_row=start_row + len(filtered_df) - 1, min_col=start_col,
                               max_col=start_col + len(filtered_df.columns) - 1):
        for cell in row:
            cell.alignment = openpyxl.styles.Alignment(wrap_text=True)

    # 변경된 엑셀 파일 저장
    output_path = 'output.xlsx'
    workbook.save(output_path)

    return send_file(output_path, as_attachment=True)


@app.route('/rackview', methods=['GET', 'POST'])
def rackview():
    data = get_rack_assets()
    df = pd.DataFrame(data)

    # loc1의 값이 없는 행 제거
    df = df.dropna(subset=['loc1'])

    # loc 컬럼에서 층, 열, 위치 추출
    floors = set()
    columns_set = set()
    locations = set()

    for loc in df['loc1']:
        try:
            floor, column, location = loc.split('-')
            floors.add(floor)
            columns_set.add(column)
            locations.add(location)
        except ValueError:
            continue

    arg_floor = request.args.get('floor')
    arg_column = request.args.get('column')
    arg_location = request.args.get('location')

    if request.method == 'POST':
        selected_floor = request.form.get('floor')
        selected_column = request.form.get('column')
        selected_location = request.form.get('location')

        # loc 필터링
        filtered_df = df[df['loc1'] == f"{selected_floor}-{selected_column}-{selected_location}"]

        # 결과 저장할 리스트
        result_df = pd.DataFrame()

        # 상단번호 42부터 1까지 반복
        idx = 42
        while idx > 0:
            loc2_rows = filtered_df[filtered_df['loc2'] == idx]
            if not loc2_rows.empty:
                # 중복된 모델명, 서버명, 담당자 수집
                model_names = loc2_rows['model'].dropna().unique().tolist()  # None 값 제거
                server_names = loc2_rows['servername'].dropna().unique().tolist()  # None 값 제거
                charges = loc2_rows['charge'].dropna().unique().tolist()  # None 값 제거
                maker_names = loc2_rows['maker'].dropna().unique().tolist()  # None 값 제거

                # 각 정보 합치기
                maker_combined = ' | '.join(filter(None, maker_names))  # None 값 필터링
                model_combined = ' | '.join(filter(None, model_names))  # None 값 필터링
                server_combined = ' | '.join(filter(None, server_names))  # None 값 필터링
                charge_combined = ' | '.join(filter(None, charges))  # None 값 필터링

                # usize로 병합할 행 수 결정
                usize = int(loc2_rows['usize'].max())
                result_df[idx] = dict(maker=maker_combined, model=model_combined,
                                                  servername=server_combined, charge=charge_combined, usize=usize)
                idx -= usize - 1
            else:
                result_df[idx] = dict(maker='', model='', servername='', charge='', usize=1)
            idx -= 1

        temp_result = []
        for idx in result_df.columns:
            temp_result.append({'loc2': idx, 'maker': result_df[idx].maker, 'model': result_df[idx].model,
                                'servername': result_df[idx].servername, 'charge': result_df[idx].charge,
                                'usize': result_df[idx].usize})

        return jsonify(temp_result)

    # 상면번호 내림차순 정렬
    equipment_data = [{'id': i, 'name': '', 'owner': ''} for i in range(42, 0, -1)]

    # 모든 값이 존재하는지 확인
    if arg_floor and arg_column and arg_location:
        return render_template('rack.html',
                               equipment_data=equipment_data,
                               floors=list(floors),
                               columns=list(columns_set),
                               locations=list(locations),
                               selected_floor=arg_floor,
                               selected_column=arg_column,
                               selected_location=arg_location,
                               auto_fetch=True)

    return render_template('rack.html',
                           equipment_data=equipment_data,
                           floors=list(floors),
                           columns=list(columns_set),
                           locations=list(locations))

@app.route('/get_locations', methods=['GET'])
def get_locations():
    floor = request.args.get('floor')
    column = request.args.get('column')

    data = get_locations_by_floor_column(floor, column)

    # loc1에서 위치만 추출
    locations = set(loc['loc1'].split('-')[2] for loc in data)

    return jsonify(sorted(list(locations)))

@app.route('/get_columns', methods=['GET'])
def get_columns():
    floor = request.args.get('floor')

    data = get_columns_by_floor(floor)

    # loc1에서 column만 추출
    columns = set(loc['loc1'].split('-')[1] for loc in data)

    return jsonify(sorted(list(columns)))


class FileForm(FlaskForm):    # 파일 유효성 검사하는 폼 클래스 생성
    files = FileField(validators=[FileRequired('업로드할 파일을 넣어주세요')])

def stamp2real(stamp):
    return datetime.fromtimestamp(stamp)

def info(filename):
    ctime = os.path.getctime(filename) # 만든시간
    mtime = os.path.getmtime(filename) # 수정시간
    size = os.path.getsize(filename) # 파일크기 (단위: bytes)
    return ctime, mtime, size

@app.errorhandler(404) # 404에러 처리
def page_not_found(error):
     return render_template('deny.html', pwd=os.getcwd() + "\\uploads"), 40


@app.route('/fileindex', methods=['GET', 'POST'])
def fileindex():
    form = FileForm()  # 파일 유효성 폼 클래스 인스턴스 생성
    current_path = request.args.get('path', './uploads')

    # 상위 디렉토리 경로 계산
    parent_path = os.path.dirname(current_path)

    if form.validate_on_submit():  # 양식 유효성 검사 + POST인 경우
        f = form.files.data
        f.save(os.path.join(current_path, f.filename))  # 파일 업로드
        return redirect(f'/fileindex?path={current_path}')

    # 새 폴더 생성
    if request.method == 'POST' and 'create_folder' in request.form:
        folder_name = request.form['folder_name']
        os.makedirs(os.path.join(current_path, folder_name), exist_ok=True)
        return redirect(f'/fileindex?path={current_path}')

    # 폴더 삭제 처리
    if request.method == 'POST' and 'delete_folder' in request.form:
        folder_name = request.form['folder_name']
        folder_path = os.path.join(current_path, folder_name)
        if os.path.isdir(folder_path):
            os.rmdir(folder_path)  # 폴더 삭제
            flash(f'폴더 "{folder_name}"가 삭제되었습니다.', 'success')
        else:
            flash(f'폴더 "{folder_name}"가 존재하지 않습니다.', 'error')
        return redirect(f'/fileindex?path={current_path}')

    filelist = os.listdir(current_path)  # 파일 리스트 가져오기
    infos = []
    for name in filelist:
        fileinfo = {}
        full_path = os.path.join(current_path, name)
        ctime = os.path.getctime(full_path)
        mtime = os.path.getmtime(full_path)

        if os.path.isdir(full_path):  # 디렉토리인지 확인
            fileinfo["name"] = name
            fileinfo["create"] = datetime.fromtimestamp(ctime)
            fileinfo["modify"] = datetime.fromtimestamp(mtime)
            fileinfo["size"] = "폴더"
            fileinfo["isfile"] = False
        else:
            size = os.path.getsize(full_path)
            fileinfo["name"] = name
            fileinfo["create"] = datetime.fromtimestamp(ctime)
            fileinfo["modify"] = datetime.fromtimestamp(mtime)
            fileinfo["isfile"] = True
            if size <= 1000000:
                fileinfo["size"] = "%.2f KB" % (size / 1024)
            else:
                fileinfo["size"] = "%.2f MB" % (size / (1024.0 * 1024.0))
        infos.append(fileinfo)  # 각 파일 정보를 모두 리스트로 입력

    return render_template('fileindex.html', form=form,
                           pwd=current_path, parent_path=parent_path, infos=infos)


@app.route('/down/<path:filename>')
def down_page(filename):
    return send_file(os.path.join(app.root_path, 'uploads', filename), as_attachment=True)

@app.route('/del/<path:filename>')
def delete_page(filename):
    os.remove(os.path.join('uploads', filename))  # 파일 삭제
    return redirect('/fileindex')  # 루트 페이지로 이동

@app.route('/export')
def export_asset():
    data = get_all_assets()
    df = pd.DataFrame(data)

    # 엑셀 파일로 저장
    today = datetime.now().strftime('%Y%m%d')
    export_filename = f'asset_{today}.xlsx'
    export_filepath = os.path.join(app.root_path, 'exports', export_filename)

    # exports 폴더가 없으면 생성
    if not os.path.exists(os.path.dirname(export_filepath)):
        os.makedirs(os.path.dirname(export_filepath))

    df.to_excel(export_filepath, index=False)

    # 파일을 사용자에게 전송
    return send_file(export_filepath, as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    # 업로드 폴더 경로 설정
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

    # uploads 폴더가 없으면 생성
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and file.filename.endswith('.xlsx'):
        # 파일 저장
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # 엑셀 파일 읽기
        df = pd.read_excel(filepath)
        df = df.replace({np.nan: None})

        # 유효성 검사 결과 저장
        invalid_rows = []

        for index, row in df.iterrows():
            try:
                df['isvm'] = df['isvm'].astype(int)
                df['isoper'] = df['isoper'].astype(int)
                df['oper'] = df['oper'].astype(int)
                df['power'] = df['power'].astype(int)
                df['power'] = df['domain'].astype(int)
            except (ValueError, TypeError):
                invalid_rows.append(index + 1)  # 변환 실패 시 유효하지 않은 행으로 간주
                print(ValueError, TypeError)
                continue

        # 모든 데이터가 유효할 경우 삽입
        valid_data = []
        for index, row in df.iterrows():
            valid_data.append((row['itamnum'], row['servername'], row['ip'],
                               row['hostname'], row['center'], row['loc1'],
                               row['loc2'], row['isvm'], row['vcenter'],
                               row['datein'], row['dateout'], row['charge'],
                               row['charge2'], row['isoper'], row['oper'],
                               row['power'], row['pdu'], row['os'], row['osver'],
                               row['maker'], row['model'], row['serial'], row['domain'], ['charge3']))

        insert_assets_bulk(valid_data)

        return redirect(url_for('index'))

    return redirect(request.url)


@app.route('/upload_rv', methods=['POST'])
def upload_rv_file():
    # 업로드 폴더 경로 설정
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

    # uploads 폴더가 없으면 생성
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and file.filename.endswith('.xlsx'):
        # 파일 저장
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # 엑셀 파일 읽기
        df = pd.read_excel(filepath)
        df = df.replace({np.nan: None})

        # 필요한 칼럼으로 필터링하여 새로운 데이터프레임 생성
        filter_df = df[['VM', 'CPUs', 'Memory', 'Primary IP Address', 'Annotation', 'Datacenter', 'Cluster', 'Host',
                        'OS according to the VMware Tools']].copy()

        # 칼럼 이름 변경
        filter_df.columns = ['hostname', 'cpu', 'memory', 'ip', 'servername', 'center', 'Cluster', 'Host', 'os']

        print(filter_df)

        # 유효성 검사 결과 저장
        invalid_rows = []

        for index, row in filter_df.iterrows():
            try:
                filter_df['cpu'] = filter_df['cpu'].astype(int)
            except (ValueError, TypeError):
                invalid_rows.append(index + 1)  # 변환 실패 시 유효하지 않은 행으로 간주
                print(ValueError, TypeError)
                continue

        # 모든 데이터가 유효할 경우 삽입
        valid_data = []
        for index, row in filter_df.iterrows():
            valid_data.append((row['servername'], row['ip'],
                               row['hostname'], row['center'], 1, row['Cluster'] + " " + row['Host'],
                               1, 1, row['os'], '서버', row['cpu'], row['memory']))

        insert_rv_assets_bulk(valid_data)

        return redirect(url_for('index'))

    return redirect(request.url)

@app.route('/index_detail', methods=['GET', 'POST'])
def index_detail():
    selected_columns = request.form.getlist('columns') if request.method == 'POST' else None

    if request.method == 'POST':
        filters = {
            'itamnum':   request.form.get('itamnum') or None,
            'servername': request.form.get('servername') or None,
            'ip':        request.form.get('ip') or None,
            'hostname':  request.form.get('hostname') or None,
            'center':    request.form.get('center') or None,
            'loc1':      request.form.get('loc1') or None,
            'loc2':      request.form.get('loc2', None, type=int),
            'isvm':      request.form.get('isvm', None, type=int),
            'vcenter':   request.form.get('vcenter', None, type=int),
            'datein':    request.form.get('datein') or None,
            'dateout':   request.form.get('dateout') or None,
            'charge':    request.form.get('charge') or None,
            'charge2':   request.form.get('charge2') or None,
            'isoper':    request.form.get('isoper', None, type=int),
            'oper':      request.form.get('oper', None, type=int),
            'power':     request.form.get('power', None, type=int),
            'pdu':       request.form.get('pdu') or None,
            'os':        request.form.get('os') or None,
            'osver':     request.form.get('osver') or None,
            'maker':     request.form.get('maker') or None,
            'model':     request.form.get('model') or None,
            'serial':    request.form.get('serial') or None,
            'domain':    request.form.get('domain') or None,
            'charge3':   request.form.get('charge3') or None,
        }
        data = get_assets_with_info(filters)
        return render_template('index_detail.html', data=data, selected_columns=selected_columns)

    # GET 요청 시 전체 자산 조회
    data = get_assets_with_info()
    return render_template('index_detail.html', data=data, selected_columns=None)


@app.route('/')
@app.route('/index')
def index():
    # 오늘 날짜와 6개월 전 날짜 계산
    end_date = datetime.now()

    data_graph = get_assets_for_graph()
    df_graph = pd.DataFrame(data_graph)

    # 데이터 변환 및 집계
    df_graph['datein'] = pd.to_datetime(df_graph['datein'])
    df_graph['dateout'] = pd.to_datetime(df_graph['dateout'])

    # 월 단위로 집계
    df_graph['month'] = df_graph['datein'].dt.to_period('M').astype(str)

    # 각 월별 설치 및 폐기 자산 수 집계
    monthly_data = df_graph.groupby('month').agg(
        installed=('os_state', 'size'),  # 설치된 자산 수
        discarded=('dateout', lambda x: x.notnull().sum())  # 폐기된 자산 수
    ).reset_index()

    # 누적 계산
    monthly_data['cumulative_installed'] = monthly_data['installed'].cumsum()
    monthly_data['cumulative_discarded'] = monthly_data['discarded'].cumsum()

    # 총 자산 수 계산
    monthly_data['total_assets'] = monthly_data['cumulative_installed'] - monthly_data['cumulative_discarded']

    # 각 월의 OS 종류 및 state 정보 집계
    df_graph['label'] = df_graph.apply(lambda row: row['os_state'] if row['domain_state'] == '서버' else row['domain_state'], axis=1)
    monthly_counts = df_graph.groupby(['month', 'label']).size().unstack(fill_value=0)

    # 누적 자산 수를 포함한 데이터프레임 생성
    monthly_counts = monthly_counts.reindex(monthly_data['month'], fill_value=0)
    cumulative_counts = monthly_counts.cumsum()

    # x축을 6개로 제한
    cumulative_counts = cumulative_counts.tail(6)
    monthly_data = monthly_data.tail(6)

    fig = px.bar(cumulative_counts, title='전체자산변동', barmode='stack',
                 labels={'value': '개수', 'month': '월'})

    # 누적 총 자산 표시
    fig.add_trace(px.line(monthly_data, x='month', y='total_assets', line_shape='linear').data[0])

    graph = fig.to_html(full_html=False)

    data_card = get_data()

    return render_template('index.html', data_card=data_card, data=data_graph, graph=graph)

@app.route('/write')
def write_asset():
    isoper_options, oper_options, power_options, os_options, domain_options = get_info_options()
    print(isoper_options, oper_options, power_options, os_options, domain_options)
    return render_template('write.html',
                           isoper_options=isoper_options,
                           oper_options=oper_options,
                           power_options=power_options,
                           os_options=os_options,
                           domain_options=domain_options)


@app.route('/add', methods=['POST'])
def add_asset():
    itamnum = request.form.get('itamnum')
    servername = request.form.get('servername')
    ip = request.form.get('ip')
    hostname = request.form.get('hostname')
    center = request.form.get('center')
    loc1 = request.form.get('loc1')
    loc2 = request.form.get('loc2', type=int)
    isvm = request.form.get('isvm', type=int)
    vcenter = request.form.get('vcenter', type=int)
    datein = request.form.get('datein')
    dateout = request.form.get('dateout')
    charge = request.form.get('charge')
    charge2 = request.form.get('charge2')
    isoper = request.form.get('isoper')
    oper = request.form.get('oper')
    power = request.form.get('power')
    pdu = request.form.get('pdu')
    os = request.form.get('os')
    osver = request.form.get('osver')
    maker = request.form.get('maker')
    model = request.form.get('model')
    serial = request.form.get('serial')
    domain = request.form.get('domain')
    charge3 = request.form.get('charge3')

    # 날짜 형식 검사 및 변환
    try:
        datein = datetime.strptime(datein, '%Y-%m-%d').date()
    except ValueError:
        datein = None  # 오류 발생 시 None으로 설정

    try:
        dateout = datetime.strptime(dateout, '%Y-%m-%d').date()
    except ValueError:
        dateout = None  # 오류 발생 시 None으로 설정

    # state → 코드 변환
    isoper = lookup_info_code('info_isoper', 'isoper', isoper) or 0
    oper   = lookup_info_code('info_oper',   'oper',   oper)   or 0
    power  = lookup_info_code('info_power',  'power',  power)  or 0
    os     = lookup_info_code('info_os',     'os',     os)     or 0
    domain = lookup_info_code('info_domain', 'domain', domain) or 0

    insert_asset((itamnum, servername, ip, hostname, center, loc1, loc2,
                  isvm, vcenter, datein, dateout, charge, charge2,
                  isoper, oper, power, pdu, os, osver, maker, model, serial, domain, charge3))

    return redirect(url_for('index'))

@app.route('/edit/<int:pnum>', methods=['GET', 'POST'])
def edit_asset(pnum):
    if request.method == 'POST':
        # 폼 데이터 가져오기
        itamnum = request.form.get('itamnum')
        servername = request.form.get('servername')
        ip = request.form.get('ip')
        hostname = request.form.get('hostname')
        center = request.form.get('center')
        loc1 = request.form.get('loc1')
        loc2 = request.form.get('loc2', type=int)
        isvm = request.form.get('isvm', type=int)
        datein = request.form.get('datein')
        dateout = request.form.get('dateout')
        charge = request.form.get('charge')
        charge2 = request.form.get('charge2')
        isoper = request.form.get('isoper')
        oper = request.form.get('oper')
        power = request.form.get('power')
        pdu = request.form.get('pdu')
        os = request.form.get('os')
        osver = request.form.get('osver')
        maker = request.form.get('maker')
        model = request.form.get('model')
        serial = request.form.get('serial')
        domain = request.form.get('domain')
        charge3 = request.form.get('charge3')

        # 날짜 형식 검사 및 변환
        try:
            datein = datetime.strptime(datein, '%Y-%m-%d').date()
        except ValueError:
            datein = None  # 오류 발생 시 None으로 설정

        try:
            dateout = datetime.strptime(dateout, '%Y-%m-%d').date()
        except ValueError:
            dateout = None  # 오류 발생 시 None으로 설정

        print(isoper, oper, power, os, domain)

        # state → 코드 변환
        isoper = lookup_info_code('info_isoper', 'isoper', isoper)
        oper   = lookup_info_code('info_oper',   'oper',   oper)
        power  = lookup_info_code('info_power',  'power',  power)
        os     = lookup_info_code('info_os',     'os',     os)
        domain = lookup_info_code('info_domain', 'domain', domain)
        print(domain)

        update_asset(pnum, (itamnum, servername, ip, hostname, center, loc1, loc2,
                             isvm, datein, dateout, charge, charge2,
                             isoper, oper, power, pdu, os, osver, maker, model, serial, domain, charge3))

        return redirect(url_for('index_detail'))

    # GET 요청 시 데이터 가져오기
    data, isoper_options, oper_options, os_options, domain_options, power_options = get_asset_with_options(pnum)

    return render_template('edit.html', data=data,
                           isoper_options=isoper_options,
                           oper_options=oper_options,
                           os_options=os_options,
                           domain_options=domain_options,
                           power_options=power_options)


@app.route('/delete/<int:pnum>')
def delete_asset_route(pnum):
    delete_asset(pnum)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
