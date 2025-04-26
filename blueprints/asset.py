from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from utils.db import execute_query, execute_many, get_db_connection
from utils.cache import cache, invalidate_cache_pattern
import os
from flask import send_file

asset_bp = Blueprint('asset', __name__)


@asset_bp.route('/index')
def index():
    """자산 관리 메인 페이지"""
    # 데이터 카드 정보 가져오기
    data_card = get_data()  # 비동기 함수를 동기 함수로 변경

    # 그래프 데이터 가져오기
    graph_html = generate_asset_graph()  # 비동기 함수를 동기 함수로 변경

    # 자산 데이터 가져오기
    sql = """
        SELECT ta.*, 
               id.state AS domain_state, 
               io_isoper.state AS isoper_state, 
               io_oper.state AS oper_state, 
               io_power.state AS power_state, 
               io_os.state AS os_state 
        FROM total_asset ta 
        JOIN info_domain id ON ta.domain = id.domain
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        LEFT JOIN info_oper io_oper ON ta.oper = io_oper.oper
        LEFT JOIN info_power io_power ON ta.power = io_power.power
        LEFT JOIN info_os io_os ON ta.os = io_os.os
        WHERE ta.isfix = 1
        ORDER BY ta.dateupdate DESC
    """
    data = execute_query(sql)

    return render_template('index.html', data_card=data_card, data=data, graph=graph_html)


@asset_bp.route('/update_isfix', methods=['POST'])
def update_isfix():
    """선택된 자산의 isfix 값을 0으로 업데이트"""
    if request.method == 'POST':
        selected_assets = request.form.getlist('selected_assets[]')

        if selected_assets:
            # 선택된 자산의 isfix 값을 0으로 업데이트
            sql = "UPDATE total_asset SET isfix = 0 WHERE pnum IN (%s)" % ','.join(['%s'] * len(selected_assets))
            execute_query(sql, selected_assets, fetch_all=False)

            flash(f'{len(selected_assets)}개 자산의 정합성 확인이 완료되었습니다.', 'success')
        else:
            flash('선택된 자산이 없습니다.', 'warning')

    return redirect(url_for('asset.index'))


def get_data():
    """자산 데이터 통계 가져오기"""
    # 데이터베이스 쿼리
    query = "SELECT * FROM total_asset"
    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
            # 컬럼 이름 가져오기
            columns = [column[0] for column in cursor.description]
            # DataFrame 생성
            df = pd.DataFrame(data, columns=columns)
    finally:
        db.close()

    # 날짜 형식 변환
    df['datein'] = pd.to_datetime(df['datein'], errors='coerce')

    # 개수 계산
    total_assets = df[df['isoper'].isin([0, 1, 2])]
    total_servers = df[df['domain'] == 0]
    physical_servers = df[(df['domain'] == 0) & (df['isvm'] == 0)]
    virtual_servers = df[(df['domain'] == 0) & (df['isvm'] == 1)]
    current_year_assets = df[pd.to_datetime(df['datein']).dt.year == pd.to_datetime('now').year]
    current_month_assets = df[pd.to_datetime(df['datein']).dt.month == pd.to_datetime('now').month]
    oper_assets = df[(df['domain'] == 0) & (df['oper'] == 0)]
    qa_assets = df[(df['domain'] == 0) & (df['oper'] == 1)]
    dev_assets = df[(df['domain'] == 0) & (df['oper'] == 2)]
    dr_assets = df[(df['domain'] == 0) & (df['oper'] == 4)]
    current_year = pd.to_datetime('now').year
    current_month = pd.to_datetime('now').month

    return {
        "total_assets": len(total_assets),
        "total_servers": len(total_servers),
        "physical_servers": len(physical_servers),
        "virtual_servers": len(virtual_servers),
        "current_year_assets": len(current_year_assets),
        "current_month_assets": len(current_month_assets),
        "oper_assets": len(oper_assets),
        "qa_assets": len(qa_assets),
        "dev_assets": len(dev_assets),
        "dr_assets": len(dr_assets),
        "current_year": current_year,
        "current_month": current_month
    }


