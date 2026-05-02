from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, send_file, session
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from utils.db import (
    execute_query, execute_many, get_db_connection,
    get_asset_info_list, get_asset_info_by_pnum,
    insert_asset_info, update_asset_info, delete_asset_info,
    bulk_insert_asset_info,
    get_ips_by_asset, replace_asset_ips, parse_ip_input,
    get_links_by_asset, replace_asset_links,
    get_relations_by_asset, replace_asset_relations,
    search_asset_info as db_search_assets,
    ASSET_OPTIONS,
)
from utils.cache import cache, invalidate_cache_pattern
import os
from werkzeug.utils import secure_filename
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from utils.auto_register import handle_auto_registered_assets
from utils.hierarchy import get_asset_hierarchy

asset_bp = Blueprint('asset', __name__)


@asset_bp.route('/index')
def index():
    """자산 관리 메인 페이지"""
    # 데이터 카드 정보 가져오기
    data_card = get_data()

    # 그래프 데이터 가져오기
    graphs = generate_asset_graph()

    # 자산 데이터 가져오기 (모든 자산을 확인 완료 상태로 처리)
    sql = """
        SELECT ta.*, 
               id.state AS domain_state, 
               io_isoper.state AS isoper_state, 
               io_oper.state AS oper_state, 
               io_power.state AS power_state, 
               io_os.state AS os_state,
               ig.state AS group_state
        FROM total_asset ta 
        JOIN info_domain id ON ta.domain = id.domain
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        LEFT JOIN info_oper io_oper ON ta.oper = io_oper.oper
        LEFT JOIN info_power io_power ON ta.power = io_power.power
        LEFT JOIN info_os io_os ON ta.os = io_os.os
        LEFT JOIN info_group ig ON ta.`group` = ig.`group` AND ta.domain = ig.domain
        ORDER BY ta.dateupdate DESC
    """
    data = execute_query(sql)

    # 모든 자산의 isfix 값을 0(확인 완료)으로 업데이트
    update_sql = "UPDATE total_asset SET isfix = 0 WHERE isfix != 0"
    execute_query(update_sql, fetch_all=False)

    return render_template('index.html', data_card=data_card, data=data, graphs=graphs)


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


@asset_bp.route('/handle_auto_assets', methods=['POST'])
def handle_auto_assets():
    """자동 등록된 자산 처리"""
    if request.method == 'POST':
        action = request.form.get('action')
        selected_assets = request.form.getlist('selected_assets[]')

        if not action or not selected_assets:
            flash('선택된 자산이 없거나 작업이 지정되지 않았습니다.', 'warning')
            return redirect(url_for('asset.index'))

        success, message = handle_auto_registered_assets(action, selected_assets)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'warning')

    return redirect(url_for('asset.index'))


def get_data():
    """자산 데이터 통계 가져오기"""
    # 데이터베이스 쿼리 - isfix=0이고 사용여부가 '사용'인 자산만 조회
    query = """
        SELECT ta.*, io_isoper.state AS isoper_state 
        FROM total_asset ta
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        WHERE ta.isfix = 0 AND io_isoper.state = '사용'
    """
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
    total_assets = len(df)
    total_servers = len(df[df['domain'] == 0])
    physical_servers = len(df[(df['domain'] == 0) & (df['group'] == 0)])
    virtual_servers = len(df[(df['domain'] == 0) & (df['group'] == 1)])

    # 현재 날짜 기준 계산
    current_date = pd.to_datetime('now')
    current_year = current_date.year
    current_month = current_date.month

    current_year_assets = len(df[pd.to_datetime(df['datein']).dt.year == current_year])
    current_month_assets = len(df[(pd.to_datetime(df['datein']).dt.year == current_year) &
                                  (pd.to_datetime(df['datein']).dt.month == current_month)])

    # 운영구분별 자산 수
    oper_assets = len(df[(df['domain'] == 0) & (df['oper'] == 0)])
    qa_assets = len(df[(df['domain'] == 0) & (df['oper'] == 1)])
    dev_assets = len(df[(df['domain'] == 0) & (df['oper'] == 2)])
    dr_assets = len(df[(df['domain'] == 0) & (df['oper'] == 4)])

    # 센터별 자산 수 (IDC/DR)
    idc_assets = len(df[df['center'].str.contains('IDC', na=False)])
    dr_center_assets = len(df[df['center'].str.contains('DR', na=False)])

    return {
        "total_assets": total_assets,
        "total_servers": total_servers,
        "physical_servers": physical_servers,
        "virtual_servers": virtual_servers,
        "current_year_assets": current_year_assets,
        "current_month_assets": current_month_assets,
        "oper_assets": oper_assets,
        "qa_assets": qa_assets,
        "dev_assets": dev_assets,
        "dr_assets": dr_assets,
        "idc_assets": idc_assets,
        "dr_center_assets": dr_center_assets,
        "current_year": current_year,
        "current_month": current_month
    }