def generate_asset_graph():
    """자산 그래프 생성"""
    # SQL 쿼리 작성
    sql_graph = """
                SELECT ta.*, 
                       id.state AS domain_state, 
                       io_isoper.state AS isoper_state, 
                       io_oper.state AS oper_state, 
                       io_power.state AS power_state, 
                       io_os.state AS os_state 
                FROM hli_asset.total_asset ta 
                JOIN hli_asset.info_domain id ON ta.domain = id.domain
                LEFT JOIN hli_asset.info_isoper io_isoper ON ta.isoper = io_isoper.isoper
                LEFT JOIN hli_asset.info_oper io_oper ON ta.oper = io_oper.oper
                LEFT JOIN hli_asset.info_power io_power ON ta.power = io_power.power
                LEFT JOIN hli_asset.info_os io_os ON ta.os = io_os.os
                ORDER BY ta.dateinsert
                """

    # 데이터 가져오기
    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql_graph)
            data_graph = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            df_graph = pd.DataFrame(data_graph, columns=columns)
    finally:
        db.close()

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
    df_graph['label'] = df_graph.apply(
        lambda row: row['os_state'] if row['domain_state'] == '서버' else row['domain_state'], axis=1)
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

    return fig.to_html(full_html=False)


@asset_bp.route('/index_detail', methods=['GET', 'POST'])
def index_detail():
    """자산 상세 검색 페이지"""
    selected_columns = request.form.getlist('columns') if request.method == 'POST' else request.args.getlist('columns')

    # 기본 선택 열 설정 (아무것도 선택되지 않았을 경우)
    if not selected_columns:
        selected_columns = ['domain', 'servername', 'ip', 'hostname', 'os', 'osver']

    # 항상 포함되어야 하는 필수 열 (pnum은 자세히 링크에 필요)
    required_columns = ['pnum']

    # 열 매핑 정의 (DB 컬럼명 -> 화면 표시명)
    column_mapping = {
        'domain': '도메인',
        'itamnum': 'ITAM자산번호',
        'servername': '서버명',
        'ip': 'IP 주소',
        'hostname': '호스트 이름',
        'center': '센터',
        'loc1': '상면번호',
        'loc2': '상단번호',
        'isvm': 'VM 여부',
        'vcenter': '상위자산',
        'datein': '설치일자',
        'dateout': '폐기일자',
        'charge': '담당자(정)',
        'charge2': '담당자(부)',
        'isoper': '사용여부',
        'oper': '서비스구분',
        'power': '전원이중화',
        'pdu': 'PDU',
        'os': 'OS',
        'osver': 'OS버전',
        'maker': '제조사',
        'model': '모델명',
        'serial': '시리얼넘버',
        'charge3': '현업담당자',
        'isfix': '정합성 확인 필요',
        'dateupdate': '업데이트 일자'
    }

    # 역매핑 생성 (화면 표시명 -> DB 컬럼명)
    reverse_mapping = {v: k for k, v in column_mapping.items()}

    # SQL 쿼리 초기화 - 선택된 열만 조회
    select_columns = required_columns + selected_columns

    # 중복 제거
    select_columns = list(dict.fromkeys(select_columns))

    # 기본 테이블 열
    base_columns = [f"ta.{col}" for col in select_columns if col not in ['domain', 'isoper', 'oper', 'power', 'os']]

    # JOIN 테이블 열 (상태 값)
    join_columns = []
    if 'domain' in select_columns:
        join_columns.append("id.state AS domain_state")
    if 'isoper' in select_columns:
        join_columns.append("io_isoper.state AS isoper_state")
    if 'oper' in select_columns:
        join_columns.append("io_oper.state AS oper_state")
    if 'power' in select_columns:
        join_columns.append("io_power.state AS power_state")
    if 'os' in select_columns:
        join_columns.append("io_os.state AS os_state")

    # 모든 열 합치기
    all_columns = base_columns + join_columns

    # SQL 쿼리 생성
    sql = f"""
        SELECT {', '.join(all_columns)}
        FROM total_asset ta 
    """

    # JOIN 조건 추가
    if 'domain' in select_columns:
        sql += " JOIN info_domain id ON ta.domain = id.domain"
    if 'isoper' in select_columns:
        sql += " LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper"
    if 'oper' in select_columns:
        sql += " LEFT JOIN info_oper io_oper ON ta.oper = io_oper.oper"
    if 'power' in select_columns:
        sql += " LEFT JOIN info_power io_power ON ta.power = io_power.power"
    if 'os' in select_columns:
        sql += " LEFT JOIN info_os io_os ON ta.os = io_os.os"

    sql += " WHERE 1=1"
    params = []

    if request.method == 'POST':
        # 입력값 가져오기
        itamnum = request.form.get('itamnum', None)
        servername = request.form.get('servername', None)
        ip = request.form.get('ip', None)
        hostname = request.form.get('hostname', None)
        center = request.form.get('center', None)
        loc1 = request.form.get('loc1', None)
        loc2 = request.form.get('loc2', None, type=int)
        isvm = request.form.get('isvm', None, type=int)
        vcenter = request.form.get('vcenter', None, type=int)
        datein = request.form.get('datein', None)
        dateout = request.form.get('dateout', None)
        charge = request.form.get('charge', None)
        charge2 = request.form.get('charge2', None)
        isoper = request.form.get('isoper', None, type=int)
        oper = request.form.get('oper', None, type=int)
        power = request.form.get('power', None, type=int)
        pdu = request.form.get('pdu', None)
        os = request.form.get('os', None)
        osver = request.form.get('osver', None)
        maker = request.form.get('maker', None)
        model = request.form.get('model', None)
        serial = request.form.get('serial', None)
        domain = request.form.get('domain', None)
        charge3 = request.form.get('charge3', None)
        isfix = request.form.get('isfix', None, type=int)

        # 조건 추가
        if itamnum:
            sql += " AND ta.itamnum LIKE %s"
            params.append(f'%{itamnum}%')
        if servername:
            sql += " AND ta.servername LIKE %s"
            params.append(f'%{servername}%')
        if ip:
            sql += " AND ta.ip LIKE %s"
            params.append(f'%{ip}%')
        if hostname:
            sql += " AND ta.hostname LIKE %s"
            params.append(f'%{hostname}%')
        if center:
            sql += " AND ta.center LIKE %s"
            params.append(f'%{center}%')
        if loc1:
            sql += " AND ta.loc1 LIKE %s"
            params.append(f'%{loc1}%')
        if loc2 is not None:
            sql += " AND ta.loc2 = %s"
            params.append(loc2)
        if isvm is not None:
            sql += " AND ta.isvm = %s"
            params.append(isvm)
        if vcenter is not None:
            sql += " AND ta.vcenter = %s"
            params.append(vcenter)
        if datein:
            sql += " AND ta.datein LIKE %s"
            params.append(f'%{datein}%')
        if dateout:
            sql += " AND ta.dateout LIKE %s"
            params.append(f'%{dateout}%')
        if charge:
            sql += " AND ta.charge LIKE %s"
            params.append(f'%{charge}%')
        if charge2:
            sql += " AND ta.charge2 LIKE %s"
            params.append(f'%{charge2}%')
        if isoper is not None:
            sql += " AND ta.isoper = %s"
            params.append(isoper)
        if oper is not None:
            sql += " AND ta.oper = %s"
            params.append(oper)
        if power is not None:
            sql += " AND ta.power = %s"
            params.append(power)
        if pdu:
            sql += " AND ta.pdu LIKE %s"
            params.append(f'%{pdu}%')
        if os:
            sql += " AND ta.os LIKE %s"
            params.append(f'%{os}%')
        if osver:
            sql += " AND ta.osver LIKE %s"
            params.append(f'%{osver}%')
        if maker:
            sql += " AND ta.maker LIKE %s"
            params.append(f'%{maker}%')
        if model:
            sql += " AND ta.model LIKE %s"
            params.append(f'%{model}%')
        if serial:
            sql += " AND ta.serial LIKE %s"
            params.append(f'%{serial}%')
        if domain:
            sql += " AND ta.domain LIKE %s"
            params.append(f'%{domain}%')
        if charge3:
            sql += " AND ta.charge3 LIKE %s"
            params.append(f'%{charge3}%')
        if isfix is not None:
            sql += " AND ta.isfix = %s"
            params.append(isfix)

    # 정렬 추가
    sql += " ORDER BY ta.dateupdate DESC LIMIT 1000"  # 성능을 위해 결과 제한

    # 데이터 가져오기
    data = execute_query(sql, params)

    return render_template('index_detail.html',
                           data=data,
                           selected_columns=selected_columns,
                           column_mapping=column_mapping)


@asset_bp.route('/get_asset_details/<int:pnum>')
def get_asset_details(pnum):
    """자산 상세 정보 가져오기 (AJAX 요청용)"""
    sql = """
        SELECT ta.*, 
               id.state AS domain_state, 
               io_isoper.state AS isoper_state, 
               io_oper.state AS oper_state, 
               io_power.state AS power_state, 
               io_os.state AS os_state 
        FROM total_asset ta 
        JOIN info_domain id ON ta.domain = id.domain
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        LEFT JOIN info_oper io_oper ON ta.oper = io_oper.oper
        LEFT JOIN info_power io_power ON ta.power = io_power.power
        LEFT JOIN info_os io_os ON ta.os = io_os.os
        WHERE ta.pnum = %s
    """

    data = execute_query(sql, (pnum,), fetch_all=False)

    # vcenter 값이 있는 경우 상위 자산 정보 가져오기
    if data and data.get('isvm') == 1 and data.get('vcenter'):
        parent_sql = """
            SELECT pnum, servername, hostname, ip
            FROM total_asset
            WHERE pnum = %s
        """
        parent_data = execute_query(parent_sql, (data['vcenter'],), fetch_all=False)
        if parent_data:
            data['parent_asset'] = parent_data

    return jsonify(data)


@asset_bp.route('/search_assets', methods=['GET'])
def search_assets():
    """자산 검색 API (AJAX 요청용)"""
    search_term = request.args.get('term', '')

    # 검색어가 없으면 빈 결과 반환
    if not search_term:
        return jsonify([])

    # 물리 서버만 검색 (isvm = 0)
    sql = """
        SELECT pnum, servername, hostname, ip
        FROM total_asset
        WHERE isvm = 0 AND (servername LIKE %s OR hostname LIKE %s OR ip LIKE %s)
        LIMIT 20
    """

    search_param = f'%{search_term}%'
    results = execute_query(sql, (search_param, search_param, search_param))

    return jsonify(results)