def generate_asset_graph():
    """자산 그래프 생성"""
    # SQL 쿼리 작성 - isfix=0이고 사용여부가 '사용'인 자산만 조회
    sql_graph = """
                SELECT ta.*, 
                       id.state AS domain_state, 
                       io_isoper.state AS isoper_state, 
                       io_oper.state AS oper_state, 
                       io_power.state AS power_state, 
                       io_os.state AS os_state,
                       ig.state AS group_state
                FROM hli_asset.total_asset ta 
                JOIN hli_asset.info_domain id ON ta.domain = id.domain
                LEFT JOIN hli_asset.info_isoper io_isoper ON ta.isoper = io_isoper.isoper
                LEFT JOIN hli_asset.info_oper io_oper ON ta.oper = io_oper.oper
                LEFT JOIN hli_asset.info_power io_power ON ta.power = io_power.power
                LEFT JOIN hli_asset.info_os io_os ON ta.os = io_os.os
                LEFT JOIN hli_asset.info_group ig ON ta.`group` = ig.`group` AND ta.domain = ig.domain
                WHERE ta.isfix = 0
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

    # 최근 1년 기간 설정
    one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)

    # 1. 전체 자산의 최근 1년간 누적 그래프
    # 최근 1년간의 월 목록 생성
    recent_months = pd.period_range(start=one_year_ago, end=pd.Timestamp.now(), freq='M')

    # 각 월별, 도메인별 누적 자산 계산
    monthly_data = []

    for month in recent_months:
        month_end = month.to_timestamp(how='end')

        # 해당 월 이전에 설치된 모든 자산
        installed_before = df_graph[df_graph['datein'] <= month_end]

        # 해당 월 이전에 폐기된 모든 자산
        discarded_before = installed_before[~installed_before['dateout'].isna() &
                                            (installed_before['dateout'] <= month_end)]

        # 해당 월 말 기준 유효 자산 (설치되었고 아직 폐기되지 않은 자산)
        valid_assets = installed_before[installed_before['dateout'].isna() |
                                        (installed_before['dateout'] > month_end) |
                                        (installed_before['isoper_state'] == '사용')]

        # 도메인별 자산 수 계산
        domain_counts = valid_assets['domain_state'].value_counts()

        # 결과 저장
        for domain, count in domain_counts.items():
            monthly_data.append({
                'month': month.strftime('%Y-%m'),
                'domain_state': domain,
                'count': count
            })

    # 데이터프레임으로 변환
    monthly_df = pd.DataFrame(monthly_data)

    # 피벗 테이블로 변환
    if not monthly_df.empty:
        monthly_pivot = monthly_df.pivot_table(
            index='month',
            columns='domain_state',
            values='count',
            fill_value=0
        ).reset_index()

        fig1 = px.bar(monthly_pivot, x='month', y=monthly_pivot.columns[1:],
                      title='전체 자산 현황 (최근 1년)',
                      labels={'value': '개수', 'month': '월', 'variable': '도메인'},
                      barmode='stack')
    else:
        # 데이터가 없는 경우 빈 그래프 생성
        fig1 = px.bar(title='전체 자산 현황 (최근 1년)')
        fig1.update_layout(
            xaxis_title='월',
            yaxis_title='개수'
        )

    # 2. 최근 1년간 설치/폐기 막대 그래프 (누적하지 않음)
    # 설치 데이터: 최근 1년 내 설치된 자산
    installed_df = df_graph[df_graph['datein'] >= one_year_ago].copy()
    installed_df['month'] = installed_df['datein'].dt.strftime('%Y-%m')
    installed_counts = installed_df.groupby('month').size().reset_index(name='installed')

    # 폐기 데이터: 최근 1년 내 폐기된 자산
    discarded_df = df_graph[(~df_graph['dateout'].isna()) & (df_graph['dateout'] >= one_year_ago)].copy()
    discarded_df['month'] = discarded_df['dateout'].dt.strftime('%Y-%m')
    discarded_counts = discarded_df.groupby('month').size().reset_index(name='discarded')

    # 모든 월 목록 생성
    all_months = pd.DataFrame({'month': [m.strftime('%Y-%m') for m in recent_months]})

    # 설치 및 폐기 데이터 병합
    monthly_changes = all_months.merge(installed_counts, on='month', how='left').fillna(0)
    monthly_changes = monthly_changes.merge(discarded_counts, on='month', how='left').fillna(0)

    # wide-form에서 long-form으로 변환
    monthly_changes_long = pd.melt(
        monthly_changes,
        id_vars=['month'],
        value_vars=['installed', 'discarded'],
        var_name='category',
        value_name='count'
    )

    # 카테고리 이름 변경
    category_names = {'installed': '설치', 'discarded': '폐기'}
    monthly_changes_long['category'] = monthly_changes_long['category'].map(category_names)

    fig2 = px.bar(monthly_changes_long, x='month', y='count', color='category',
                  title='최근 1년간 설치/폐기 자산',
                  labels={'count': '개수', 'month': '월', 'category': '구분'},
                  barmode='group',
                  color_discrete_map={'설치': 'green', '폐기': 'red'})
    fig2.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))

    # 3. 도메인별 원형 그래프
    domain_counts = df_graph['domain_state'].value_counts().reset_index()
    domain_counts.columns = ['도메인', '개수']

    fig3 = px.pie(domain_counts, values='개수', names='도메인', title='도메인별 자산 분포')
    fig3.update_traces(textposition='inside', textinfo='percent+label+value')

    # 4. 서버 도메인의 OS별 원형 그래프
    server_df = df_graph[df_graph['domain_state'] == '서버']
    os_counts = server_df['os_state'].value_counts().reset_index()
    os_counts.columns = ['OS', '개수']

    fig4 = px.pie(os_counts, values='개수', names='OS', title='서버 OS별 분포')
    fig4.update_traces(textposition='inside', textinfo='percent+label+value')

    # HTML로 그래프 렌더링
    graph1 = fig1.to_html(full_html=False, include_plotlyjs=False)
    graph2 = fig2.to_html(full_html=False, include_plotlyjs=False)
    graph3 = fig3.to_html(full_html=False, include_plotlyjs=False)
    graph4 = fig4.to_html(full_html=False, include_plotlyjs=False)

    return {
        'graph1': graph1,
        'graph2': graph2,
        'graph3': graph3,
        'graph4': graph4
    }


@asset_bp.route('/index_detail', methods=['GET', 'POST'])
def index_detail():
    """자산 상세 검색 페이지 (asset_info 스키마)"""
    if request.method == 'POST':
        selected_columns = request.form.getlist('columns')
        session['search_options'] = {k: v for k, v in request.form.items() if k != 'columns'}
        session['selected_columns'] = selected_columns
    else:
        url_columns = request.args.getlist('columns')
        if url_columns:
            selected_columns = url_columns
            session['selected_columns'] = selected_columns
        else:
            selected_columns = session.get('selected_columns', [])

    if not selected_columns:
        selected_columns = ['grp', 'servername', 'ip', 'hostname', 'os', 'status']

    # pnum은 항상 조회 (더블클릭 링크용)
    if 'pnum' not in selected_columns:
        selected_columns = ['pnum'] + selected_columns

    column_mapping = {
        'pnum':                 '자산번호',
        'hostname':             'Hostname',
        'servername':           '서버명',
        'grp':                  '그룹',
        'oper':                 '운영구분',
        'status':               '자산상태',
        'center':               '센터',
        'network_zone':         '망',
        'asset_type':           '물리/논리',
        'purpose':              '용도',
        'ip':                   'IP 주소',
        'loc1':                 '상면번호',
        'loc2':                 '상단번호',
        'usize':                'U사이즈',
        'maker':                '제조사',
        'model':                '모델명',
        'serial':               '시리얼',
        'os':                   'OS',
        'osver':                'OS버전',
        'cpucore':              'CPU코어',
        'cpusocket':            'CPU소켓',
        'memory':               '메모리(GB)',
        'datein':               '도입일자',
        'dateout':              '폐기일자',
        'hw_eos':               'HW EOS',
        'hw_eosl':              'HW EOSL',
        'importance':           '중요도',
        'power':                '전원이중화',
        'watt':                 '소비전력(W)',
        'ampere':               '사용전류(A)',
        'charge':               '담당(정)',
        'charge2':              '담당(부)',
        'charge3':              '서비스담당',
        'memo':                 '메모',
        'vm_parent_servername': '상위VM 서버명',
        'vm_parent_hostname':   '상위VM Hostname',
        'vm_parent_ip':         '상위VM IP',
    }

    if request.method == 'POST':
        search_options = {k: v for k, v in request.form.items() if k != 'columns'}
    else:
        search_options = session.get('search_options', {})

    # ── SQL 빌드 ─────────────────────────────────────────────
    sql = """
        SELECT ai.*,
               GROUP_CONCAT(DISTINCT aip.ip ORDER BY aip.id SEPARATOR ', ') AS ip,
               ANY_VALUE(vm_info.vm_parent_servername) AS vm_parent_servername,
               ANY_VALUE(vm_info.vm_parent_hostname)   AS vm_parent_hostname,
               ANY_VALUE(vm_info.vm_parent_ip)         AS vm_parent_ip
        FROM asset_info ai
        LEFT JOIN asset_ip aip ON ai.pnum = aip.asset_pnum
        LEFT JOIN (
            SELECT ar.child_pnum,
                   ANY_VALUE(pa.servername) AS vm_parent_servername,
                   ANY_VALUE(pa.hostname)   AS vm_parent_hostname,
                   GROUP_CONCAT(DISTINCT paip.ip ORDER BY paip.id SEPARATOR ', ') AS vm_parent_ip
            FROM asset_relation ar
            JOIN asset_info pa   ON ar.parent_pnum = pa.pnum
            LEFT JOIN asset_ip paip ON paip.asset_pnum = pa.pnum
            WHERE ar.relation_type = 'VM'
            GROUP BY ar.child_pnum
        ) vm_info ON vm_info.child_pnum = ai.pnum
        WHERE 1=1
    """
    params = []

    def _like(field, val):
        return f" AND ai.{field} LIKE %s", f"%{val}%"

    for field in ('servername', 'hostname', 'center', 'loc1', 'osver', 'maker', 'model', 'serial',
                  'grp', 'oper', 'status', 'network_zone',
                  'asset_type', 'importance', 'power', 'os', 'purpose'):
        val = search_options.get(field, '').strip()
        if val:
            clause, p = _like(field, val)
            sql += clause
            params.append(p)

    # 담당자(정)·(부)·서비스담당자 통합 OR 검색
    charge_any = search_options.get('charge_any', '').strip()
    if charge_any:
        sql += " AND (ai.charge LIKE %s OR ai.charge2 LIKE %s OR ai.charge3 LIKE %s)"
        pv = f"%{charge_any}%"
        params.extend([pv, pv, pv])

    # 날짜 기간(from~to) 검색
    for field in ('datein', 'dateout', 'hw_eos', 'hw_eosl'):
        from_val = search_options.get(f'{field}_from', '').strip()
        to_val   = search_options.get(f'{field}_to',   '').strip()
        if from_val:
            sql += f" AND ai.{field} >= %s"
            params.append(from_val)
        if to_val:
            sql += f" AND ai.{field} <= %s"
            params.append(to_val)

    loc2 = search_options.get('loc2', '').strip()
    if loc2:
        try:
            sql += " AND ai.loc2 = %s"
            params.append(int(loc2))
        except ValueError:
            pass

    ip_search = search_options.get('ip', '').strip()
    if ip_search:
        sql += " AND ai.pnum IN (SELECT asset_pnum FROM asset_ip WHERE ip LIKE %s)"
        params.append(f"%{ip_search}%")

    sql += " GROUP BY ai.pnum ORDER BY ai.pnum DESC"

    # 세션 저장 (검색결과 내보내기용)
    session['last_search_query'] = sql
    session['last_search_params'] = params

    data = execute_query(sql, params)
    hierarchy = get_asset_hierarchy()

    return render_template('index_detail.html',
                           data=data,
                           selected_columns=selected_columns,
                           column_mapping=column_mapping,
                           hierarchy=hierarchy,
                           search_options=search_options,
                           options=ASSET_OPTIONS)


@asset_bp.route('/get_asset_details/<int:pnum>')
def get_asset_details(pnum):
    """자산 상세 정보 가져오기 (AJAX 요청용)"""
    sql = """
        SELECT ta.*, 
               id.state AS domain_state, 
               io_isoper.state AS isoper_state, 
               io_oper.state AS oper_state, 
               io_power.state AS power_state, 
               io_os.state AS os_state,
               ig.state AS group_state
        FROM total_asset ta 
        JOIN info_domain id ON ta.domain = id.domain
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        LEFT JOIN info_oper io_oper ON ta.oper = io_oper.oper
        LEFT JOIN info_power io_power ON ta.power = io_power.power
        LEFT JOIN info_os io_os ON ta.os = io_os.os
        LEFT JOIN info_group ig ON ta.`group` = ig.`group` AND ta.domain = ig.domain
        WHERE ta.pnum = %s
    """

    data = execute_query(sql, (pnum,), fetch_all=False)

    # vcenter 값이 있는 경우 상위 자산 정보 가져오기
    if data and data.get('group') == 1 and data.get('vcenter'):
        parent_sql = """
            SELECT pnum, servername, hostname, ip
            FROM total_asset
            WHERE pnum = %s
        """
        parent_data = execute_query(parent_sql, (data['vcenter'],), fetch_all=False)
        if parent_data:
            data['parent_asset'] = parent_data

    return jsonify(data)


@asset_bp.route('/get_groups', methods=['GET'])
def get_groups():
    """도메인에 따른 그룹 정보 가져오기"""
    domain = request.args.get('domain', type=int)

    if domain is None:
        return jsonify([])

    sql = "SELECT `group`, state FROM info_group WHERE domain = %s"
    groups = execute_query(sql, (domain,))

    return jsonify(groups)


@asset_bp.route('/search_assets', methods=['GET'])
def search_assets():
    """자산 검색 API (AJAX autocomplete)"""
    term       = request.args.get('term', '')
    grp_filter = request.args.get('grp', None)

    if not term:
        return jsonify([])

    results = db_search_assets(term, grp_filter=grp_filter, limit=20)
    return jsonify([
        {
            "pnum":       r["pnum"],
            "label":      f"{r['servername'] or ''} ({r['hostname'] or ''}) [{r['ip'] or ''}]",
            "servername": r["servername"],
            "hostname":   r["hostname"],
            "ip":         r["ip"],
            "grp":        r["grp"],
        }
        for r in results
    ])


@asset_bp.route('/write')
def write_asset():
    """자산 등록 페이지 (신규 — pnum 없음)"""
    hierarchy = get_asset_hierarchy()
    return render_template('asset/form.html',
                           mode='create',
                           data=None,
                           ips=[],
                           links=[],
                           relations=[],
                           options=ASSET_OPTIONS,
                           hierarchy=hierarchy)


@asset_bp.route('/add', methods=['POST'])
def add_asset():
    """자산 등록 처리"""
    data = _collect_form_data()

    # asset_info 삽입
    new_pnum = insert_asset_info(data)

    # IP 저장
    replace_asset_ips(new_pnum, parse_ip_input(request.form.get('ip_raw', '')))

    # 연계 정보 저장
    replace_asset_links(new_pnum, _collect_links())

    # 관계 저장
    replace_asset_relations(new_pnum, _collect_relations())

    _invalidate_asset_cache()
    flash('자산정보가 성공적으로 등록되었습니다.', 'success')
    return redirect(url_for('asset.index'))


@asset_bp.route('/edit/<int:pnum>', methods=['GET', 'POST'])
def edit_asset(pnum):
    """자산 수정 페이지 및 처리"""
    if request.method == 'POST':
        data = _collect_form_data()
        update_asset_info(pnum, data)

        replace_asset_ips(pnum, parse_ip_input(request.form.get('ip_raw', '')))
        replace_asset_links(pnum, _collect_links())
        replace_asset_relations(pnum, _collect_relations())

        _invalidate_asset_cache()
        flash('자산정보가 성공적으로 수정되었습니다.', 'success')
        return redirect(url_for('asset.index_detail'))

    # GET: 기존 데이터 조회
    data      = get_asset_info_by_pnum(pnum)
    ips       = get_ips_by_asset(pnum)
    links     = get_links_by_asset(pnum)
    relations = get_relations_by_asset(pnum)

    # 연계 소프트웨어 (total_software 테이블 참조 — 기존 유지)
    linked_software = execute_query("""
        SELECT s.sw_idx, s.sw_name, s.sw_version, st.type_name,
               CASE s.sw_status WHEN 1 THEN '사용' ELSE '미사용' END AS isoper_state
        FROM info_software s
        LEFT JOIN info_software_type st ON s.sw_type = st.type_idx
        JOIN total_software ts ON s.sw_idx = ts.software_swidx
        WHERE ts.software_pnum = %s
        ORDER BY s.sw_name
    """, (pnum,))

    # 연계 서비스 (total_service 테이블 참조 — 기존 유지)
    linked_services = execute_query("""
        SELECT sv.app_idx, sv.app_name, sv.app_servicecode
        FROM total_service ts
        JOIN info_service sv ON ts.service_idx = sv.app_idx
        WHERE ts.service_pnum = %s
        ORDER BY sv.app_name
    """, (pnum,))

    hierarchy = get_asset_hierarchy(pnum=pnum)

    return render_template('asset/form.html',
                           mode='edit',
                           data=data,
                           ips=ips,
                           links=links,
                           relations=relations,
                           linked_software=linked_software,
                           linked_services=linked_services,
                           options=ASSET_OPTIONS,
                           hierarchy=hierarchy)


@asset_bp.route('/delete/<int:pnum>')
def delete_asset(pnum):
    """자산 삭제 처리 (FK CASCADE 로 IP/연계/관계 자동 삭제)"""
    delete_asset_info(pnum)
    _invalidate_asset_cache()
    flash('자산이 삭제되었습니다.', 'success')
    return redirect(url_for('asset.index'))


@asset_bp.route('/export', methods=['GET', 'POST'])
def export_asset():
    """자산 데이터 내보내기 (열 선택 지원)"""
    # 선택된 열 (POST: 모달에서 선택, GET: 전체)
    col_order = [
        'pnum', 'hostname', 'servername', 'grp', 'oper', 'status', 'center', 'network_zone',
        'asset_type', 'purpose', 'ip', 'loc1', 'loc2', 'usize', 'maker', 'model', 'serial',
        'os', 'osver', 'cpucore', 'cpusocket', 'memory', 'datein', 'dateout',
        'hw_eos', 'hw_eosl', 'importance', 'power', 'watt', 'ampere',
        'charge', 'charge2', 'charge3', 'memo',
        'vm_parent_servername', 'vm_parent_hostname', 'vm_parent_ip',
    ]
    if request.method == 'POST':
        chosen = request.form.getlist('columns')
        col_order = [c for c in col_order if c in chosen] or col_order

    label_map = {
        'pnum': '자산번호', 'hostname': 'Hostname', 'servername': '서버명',
        'grp': '그룹', 'oper': '운영구분', 'status': '자산상태', 'center': '센터',
        'network_zone': '망', 'asset_type': '물리/논리', 'purpose': '용도',
        'ip': 'IP 주소', 'loc1': '상면번호', 'loc2': '상단번호', 'usize': 'U사이즈',
        'maker': '제조사', 'model': '모델명', 'serial': '시리얼',
        'os': 'OS', 'osver': 'OS버전', 'cpucore': 'CPU코어',
        'cpusocket': 'CPU소켓', 'memory': '메모리(GB)',
        'datein': '도입일자', 'dateout': '폐기일자',
        'hw_eos': 'HW EOS', 'hw_eosl': 'HW EOSL',
        'importance': '중요도', 'power': '전원이중화',
        'watt': '소비전력(W)', 'ampere': '사용전류(A)',
        'charge': '담당(정)', 'charge2': '담당(부)', 'charge3': '서비스담당', 'memo': '메모',
        'vm_parent_servername': '상위VM 서버명',
        'vm_parent_hostname':   '상위VM Hostname',
        'vm_parent_ip':         '상위VM IP',
    }

    sql = """
        SELECT ai.*,
               GROUP_CONCAT(DISTINCT aip.ip ORDER BY aip.id SEPARATOR ', ') AS ip,
               ANY_VALUE(vm_info.vm_parent_servername) AS vm_parent_servername,
               ANY_VALUE(vm_info.vm_parent_hostname)   AS vm_parent_hostname,
               ANY_VALUE(vm_info.vm_parent_ip)         AS vm_parent_ip
        FROM asset_info ai
        LEFT JOIN asset_ip aip ON ai.pnum = aip.asset_pnum
        LEFT JOIN (
            SELECT ar.child_pnum,
                   ANY_VALUE(pa.servername) AS vm_parent_servername,
                   ANY_VALUE(pa.hostname)   AS vm_parent_hostname,
                   GROUP_CONCAT(DISTINCT paip.ip ORDER BY paip.id SEPARATOR ', ') AS vm_parent_ip
            FROM asset_relation ar
            JOIN asset_info pa   ON ar.parent_pnum = pa.pnum
            LEFT JOIN asset_ip paip ON paip.asset_pnum = pa.pnum
            WHERE ar.relation_type = 'VM'
            GROUP BY ar.child_pnum
        ) vm_info ON vm_info.child_pnum = ai.pnum
        GROUP BY ai.pnum
        ORDER BY ai.pnum
    """
    rows = execute_query(sql)
    if not rows:
        rows = []

    # 선택된 열만 추출
    records = [{c: (row.get(c) or '') for c in col_order} for row in rows]
    df = pd.DataFrame(records, columns=col_order)
    df.rename(columns=label_map, inplace=True)

    today = datetime.now().strftime('%Y%m%d')
    export_filepath = os.path.join(os.getcwd(), 'exports', f'asset_{today}.xlsx')
    os.makedirs(os.path.dirname(export_filepath), exist_ok=True)

    with pd.ExcelWriter(export_filepath, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='자산목록')
        ws = writer.sheets['자산목록']
        for i, col in enumerate(df.columns, 1):
            max_len = max(df[col].astype(str).map(len).max() if len(df) else 0, len(col) + 2)
            ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 40)

    return send_file(export_filepath, as_attachment=True)


@asset_bp.route('/export_filtered_asset')
def export_filtered_asset():
    """검색결과 내보내기 (세션 마지막 쿼리 재사용)"""
    last_sql = session.get('last_search_query')
    last_params = session.get('last_search_params', [])

    if not last_sql:
        last_sql = """
            SELECT ai.*, GROUP_CONCAT(aip.ip ORDER BY aip.id SEPARATOR ', ') AS ip
            FROM asset_info ai
            LEFT JOIN asset_ip aip ON ai.pnum = aip.asset_pnum
            GROUP BY ai.pnum ORDER BY ai.pnum DESC
        """
        last_params = []

    rows = execute_query(last_sql, last_params) or []
    label_map = {
        'pnum': '자산번호', 'hostname': 'Hostname', 'servername': '서버명',
        'grp': '그룹', 'oper': '운영구분', 'status': '자산상태', 'center': '센터',
        'network_zone': '망', 'asset_type': '물리/논리', 'purpose': '용도',
        'ip': 'IP 주소', 'loc1': '상면번호', 'loc2': '상단번호', 'usize': 'U사이즈',
        'maker': '제조사', 'model': '모델명', 'serial': '시리얼',
        'os': 'OS', 'osver': 'OS버전', 'cpucore': 'CPU코어',
        'cpusocket': 'CPU소켓', 'memory': '메모리(GB)',
        'datein': '도입일자', 'dateout': '폐기일자',
        'hw_eos': 'HW EOS', 'hw_eosl': 'HW EOSL',
        'importance': '중요도', 'power': '전원이중화',
        'watt': '소비전력(W)', 'ampere': '사용전류(A)',
        'charge': '담당(정)', 'charge2': '담당(부)', 'charge3': '서비스담당', 'memo': '메모',
    }
    df = pd.DataFrame(rows)
    if not df.empty:
        df.rename(columns={k: v for k, v in label_map.items() if k in df.columns}, inplace=True)

    today = datetime.now().strftime('%Y%m%d')
    fpath = os.path.join(os.getcwd(), 'exports', f'asset_filtered_{today}.xlsx')
    os.makedirs(os.path.dirname(fpath), exist_ok=True)

    with pd.ExcelWriter(fpath, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='검색결과')
        ws = writer.sheets['검색결과']
        for i, col in enumerate(df.columns, 1):
            max_len = max(df[col].astype(str).map(len).max() if len(df) else 0, len(col) + 2)
            ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 40)

    return send_file(fpath, as_attachment=True)


@asset_bp.route('/export_bulk')
def export_bulk():
    """일괄 등록/수정용 전체 자산 xlsx 다운로드 (pnum 포함)"""
    sql = """
        SELECT ai.pnum, ai.hostname, ai.servername, ai.grp, ai.oper, ai.status, ai.center,
               ai.network_zone, ai.asset_type, ai.purpose,
               GROUP_CONCAT(aip.ip ORDER BY aip.id SEPARATOR ', ') AS ip,
               ai.loc1, ai.loc2, ai.usize, ai.maker, ai.model, ai.serial,
               ai.os, ai.osver, ai.cpucore, ai.cpusocket, ai.memory,
               ai.datein, ai.dateout, ai.hw_eos, ai.hw_eosl,
               ai.importance, ai.power, ai.watt, ai.ampere,
               ai.charge, ai.charge2, ai.charge3, ai.memo
        FROM asset_info ai
        LEFT JOIN asset_ip aip ON ai.pnum = aip.asset_pnum
        GROUP BY ai.pnum
        ORDER BY ai.pnum
    """
    rows = execute_query(sql) or []
    df = pd.DataFrame(rows)

    today = datetime.now().strftime('%Y%m%d')
    fpath = os.path.join(os.getcwd(), 'exports', f'asset_bulk_{today}.xlsx')
    os.makedirs(os.path.dirname(fpath), exist_ok=True)

    with pd.ExcelWriter(fpath, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='자산목록')
        ws = writer.sheets['자산목록']
        for i, col in enumerate(df.columns, 1):
            max_len = max(df[col].astype(str).map(len).max() if len(df) else 0, len(col) + 2)
            ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 40)

    return send_file(fpath, as_attachment=True)


@asset_bp.route('/bulk_upsert_asset', methods=['POST'])
def bulk_upsert_asset():
    """일괄 등록/수정 처리 (pnum 존재 → UPDATE, 없으면 INSERT)"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '파일이 없습니다.'})

    f = request.files['file']
    if not f.filename.endswith('.xlsx'):
        return jsonify({'success': False, 'message': 'xlsx 파일만 업로드 가능합니다.'})

    try:
        import io
        df = pd.read_excel(io.BytesIO(f.read()), engine='openpyxl')
        df = df.where(pd.notnull(df), None)  # NaN → None

        # DB에 존재하는 pnum 목록
        existing = {row['pnum'] for row in execute_query("SELECT pnum FROM asset_info")}

        inserted = updated = 0
        for _, row in df.iterrows():
            pnum = row.get('pnum')
            data = {k: (str(v) if v is not None else None)
                    for k, v in row.items() if k != 'pnum' and k in (
                        'hostname', 'servername', 'grp', 'oper', 'status', 'center',
                        'network_zone', 'asset_type', 'purpose', 'loc1', 'loc2', 'usize',
                        'maker', 'model', 'serial', 'os', 'osver', 'cpucore', 'cpusocket',
                        'memory', 'datein', 'dateout', 'hw_eos', 'hw_eosl',
                        'importance', 'power', 'watt', 'ampere',
                        'charge', 'charge2', 'charge3', 'memo'
                    )}
            data['dateupdate'] = datetime.now()

            # IP 처리
            ip_raw = row.get('ip') or ''

            if pnum and int(pnum) in existing:
                update_asset_info(int(pnum), data)
                ip_list = parse_ip_input(str(ip_raw))
                replace_asset_ips(int(pnum), ip_list)
                updated += 1
            else:
                new_pnum = insert_asset_info(data)
                ip_list = parse_ip_input(str(ip_raw))
                replace_asset_ips(new_pnum, ip_list)
                inserted += 1

        _invalidate_asset_cache()
        return jsonify({
            'success': True,
            'message': f'처리 완료: 신규 {inserted}건 등록, {updated}건 수정되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'처리 중 오류: {str(e)}'})


@asset_bp.route('/export_relation_template')
def export_relation_template():
    """VM 자산 관계 일괄 등록/수정용 템플릿 다운로드 (기존 VM 관계 포함)"""
    import io as _io
    rows = execute_query("""
        SELECT ar.id          AS relation_id,
               ar.child_pnum,
               ci.servername  AS child_servername,
               ci.hostname    AS child_hostname,
               ar.parent_pnum,
               pi.servername  AS parent_servername,
               pi.hostname    AS parent_hostname
        FROM asset_relation ar
        JOIN asset_info ci ON ci.pnum = ar.child_pnum
        JOIN asset_info pi ON pi.pnum = ar.parent_pnum
        WHERE ar.relation_type = 'VM'
        ORDER BY ar.child_pnum
    """) or []

    df = pd.DataFrame(rows, columns=[
        'relation_id', 'child_pnum', 'child_servername', 'child_hostname',
        'parent_pnum', 'parent_servername', 'parent_hostname',
    ])

    output = _io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='VM관계')
        ws = writer.sheets['VM관계']
        # 헤더 설명 행 (맨 위 삽입)
        ws.insert_rows(1, 2)
        ws['A1'] = 'VM 자산 관계 일괄 등록/수정 템플릿'
        ws['A2'] = ('child_pnum(필수): 하위 자산번호 | parent_pnum(필수): 상위 자산번호 | '
                    'child_servername/child_hostname/parent_servername/parent_hostname: 참고용(수정 무시)')
        # 열 너비
        for i, w in enumerate([14, 12, 22, 22, 12, 22, 22], 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='vm_relation_template.xlsx',
    )


@asset_bp.route('/bulk_upsert_relation', methods=['POST'])
def bulk_upsert_relation():
    """VM 자산 관계 일괄 등록/수정.
    child_pnum 당 VM 관계는 1개만 유지 (중복 시 UPDATE)."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '파일이 없습니다.'})

    f = request.files['file']
    if not f.filename.endswith('.xlsx'):
        return jsonify({'success': False, 'message': 'xlsx 파일만 업로드 가능합니다.'})

    try:
        import io as _io
        df = pd.read_excel(_io.BytesIO(f.read()), engine='openpyxl')
        # 설명 행이 있을 경우 header=2로 재시도
        if 'child_pnum' not in df.columns:
            f.stream.seek(0)
            df = pd.read_excel(_io.BytesIO(f.read()), engine='openpyxl', header=2)
        df = df.where(pd.notnull(df), None)

        inserted = updated = failed = 0
        row_errors = []
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for idx, row in df.iterrows():
                    child_pnum  = row.get('child_pnum')
                    parent_pnum = row.get('parent_pnum')
                    if not child_pnum or not parent_pnum:
                        failed += 1
                        row_errors.append(f'행 {idx + 1}: child_pnum 또는 parent_pnum 누락')
                        continue
                    try:
                        child_pnum  = int(child_pnum)
                        parent_pnum = int(parent_pnum)
                    except (ValueError, TypeError):
                        failed += 1
                        row_errors.append(f'행 {idx + 1}: pnum 숫자 변환 실패 ({child_pnum}, {parent_pnum})')
                        continue

                    cursor.execute(
                        "SELECT id FROM asset_relation WHERE child_pnum = %s AND relation_type = 'VM'",
                        (child_pnum,)
                    )
                    existing = cursor.fetchone()
                    if existing:
                        cursor.execute(
                            "UPDATE asset_relation SET parent_pnum = %s WHERE id = %s",
                            (parent_pnum, existing['id'])
                        )
                        updated += 1
                    else:
                        cursor.execute(
                            "INSERT INTO asset_relation (parent_pnum, child_pnum, relation_type) VALUES (%s, %s, 'VM')",
                            (parent_pnum, child_pnum)
                        )
                        inserted += 1
            conn.commit()
        finally:
            conn.close()

        _invalidate_asset_cache()
        resp = {
            'success': True,
            'message': f'처리 완료: 신규 {inserted}건 등록, {updated}건 수정, {failed}건 실패',
        }
        if row_errors:
            resp['row_errors'] = row_errors
        return jsonify(resp)
    except Exception as e:
        return jsonify({'success': False, 'message': f'처리 중 오류: {str(e)}'})


@asset_bp.route('/download_template')
def download_template():
    """자산 일괄 등록을 위한 엑셀 템플릿 다운로드"""
    # 템플릿 파일 경로
    template_path = os.path.join(os.getcwd(), 'exports', 'asset_template.xlsx')

    # 템플릿 파일 생성
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "자산 등록"

    # 스타일 정의
    header_font = Font(name='맑은 고딕', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # 헤더 행 추가
    headers = [
        '서버명*', 'IP 주소*', '호스트 이름', 'ITAM자산번호', '센터', '상면번호', '상단번호',
        '도메인*', '그룹*', '설치일자', '폐기일자', 'EOS 일자', 'EOSL 일자', '담당자(정)', '담당자(부)', '사용여부*',
        '서비스구분*', '전원이중화', 'PDU', 'OS*', 'OS버전', '제조사', '모델',
        '시리얼넘버', '현업담당자', '장비크기(U)', '물리코어', '메모리(GB)', '상위자산'
    ]

    # 필수 입력 필드 표시
    required_fields = ['서버명*', 'IP 주소*', '도메인*', '그룹*', '사용여부*', '서비스구분*', 'OS*']

    # 헤더 행 스타일 적용
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_alignment

    # 열 너비 설정
    for col_idx, header in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(len(header) * 1.5, 15)

    # 데이터 유효성 검사 설정
    # 도메인 드롭다운
    domain_options = execute_query("SELECT state FROM info_domain")
    domain_list = ','.join([f'"{option["state"]}"' for option in domain_options])
    domain_validation = DataValidation(type="list", formula1=f'"{domain_list}"', allow_blank=True)
    domain_validation.error = "올바른 도메인을 선택하세요."
    domain_validation.errorTitle = "입력 오류"
    ws.add_data_validation(domain_validation)
    domain_validation.add(f"H2:H1000")

    # 그룹 드롭다운 (도메인별로 다르므로 일반적인 목록만 제공)
    group_options = execute_query("SELECT DISTINCT state FROM info_group")
    group_list = ','.join([f'"{option["state"]}"' for option in group_options])
    group_validation = DataValidation(type="list", formula1=f'"{group_list}"', allow_blank=True)
    group_validation.error = "올바른 그룹을 선택하세요."
    group_validation.errorTitle = "입력 오류"
    ws.add_data_validation(group_validation)
    group_validation.add(f"I2:I1000")

    # 사용여부 드롭다운
    isoper_options = execute_query("SELECT state FROM info_isoper")
    isoper_list = ','.join([f'"{option["state"]}"' for option in isoper_options])
    isoper_validation = DataValidation(type="list", formula1=f'"{isoper_list}"', allow_blank=True)
    isoper_validation.error = "올바른 사용여부를 선택하세요."
    isoper_validation.errorTitle = "입력 오류"
    ws.add_data_validation(isoper_validation)
    isoper_validation.add(f"P2:P1000")

    # 서비스구분 드롭다운
    oper_options = execute_query("SELECT state FROM info_oper")
    oper_list = ','.join([f'"{option["state"]}"' for option in oper_options])
    oper_validation = DataValidation(type="list", formula1=f'"{oper_list}"', allow_blank=True)
    oper_validation.error = "올바른 서비스구분을 선택하세요."
    oper_validation.errorTitle = "입력 오류"
    ws.add_data_validation(oper_validation)
    oper_validation.add(f"Q2:Q1000")

    # 전원이중화 드롭다운
    power_options = execute_query("SELECT state FROM info_power")
    power_list = ','.join([f'"{option["state"]}"' for option in power_options])
    power_validation = DataValidation(type="list", formula1=f'"{power_list}"', allow_blank=True)
    power_validation.error = "올바른 전원이중화 옵션을 선택하세요."
    power_validation.errorTitle = "입력 오류"
    ws.add_data_validation(power_validation)
    power_validation.add(f"R2:R1000")

    # OS 드롭다운
    os_options = execute_query("SELECT state FROM info_os")
    os_list = ','.join([f'"{option["state"]}"' for option in os_options])
    os_validation = DataValidation(type="list", formula1=f'"{os_list}"', allow_blank=True)
    os_validation.error = "올바른 OS를 선택하세요."
    os_validation.errorTitle = "입력 오류"
    ws.add_data_validation(os_validation)
    os_validation.add(f"T2:T1000")

    # 안내 시트 추가
    guide_ws = wb.create_sheet(title="작성 가이드")
    guide_ws['A1'] = "자산 일괄 등록 양식 작성 가이드"
    guide_ws['A1'].font = Font(size=14, bold=True)
    guide_ws.merge_cells('A1:F1')

    guide_rows = [
        ["* 표시된 항목은 필수 입력 항목입니다."],
        ["날짜는 YYYY-MM-DD 형식으로 입력해주세요. (예: 2023-01-01)"],
        ["드롭다운 목록에서 선택 가능한 항목만 입력해주세요."],
        ["상위자산은 그룹이 '논리'인 경우에만 입력하며, 물리 서버의 자산번호를 입력해주세요."],
        [""],
        ["각 필드 설명:"],
        ["서버명", "서버의 이름을 입력합니다."],
        ["IP 주소", "서버의 IP 주소를 입력합니다."],
        ["호스트 이름", "서버의 호스트 이름을 입력합니다."],
        ["ITAM자산번호", "ITAM 시스템의 자산 번호를 입력합니다."],
        ["센터", "서버가 위치한 센터를 입력합니다."],
        ["상면번호", "서버의 상면 번호를 입력합니다. (예: 1F-R01-01)"],
        ["상단번호", "서버의 상단 번호를 입력합니다."],
        ["도메인", "드롭다운에서 도메인을 선택합니다. (서버, 스위치, 스토리지, 어플라이언스)"],
        ["그룹", "드롭다운에서 그룹을 선택합니다. (물리, 논리, L2, L3 등)"],
        ["설치일자", "서버의 설치 날짜를 입력합니다."],
        ["폐기일자", "서버의 폐기 날짜를 입력합니다."],
        ["EOS 일자", "서버의 EOS (End of Support) 날짜를 입력합니다."],
        ["EOSL 일자", "서버의 EOSL (End of Service Life) 날짜를 입력합니다."],
        ["담당자(정)", "서버의 담당자(정) 이름을 입력합니다."],
        ["담당자(부)", "서버의 담당자(부) 이름을 입력합니다."],
        ["사용여부", "드롭다운에서 사용 여부를 선택합니다. (사용, 미사용)"],
        ["서비스구분", "드롭다운에서 서비스 구분을 선택합니다. (운영, QA, 개발 등)"],
        ["전원이중화", "드롭다운에서 전원 이중화 여부를 선택합니다. (이중화, 단일)"],
        ["PDU", "서버가 연결된 PDU 정보를 입력합니다."],
        ["OS", "드롭다운에서 OS를 선택합니다. (Windows, Linux 등)"],
        ["OS버전", "서버의 OS 버전을 입력합니다."],
        ["제조사", "서버 제조사를 입력합니다."],
        ["모델", "서버 모델명을 입력합니다."],
        ["시리얼넘버", "서버 시리얼 번호를 입력합니다."],
        ["현업담당자", "서버의 현업 담당자를 입력합니다."],
        ["장비크기(U)", "서버의 장비 크기를 U 단위로 입력합니다."],
        ["물리코어", "서버의 물리 코어 수를 입력합니다."],
        ["메모리(GB)", "서버의 메모리 크기를 GB 단위로 입력합니다."],
        ["상위자산", "상위 자산의 자산고유번호(pnum)를 입력합니다. (논리 서버인 경우)"]
    ]

    for row in guide_rows:
        guide_ws.append(row)

    # 스타일 및 높이 조정
    for row in guide_ws.iter_rows(min_row=1, max_row=guide_ws.max_row):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.border = thin_border
    guide_ws.column_dimensions['A'].width = 25
    guide_ws.column_dimensions['B'].width = 60

    for row_num in range(1, guide_ws.max_row + 1):
        guide_ws.row_dimensions[row_num].height = 25

    # 템플릿 파일 저장
    wb.save(template_path)

    # 파일 다운로드 응답 생성
    return send_file(template_path, as_attachment=True, download_name='asset_template.xlsx')


@asset_bp.route('/import_asset', methods=['GET', 'POST'])
def import_asset():
    """자산 일괄 등록 처리"""
    if request.method == 'POST':
        # 파일 업로드 확인
        if 'file' not in request.files:
            flash('업로드할 파일이 없습니다.', 'error')
            return redirect(request.url)

        file = request.files['file']

        # 파일 유효성 검사
        if file.filename == '':
            flash('파일 이름이 없습니다.', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                # 파일 저장 (임시)
                filename = secure_filename(file.filename)
                filepath = os.path.join(os.getcwd(), 'uploads', filename)

                # uploads 폴더가 없으면 생성
                if not os.path.exists(os.path.dirname(filepath)):
                    os.makedirs(os.path.dirname(filepath))

                file.save(filepath)

                # 엑셀 파일 읽기
                wb = openpyxl.load_workbook(filepath)
                ws = wb['자산 등록']  # 시트 이름 확인

                # 데이터 읽기 (헤더 제외)
                data = []
                for row in ws.iter_rows(min_row=2, values_only=True):
                    data.append(row)

                # 데이터베이스 연결
                db = get_db_connection()
                try:
                    with db.cursor() as cursor:
                        # SQL 쿼리 작성
                        sql = """
                            INSERT INTO total_asset (
                                servername, ip, hostname, itamnum, center, loc1, loc2,
                                domain, `group`, datein, dateout, eos, eosl, charge, charge2,
                                isoper, oper, power, pdu, os, osver, maker, model,
                                serial, charge3, usize, cpucore, memory, vcenter, isfix, dateupdate
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """

                        # 데이터 변환 및 정리
                        processed_data = []
                        for row in data:
                            # 날짜 형식 변환
                            try:
                                datein = datetime.strptime(str(row[9]), '%Y-%m-%d').date() if row[9] else None
                            except (ValueError, TypeError):
                                datein = None

                            try:
                                dateout = datetime.strptime(str(row[10]), '%Y-%m-%d').date() if row[10] else None
                            except (ValueError, TypeError):
                                dateout = None

                            try:
                                eos = datetime.strptime(str(row[11]), '%Y-%m-%d').date() if row[11] else None
                            except (ValueError, TypeError):
                                eos = None

                            try:
                                eosl = datetime.strptime(str(row[12]), '%Y-%m-%d').date() if row[12] else None
                            except (ValueError, TypeError):
                                eosl = None

                            # 코드 값 변환 (state -> code)
                            try:
                                # 도메인
                                cursor.execute("SELECT domain FROM info_domain WHERE state = %s", (row[7],))
                                domain_value = cursor.fetchone()
                                domain = domain_value['domain'] if domain_value else None

                                # 그룹
                                cursor.execute("SELECT `group` FROM info_group WHERE state = %s AND domain = %s",
                                               (row[8], domain))
                                group_value = cursor.fetchone()
                                group = group_value['group'] if group_value else None

                                # 사용여부
                                cursor.execute("SELECT isoper FROM info_isoper WHERE state = %s", (row[15],))
                                isoper_value = cursor.fetchone()
                                isoper = isoper_value['isoper'] if isoper_value else None

                                # 서비스구분
                                cursor.execute("SELECT oper FROM info_oper WHERE state = %s", (row[16],))
                                oper_value = cursor.fetchone()
                                oper = oper_value['oper'] if oper_value else None

                                # 전원이중화
                                cursor.execute("SELECT power FROM info_power WHERE state = %s", (row[17],))
                                power_value = cursor.fetchone()
                                power = power_value['power'] if power_value else None

                                # OS
                                cursor.execute("SELECT os FROM info_os WHERE state = %s", (row[19],))
                                os_value = cursor.fetchone()
                                os_code = os_value['os'] if os_value else None

                            except Exception as e:
                                flash(f"코드 변환 중 오류 발생: {e}", 'error')
                                return redirect(request.url)

                            # vcenter 처리
                            vcenter = row[28] if row[28] else None

                            # isfix, dateupdate 설정
                            isfix = 0
                            dateupdate = datetime.now()

                            processed_data.append((
                                row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                                domain, group, datein, dateout, eos, eosl, row[13], row[14],
                                isoper, oper, power, row[18], os_code, row[20], row[21], row[22],
                                row[23], row[24], row[25], row[26], row[27], vcenter, isfix, dateupdate
                            ))

                        # 데이터 삽입
                        cursor.executemany(sql, processed_data)
                        db.commit()

                        # 성공 메시지
                        flash(f'{len(data)}개의 자산이 성공적으로 등록되었습니다.', 'success')

                        # 캐시 무효화
                        invalidate_cache_pattern('index_data')
                        invalidate_cache_pattern('asset_data')
                        invalidate_cache_pattern('asset_graph')

                except Exception as e:
                    db.rollback()
                    flash(f'데이터베이스 오류 발생: {e}', 'error')
                finally:
                    db.close()

                # 임시 파일 삭제
                os.remove(filepath)

            except Exception as e:
                flash(f'파일 처리 오류 발생: {e}', 'error')
                return redirect(request.url)

            return redirect(url_for('asset.index'))

        else:
            flash('잘못된 파일 형식입니다. 엑셀 파일(.xlsx)만 허용됩니다.', 'error')
            return redirect(request.url)

    return render_template('import.html')


@asset_bp.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    """AJAX를 통한 자산 일괄 등록 처리"""
    if 'excelFile' not in request.files:
        return jsonify({
            'success': False,
            'message': '업로드된 파일이 없습니다.'
        })

    file = request.files['excelFile']

    if file.filename == '':
        return jsonify({
            'success': False,
            'message': '선택된 파일이 없습니다.'
        })

    if not file.filename.endswith('.xlsx'):
        return jsonify({
            'success': False,
            'message': 'XLSX 형식의 파일만 업로드 가능합니다.'
        })

    # 임시 파일로 저장
    filename = secure_filename(file.filename)
    temp_path = os.path.join(os.getcwd(), 'uploads', filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    file.save(temp_path)

    try:
        # 엑셀 파일 로드
        wb = openpyxl.load_workbook(temp_path)
        ws = wb.active

        # 헤더 확인
        headers = [cell.value for cell in ws[1]]
        expected_headers = [
            '서버명*', 'IP 주소*', '호스트 이름', 'ITAM자산번호', '센터', '상면번호', '상단번호',
            '도메인*', '그룹*', '설치일자', '폐기일자', 'EOS 일자', 'EOSL 일자', '담당자(정)', '담당자(부)', '사용여부*',
            '서비스구분*', '전원이중화', 'PDU', 'OS*', 'OS버전', '제조사', '모델',
            '시리얼넘버', '현업담당자', '장비크기(U)', '물리코어', '메모리(GB)', '상위자산'
        ]

        if headers != expected_headers:
            return jsonify({
                'success': False,
                'message': '양식이 올바르지 않습니다. 제공된 템플릿을 사용해주세요.'
            })

        # 데이터 추출 및 검증
        data = []
        errors = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if all(cell is None or cell == '' for cell in row):
                continue  # 빈 행 무시

            # 필수 필드 검증
            if not row[0]:  # 서버명
                errors.append({'row': row_idx, 'column': '서버명*', 'message': '서버명은 필수 입력 항목입니다.'})

            if not row[1]:  # IP 주소
                errors.append({'row': row_idx, 'column': 'IP 주소*', 'message': 'IP 주소는 필수 입력 항목입니다.'})

            # 도메인 검증
            domain_value = row[7]
            if not domain_value:
                errors.append({'row': row_idx, 'column': '도메인*', 'message': '도메인은 필수 입력 항목입니다.'})
            else:
                domain_options = [option['state'] for option in execute_query("SELECT state FROM info_domain")]
                if domain_value not in domain_options:
                    errors.append(
                        {'row': row_idx, 'column': '도메인*', 'message': f'도메인은 {", ".join(domain_options)} 중 하나여야 합니다.'})

            # 그룹 검증
            group_value = row[8]
            if not group_value:
                errors.append({'row': row_idx, 'column': '그룹*', 'message': '그룹은 필수 입력 항목입니다.'})
            else:
                group_options = [option['state'] for option in execute_query("SELECT DISTINCT state FROM info_group")]
                if group_value not in group_options:
                    errors.append({'row': row_idx, 'column': '그룹*',
                                   'message': f'그룹은 {", ".join(group_options)} 중 하나여야 합니다.'})

            # 사용여부 검증
            isoper_value = row[15]
            if not isoper_value:
                errors.append({'row': row_idx, 'column': '사용여부*', 'message': '사용여부는 필수 입력 항목입니다.'})
            else:
                isoper_options = [option['state'] for option in execute_query("SELECT state FROM info_isoper")]
                if isoper_value not in isoper_options:
                    errors.append({'row': row_idx, 'column': '사용여부*',
                                   'message': f'사용여부는 {", ".join(isoper_options)} 중 하나여야 합니다.'})

            # 서비스구분 검증
            oper_value = row[16]
            if not oper_value:
                errors.append({'row': row_idx, 'column': '서비스구분*', 'message': '서비스구분은 필수 입력 항목입니다.'})
            else:
                oper_options = [option['state'] for option in execute_query("SELECT state FROM info_oper")]
                if oper_value not in oper_options:
                    errors.append({'row': row_idx, 'column': '서비스구분*',
                                   'message': f'서비스구분은 {", ".join(oper_options)} 중 하나여야 합니다.'})

            # OS 검증
            os_value = row[19]
            if not os_value:
                errors.append({'row': row_idx, 'column': 'OS*', 'message': 'OS는 필수 입력 항목입니다.'})
            else:
                os_options = [option['state'] for option in execute_query("SELECT state FROM info_os")]
                if os_value not in os_options:
                    errors.append(
                        {'row': row_idx, 'column': 'OS*', 'message': f'OS는 {", ".join(os_options)} 중 하나여야 합니다.'})

            # 전원이중화 검증 (필수는 아님)
            power_value = row[17]
            if power_value:
                power_options = [option['state'] for option in execute_query("SELECT state FROM info_power")]
                if power_value not in power_options:
                    errors.append({'row': row_idx, 'column': '전원이중화',
                                   'message': f'전원이중화는 {", ".join(power_options)} 중 하나여야 합니다.'})

            # 날짜 형식 검증
            datein = row[9]
            if datein:
                try:
                    if isinstance(datein, str):
                        datetime.strptime(datein, '%Y-%m-%d')
                    # 엑셀 날짜 형식인 경우는 이미 datetime 객체로 로드됨
                except ValueError:
                    errors.append({'row': row_idx, 'column': '설치일자', 'message': '설치일자는 YYYY-MM-DD 형식이어야 합니다.'})

            dateout = row[10]
            if dateout:
                try:
                    if isinstance(dateout, str):
                        datetime.strptime(dateout, '%Y-%m-%d')
                except ValueError:
                    errors.append({'row': row_idx, 'column': '폐기일자', 'message': '폐기일자는 YYYY-MM-DD 형식이어야 합니다.'})

            # 상위자산 검증 (그룹이 '논리'인 경우에만)
            if group_value == '논리':
                vcenter = row[28]  # 상위자산
                if vcenter:
                    # 상위자산이 존재하는지 확인
                    sql = "SELECT COUNT(*) as count FROM total_asset WHERE pnum = %s AND `group` = 0"
                    result = execute_query(sql, (vcenter,), fetch_all=False)
                    if result['count'] == 0:
                        errors.append(
                            {'row': row_idx, 'column': '상위자산', 'message': f'상위자산 번호 {vcenter}에 해당하는 물리 서버가 존재하지 않습니다.'})

            # 데이터 추가
            data.append({
                'servername': row[0],
                'ip': row[1],
                'hostname': row[2],
                'itamnum': row[3],
                'center': row[4],
                'loc1': row[5],
                'loc2': row[6],
                'domain': row[7],
                'group': row[8],
                'datein': row[9],
                'dateout': row[10],
                'eos': row[11],
                'eosl': row[12],
                'charge': row[13],
                'charge2': row[14],
                'isoper': row[15],
                'oper': row[16],
                'power': row[17],
                'pdu': row[18],
                'os': row[19],
                'osver': row[20],
                'maker': row[21],
                'model': row[22],
                'serial': row[23],
                'charge3': row[24],
                'usize': row[25],
                'cpucore': row[26],
                'memory': row[27],
                'vcenter': row[28] if row[8] == '논리' else None
            })

        # 오류가 있으면 처리 중단
        if errors:
            return jsonify({
                'success': False,
                'message': f'{len(errors)}개의 오류가 발견되었습니다. 수정 후 다시 시도해주세요.',
                'errors': errors
            })

        # 데이터 DB에 저장
        inserted_count = 0
        db = get_db_connection()
        try:
            with db.cursor() as cursor:
                for item in data:
                    # 코드값 조회
                    # domain
                    cursor.execute("SELECT domain FROM info_domain WHERE state = %s", (item['domain'],))
                    domain_value = cursor.fetchone()
                    domain = domain_value['domain'] if domain_value else 0

                    # group
                    cursor.execute("SELECT `group` FROM info_group WHERE state = %s AND domain = %s",
                                   (item['group'], domain))
                    group_value = cursor.fetchone()
                    group = group_value['group'] if group_value else 0

                    # isoper
                    cursor.execute("SELECT isoper FROM info_isoper WHERE state = %s", (item['isoper'],))
                    isoper_value = cursor.fetchone()
                    isoper = isoper_value['isoper'] if isoper_value else 0

                    # oper
                    cursor.execute("SELECT oper FROM info_oper WHERE state = %s", (item['oper'],))
                    oper_value = cursor.fetchone()
                    oper = oper_value['oper'] if oper_value else 0

                    # power
                    power = None
                    if item['power']:
                        cursor.execute("SELECT power FROM info_power WHERE state = %s", (item['power'],))
                        power_value = cursor.fetchone()
                        power = power_value['power'] if power_value else None

                    # os
                    cursor.execute("SELECT os FROM info_os WHERE state = %s", (item['os'],))
                    os_value = cursor.fetchone()
                    os_code = os_value['os'] if os_value else 0

                    # 날짜 처리
                    datein = item['datein']
                    if isinstance(datein, str) and datein:
                        datein = datetime.strptime(datein, '%Y-%m-%d').date()
                    elif isinstance(datein, datetime):
                        datein = datein.date()

                    dateout = item['dateout']
                    if isinstance(dateout, str) and dateout:
                        dateout = datetime.strptime(dateout, '%Y-%m-%d').date()
                    elif isinstance(dateout, datetime):
                        dateout = dateout.date()

                    eos = item['eos']
                    if isinstance(eos, str) and eos:
                        eos = datetime.strptime(eos, '%Y-%m-%d').date()
                    elif isinstance(eos, datetime):
                        eos = eos.date()

                    eosl = item['eosl']
                    if isinstance(eosl, str) and eosl:
                        eosl = datetime.strptime(eosl, '%Y-%m-%d').date()
                    elif isinstance(eosl, datetime):
                        eosl = eosl.date()

                    # 숫자 필드 처리
                    loc2 = int(item['loc2']) if item['loc2'] else None
                    usize = int(item['usize']) if item['usize'] else 1
                    cpucore = int(item['cpucore']) if item['cpucore'] else None
                    memory = int(item['memory']) if item['memory'] else None
                    vcenter = int(item['vcenter']) if item['vcenter'] else None

                    # 현재 시간
                    now = datetime.now()

                    # SQL 쿼리
                    sql = """INSERT INTO total_asset (
                        itamnum, servername, ip, hostname, center, loc1, loc2, `group`, vcenter, 
                        datein, dateout, eos, eosl, charge, charge2, isoper, oper, power, pdu, os, osver, 
                        maker, model, serial, domain, charge3, usize, cpucore, memory, 
                        isfix, dateinsert, dateupdate
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )"""

                    cursor.execute(sql, (
                        item['itamnum'], item['servername'], item['ip'], item['hostname'],
                        item['center'], item['loc1'], loc2, group, vcenter,
                        datein, dateout, eos, eosl, item['charge'], item['charge2'],
                        isoper, oper, power, item['pdu'], os_code, item['osver'],
                        item['maker'], item['model'], item['serial'], domain, item['charge3'],
                        usize, cpucore, memory, 0, now, now
                    ))

                    inserted_count += 1

                db.commit()
        except Exception as e:
            db.rollback()
            return jsonify({
                'success': False,
                'message': f'데이터 저장 중 오류가 발생했습니다: {str(e)}'
            })
        finally:
            db.close()

        # 캐시 무효화
        invalidate_cache_pattern('index_data')
        invalidate_cache_pattern('asset_data')
        invalidate_cache_pattern('asset_graph')

        return jsonify({
            'success': True,
            'message': f'{inserted_count}개의 자산이 성공적으로 등록되었습니다.',
            'details': {
                '총 등록 자산': inserted_count,
                '물리 서버': sum(1 for item in data if item['group'] == '물리'),
                '논리 서버': sum(1 for item in data if item['group'] == '논리')
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'파일 처리 중 오류가 발생했습니다: {str(e)}'
        })
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)


def allowed_file(filename):
    """허용된 파일 형식인지 검사"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}


# ─────────────────────────────────────────────
# 내부 헬퍼: 폼 데이터 수집 / 캐시 무효화
# ─────────────────────────────────────────────

def _parse_date(val):
    try:
        return datetime.strptime(val, '%Y-%m-%d').date() if val else None
    except ValueError:
        return None


def _collect_form_data() -> dict:
    """asset/form.html 의 POST 데이터를 asset_info 컬럼 dict 로 변환"""
    f = request.form
    return {
        "hostname":     f.get('hostname')    or None,
        "servername":   f.get('servername')  or None,
        "grp":          f.get('grp')         or None,
        "oper":         f.get('oper')        or None,
        "center":       f.get('center')      or None,
        "network_zone": f.get('network_zone') or None,
        "asset_type":   f.get('asset_type')  or None,
        "purpose":      ",".join(f.getlist('purpose')) or None,
        "loc1":         f.get('loc1')        or None,
        "loc2":         f.get('loc2', type=int),
        "usize":        f.get('usize', type=int) or 1,
        "maker":        f.get('maker')       or None,
        "model":        f.get('model')       or None,
        "serial":       f.get('serial')      or None,
        "os":           f.get('os')          or None,
        "osver":        f.get('osver')       or None,
        "cpucore":      f.get('cpucore', type=int),
        "cpusocket":    f.get('cpusocket', type=int),
        "memory":       f.get('memory', type=float),
        "datein":       _parse_date(f.get('datein')),
        "dateout":      _parse_date(f.get('dateout')),
        "hw_eos":       _parse_date(f.get('hw_eos')),
        "hw_eosl":      _parse_date(f.get('hw_eosl')),
        "status":       f.get('status')      or '사용',
        "importance":   f.get('importance')  or '일반',
        "power":        f.get('power')       or None,
        "watt":         f.get('watt', type=float),
        "ampere":       f.get('ampere', type=float),
        "charge":       f.get('charge')      or None,
        "charge2":      f.get('charge2')     or None,
        "charge3":      f.get('charge3')     or None,
        "memo":         f.get('memo')        or None,
        "dateupdate":   datetime.now(),
    }


def _collect_links() -> list:
    """폼에서 연계 정보 목록 수집. 동적 행 기반 (link_type_N, link_id_N)"""
    links = []
    idx = 0
    while True:
        stype = request.form.get(f'link_type_{idx}')
        sid   = request.form.get(f'link_id_{idx}')
        if stype is None:
            break
        if stype.strip() and sid.strip():
            links.append({"system_type": stype.strip(), "system_id": sid.strip()})
        idx += 1
    return links


def _collect_relations() -> list:
    """폼에서 자산관계 목록 수집. 동적 행 기반 (rel_parent_N, rel_type_N)"""
    relations = []
    idx = 0
    while True:
        parent = request.form.get(f'rel_parent_{idx}', type=int)
        rtype  = request.form.get(f'rel_type_{idx}')
        if request.form.get(f'rel_parent_{idx}') is None:
            break
        if parent and rtype:
            relations.append({"parent_pnum": parent, "relation_type": rtype.strip()})
        idx += 1
    return relations


def _invalidate_asset_cache():
    invalidate_cache_pattern('index_data')
    invalidate_cache_pattern('asset_data')
    invalidate_cache_pattern('asset_graph')