@asset_bp.route('/write')
def write_asset():
    """자산 추가 페이지"""
    # 옵션 데이터 가져오기
    isoper_options = execute_query("SELECT * FROM info_isoper")
    oper_options = execute_query("SELECT * FROM info_oper")
    power_options = execute_query("SELECT * FROM info_power")
    os_options = execute_query("SELECT * FROM info_os")
    domain_options = execute_query("SELECT * FROM info_domain")

    return render_template('write.html',
                           isoper_options=isoper_options,
                           oper_options=oper_options,
                           power_options=power_options,
                           os_options=os_options,
                           domain_options=domain_options)


@asset_bp.route('/add', methods=['POST'])
def add_asset():
    """자산 추가 처리"""
    sql = """INSERT INTO total_asset (itamnum, servername, ip, hostname, center, loc1, loc2, isvm, vcenter, 
            datein, dateout, charge, charge2, isoper, oper, power, pdu, os, osver, maker, model, serial, domain, 
            charge3, usize, cpucore, memory, isfix, dateupdate) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s)"""

    # 폼 데이터 가져오기
    itamnum = request.form.get('itamnum')
    servername = request.form.get('servername')
    ip = request.form.get('ip')
    hostname = request.form.get('hostname')
    center = request.form.get('center')
    loc1 = request.form.get('loc1')
    loc2 = request.form.get('loc2', type=int)
    isvm = request.form.get('isvm', type=int)

    # vcenter 값 처리 - isvm이 1(가상머신)인 경우에만 vcenter 값을 사용
    vcenter = None
    if isvm == 1:
        vcenter = request.form.get('vcenter', type=int)
        # vcenter 값이 없거나 0인 경우 None으로 설정
        if not vcenter:
            vcenter = None

    datein = request.form.get('datein')
    dateout = request.form.get('dateout')
    charge = request.form.get('charge')
    charge2 = request.form.get('charge2')
    isoper_state = request.form.get('isoper')
    oper_state = request.form.get('oper')
    power_state = request.form.get('power')
    pdu = request.form.get('pdu')
    os_state = request.form.get('os')
    osver = request.form.get('osver')
    maker = request.form.get('maker')
    model = request.form.get('model')
    serial = request.form.get('serial')
    domain_state = request.form.get('domain')
    charge3 = request.form.get('charge3')
    usize = request.form.get('usize', type=int, default=1)
    cpucore = request.form.get('cpucore', type=int)
    memory = request.form.get('memory', type=int)
    isfix = 1  # 새로 추가된 자산은 기본적으로 정합성 확인이 필요
    dateupdate = datetime.now()  # 현재 시간으로 업데이트 일자 설정

    # 날짜 형식 검사 및 변환
    try:
        datein = datetime.strptime(datein, '%Y-%m-%d').date() if datein else None
    except ValueError:
        datein = None

    try:
        dateout = datetime.strptime(dateout, '%Y-%m-%d').date() if dateout else None
    except ValueError:
        dateout = None

    # 코드 값 조회
    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            # isoper
            cursor.execute("SELECT isoper FROM info_isoper WHERE state = %s", (isoper_state,))
            isoper_value = cursor.fetchone()
            isoper = isoper_value['isoper'] if isoper_value else 0

            # oper
            cursor.execute("SELECT oper FROM info_oper WHERE state = %s", (oper_state,))
            oper_value = cursor.fetchone()
            oper = oper_value['oper'] if oper_value else 0

            # power
            cursor.execute("SELECT power FROM info_power WHERE state = %s", (power_state,))
            power_value = cursor.fetchone()
            power = power_value['power'] if power_value else 0

            # os
            cursor.execute("SELECT os FROM info_os WHERE state = %s", (os_state,))
            os_value = cursor.fetchone()
            os = os_value['os'] if os_value else 0

            # domain
            cursor.execute("SELECT domain FROM info_domain WHERE state = %s", (domain_state,))
            domain_value = cursor.fetchone()
            domain = domain_value['domain'] if domain_value else 0

            # 데이터 삽입
            cursor.execute(sql, (itamnum, servername, ip, hostname, center, loc1, loc2,
                                 isvm, vcenter, datein, dateout, charge, charge2,
                                 isoper, oper, power, pdu, os, osver, maker, model, serial, domain, charge3,
                                 usize, cpucore, memory, isfix, dateupdate))
            db.commit()
    finally:
        db.close()

    # 캐시 무효화
    invalidate_cache_pattern('index_data')
    invalidate_cache_pattern('asset_data')
    invalidate_cache_pattern('asset_graph')

    return redirect(url_for('asset.index'))


@asset_bp.route('/edit/<int:pnum>', methods=['GET', 'POST'])
def edit_asset(pnum):
    """자산 수정 페이지 및 처리"""
    if request.method == 'POST':
        sql = """UPDATE total_asset SET itamnum = %s, servername = %s, ip = %s, 
                      hostname = %s, center = %s, loc1 = %s, loc2 = %s, isvm = %s, vcenter = %s,
                      datein = %s, dateout = %s, charge = %s, charge2 = %s, 
                      isoper = %s, oper = %s, power = %s, pdu = %s, os = %s, 
                      osver = %s, maker = %s, model = %s, serial = %s, domain = %s, charge3 = %s,
                      usize = %s, cpucore = %s, memory = %s, isfix = %s, dateupdate = %s
                      WHERE pnum = %s"""

        # 폼 데이터 가져오기
        itamnum = request.form.get('itamnum')
        servername = request.form.get('servername')
        ip = request.form.get('ip')
        hostname = request.form.get('hostname')
        center = request.form.get('center')
        loc1 = request.form.get('loc1')
        loc2 = request.form.get('loc2', type=int)
        isvm = request.form.get('isvm', type=int)

        # vcenter 값 처리 - isvm이 1(가상머신)인 경우에만 vcenter 값을 사용
        vcenter = None
        if isvm == 1:
            vcenter = request.form.get('vcenter', type=int)
            # vcenter 값이 없거나 0인 경우 None으로 설정
            if not vcenter:
                vcenter = None

        datein = request.form.get('datein')
        dateout = request.form.get('dateout')
        charge = request.form.get('charge')
        charge2 = request.form.get('charge2')
        isoper_state = request.form.get('isoper')
        oper_state = request.form.get('oper')
        power_state = request.form.get('power')
        pdu = request.form.get('pdu')
        os_state = request.form.get('os')
        osver = request.form.get('osver')
        maker = request.form.get('maker')
        model = request.form.get('model')
        serial = request.form.get('serial')
        domain_state = request.form.get('domain')
        charge3 = request.form.get('charge3')
        usize = request.form.get('usize', type=int, default=1)
        cpucore = request.form.get('cpucore', type=int)
        memory = request.form.get('memory', type=int)
        isfix = 1  # 수정된 자산은 기본적으로 정합성 확인이 필요
        dateupdate = datetime.now()  # 현재 시간으로 업데이트 일자 설정

        # 날짜 형식 검사 및 변환
        try:
            datein = datetime.strptime(datein, '%Y-%m-%d').date() if datein else None
        except ValueError:
            datein = None

        try:
            dateout = datetime.strptime(dateout, '%Y-%m-%d').date() if dateout else None
        except ValueError:
            dateout = None

        # 코드 값 조회
        db = get_db_connection()
        try:
            with db.cursor() as cursor:
                # isoper
                cursor.execute("SELECT isoper FROM info_isoper WHERE state = %s", (isoper_state,))
                isoper_value = cursor.fetchone()
                isoper = isoper_value['isoper'] if isoper_value else None

                # oper
                cursor.execute("SELECT oper FROM info_oper WHERE state = %s", (oper_state,))
                oper_value = cursor.fetchone()
                oper = oper_value['oper'] if oper_value else None

                # power
                cursor.execute("SELECT power FROM info_power WHERE state = %s", (power_state,))
                power_value = cursor.fetchone()
                power = power_value['power'] if power_value else None

                # os
                cursor.execute("SELECT os FROM info_os WHERE state = %s", (os_state,))
                os_value = cursor.fetchone()
                os = os_value['os'] if os_value else None

                # domain
                cursor.execute("SELECT domain FROM info_domain WHERE state = %s", (domain_state,))
                domain_value = cursor.fetchone()
                domain = domain_value['domain'] if domain_value else None

                # 데이터 업데이트
                cursor.execute(sql, (itamnum, servername, ip, hostname, center, loc1, loc2,
                                     isvm, vcenter, datein, dateout, charge, charge2,
                                     isoper, oper, power, pdu, os, osver, maker, model, serial, domain, charge3,
                                     usize, cpucore, memory, isfix, dateupdate, pnum))
                db.commit()
        finally:
            db.close()

        # 캐시 무효화
        invalidate_cache_pattern('index_data')
        invalidate_cache_pattern('asset_data')
        invalidate_cache_pattern('asset_graph')

        return redirect(url_for('asset.index_detail'))

    # GET 요청 시 데이터 가져오기
    sql = """
        SELECT ta.*, 
               io_isoper.state AS isoper_state, 
               io_oper.state AS oper_state,
               io_os.state AS os_state,
               io_domain.state AS domain_state,
               io_power.state AS power_state
        FROM total_asset ta
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        LEFT JOIN info_oper io_oper ON ta.oper = io_oper.oper
        LEFT JOIN info_os io_os ON ta.os = io_os.os
        LEFT JOIN info_domain io_domain ON ta.domain = io_domain.domain
        LEFT JOIN info_power io_power ON ta.power = io_power.power
        WHERE ta.pnum = %s
    """
    data = execute_query(sql, (pnum,), fetch_all=False)

    # 상위 자산 정보 가져오기 (vcenter가 있는 경우)
    parent_asset = None
    if data and data.get('isvm') == 1 and data.get('vcenter'):
        parent_sql = """
            SELECT pnum, servername, hostname, ip
            FROM total_asset
            WHERE pnum = %s
        """
        parent_asset = execute_query(parent_sql, (data['vcenter'],), fetch_all=False)

    # 하위 자산 정보 가져오기 (현재 자산의 pnum을 vcenter로 가지고 있는 자산들)
    child_assets = []
    child_sql = """
        SELECT pnum, servername, hostname, ip
        FROM total_asset
        WHERE vcenter = %s AND isvm = 1
        ORDER BY servername
    """
    child_assets = execute_query(child_sql, (pnum,))

    # 옵션 데이터 가져오기
    isoper_options = execute_query("SELECT * FROM info_isoper")
    oper_options = execute_query("SELECT * FROM info_oper")
    os_options = execute_query("SELECT * FROM info_os")
    domain_options = execute_query("SELECT * FROM info_domain")
    power_options = execute_query("SELECT * FROM info_power")

    return render_template('edit.html',
                           data=data,
                           parent_asset=parent_asset,
                           child_assets=child_assets,
                           isoper_options=isoper_options,
                           oper_options=oper_options,
                           os_options=os_options,
                           domain_options=domain_options,
                           power_options=power_options)


@asset_bp.route('/delete/<int:pnum>')
def delete_asset(pnum):
    """자산 삭제 처리"""
    sql = "DELETE FROM total_asset WHERE pnum = %s"
    execute_query(sql, (pnum,), fetch_all=False)

    # 캐시 무효화
    invalidate_cache_pattern('index_data')
    invalidate_cache_pattern('asset_data')
    invalidate_cache_pattern('asset_graph')

    return redirect(url_for('asset.index'))


@asset_bp.route('/export')
def export_asset():
    """자산 데이터 내보내기"""
    # 데이터베이스에서 자산 데이터 가져오기
    sql = "SELECT * FROM total_asset"
    data = execute_query(sql)

    # 데이터프레임 생성
    df = pd.DataFrame(data)

    # 엑셀 파일로 저장
    today = datetime.now().strftime('%Y%m%d')
    export_filename = f'asset_{today}.xlsx'
    export_filepath = os.path.join(os.getcwd(), 'exports', export_filename)

    # exports 폴더가 없으면 생성
    if not os.path.exists(os.path.dirname(export_filepath)):
        os.makedirs(os.path.dirname(export_filepath))

    # 파일 저장
    df.to_excel(export_filepath, index=False)

    return send_file(export_filepath, as_attachment=True)
