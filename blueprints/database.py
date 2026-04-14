from datetime import date, datetime, timedelta
from typing import Tuple

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from utils import db, qo_db, dirst_db
import pandas as pd
import numpy as np 
import json


database_bp = Blueprint('database', __name__, url_prefix='/database')

# DB 자산 목록 조회 페이지
@database_bp.route('/list')
def database_index():
    return render_template('database/index.html')


# DB 자산 목록 조회
@database_bp.route('/', methods=['GET'])
def get_database():

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20)) 

    offset = (page - 1) * per_page

    params = {
        'page': page,
        'per_page': per_page,
        'offset': offset,
        'service_name': request.args.get('service_name', ''),
        'instance': request.args.get('instance', ''),
        'ip': request.args.get('ip', ''),
        'hostname': request.args.get('hostname', ''),
        'oper': request.args.getlist('oper'),
        'dbms': request.args.getlist('dbms'),
        'queryone_status': request.args.getlist('queryone_status'),
        'dbsafer_port': request.args.get('dbsafer_port', ''),
        'order': ''
    }

    return jsonify(get_database_list(params))


# DB 자산 추가 페이지
@database_bp.route('/add')
def add_database_index():
    return render_template('database/add.html')  


# DB 자산 추가
@database_bp.route('/', methods=['POST'])
def add_database():

    params = {
        'service_name': request.form.get('service_name'),
        'oper': request.form.get('oper'),
        'instance': request.form.get('instance'),
        'ip': request.form.get('ip', ''),
        'port': request.form.get('port', None),
        'dbsafer_port': request.form.get('dbsafer_port', None),
        'hostname': request.form.get('hostname', ''),
        'db_name': request.form.get('db_name'),
        'dbms': request.form.get('dbms'),
        'sw_idx': request.form.get('sw_idx', None),
        'memo': request.form.get('memo', ''),
        'characterset': request.form.get('characterset', None),
        'avl_cd': request.form.get('avl', None),
    }

    try:
        add_database_info(params)
        flash('✅ 성공적으로 저장되었습니다.', 'success')
    except Exception as e:
        flash(f'❌ 저장 중 오류가 발생했습니다: {str(e)}', 'danger')

    return redirect(url_for('database.database_index'))


# DB 자산 파일로 추가


# DB 자산 상세 정보
@database_bp.route('/<int:id>')
def database_detail(id):
        
    database_detail = get_database_info(id)

    hostname = database_detail['hostname']

    server_detail = get_server_info(hostname)
    queryone = get_queryone_by_seq(id)
    dbsafer = get_dbsafer_by_port(queryone[2])
    queryone_use_flag = queryone[4]
    dbsafer_use_flag = dbsafer[6]

    return render_template('database/detail.html', 
                            database=database_detail,
                            server=server_detail,
                            queryone_use_flag=queryone_use_flag,
                            dbsafer_use_flag=dbsafer_use_flag
                           )
    

# DB 자산 정보 수정
@database_bp.route('/<int:id>', methods=['POST'])
def update_database(id):

    params = {
        'service_name': request.form.get('service_name'),
        'oper': request.form.get('oper'),
        'instance': request.form.get('instance'),
        'ip': request.form.get('ip', ''),
        'port': request.form.get('port', None),
        'hostname': request.form.get('hostname', ''),
        'db_name': request.form.get('db_name'),
        'dbms': request.form.get('dbms'),
        'sw_idx': request.form.get('db_version', None),
        'memo': request.form.get('memo', ''),
        'characterset': request.form.get('characterset', None),
        'avl_cd': request.form.get('avl', None),
    }

    try:
        update_database_info_by_id(id, params)
        flash('✅ 성공적으로 저장되었습니다.', 'success')
    except Exception as e:
        flash(f'❌ 저장 중 오류가 발생했습니다: {str(e)}', 'danger')

    return redirect(url_for('database.database_detail', id=id))


# DB 자산 삭제
# @database_bp.route('/<int:id>', methods=['DELETE'])
# def delete_database(id):
#     return


# DB 버전 목록 조회
@database_bp.route('/version')
def get_database_version():

    dbms_type = request.args.get('dbms', '')
    database_version = get_database_version_list(dbms_type)

    return jsonify(database_version)


# 자산 연계 정보 조회
@database_bp.route('/server')
def get_server():
    hostname = request.args.get('hostname', '')

    return jsonify(get_server_info(hostname))


# 자산 연계 등록
@database_bp.route('/link', methods=['POST'])
def link_asset():
    return


# 자산 연계 해제
@database_bp.route('/unlink', methods=['POST'])
def unlink_asset():
    return


# 백업 대시보드
@database_bp.route('/dashboard')
def backup_dashboard():
    return render_template('database/backup.html')

# 백업 현황
@database_bp.route("/backup/list")
def get_backup_info():
    response = analyze_backup_intervals_v2_2(2)
    return jsonify(response)


# 전체 백업 정보 조회
@database_bp.route('/backup')
def get_total_backup():
    
    return


# 세부 백업 현황 조회
@database_bp.route('/backup/<int:id>')
def backup_detail(id):
    return



# multiselect 필터링
def selected_sql(column_name, selected_values, params):
    none_selected = 'N' in selected_values
    values = [v for v in selected_values if v != 'N']

    if values and none_selected:
        sql_cond = f" AND ({column_name} IN ({', '.join(['%s']*len(values))}) OR {column_name} IS NULL)"
        params.extend(values)
    elif values:
        sql_cond = f" AND {column_name} IN ({', '.join(['%s']*len(values))})"
        params.extend(values)
    elif none_selected:
        sql_cond = f" AND {column_name} IS NULL"
    else:
        sql_cond = ""

    return sql_cond

# DB 목록 필터링
def get_database_list(params=None):
    if params is None:
        params = {}

    data_sql = """
        SELECT d.id, d.service_name, o.oper, o.state as oper_state, d.isoper, i.state as isoper_state, d.dbms, d.sw_idx, s.sw_name, s.sw_version, a.ip, d.hostname, d.dbsafer_port, d.instance 
    """
    count_sql = "SELECT COUNT(*) as total"

    base_sql = """
         FROM total_database d
        LEFT JOIN info_software s ON d.sw_idx=s.sw_idx
        LEFT JOIN info_oper o ON d.oper=o.oper
        LEFT JOIN info_isoper i ON d.isoper=i.isoper
        LEFT JOIN total_asset a ON d.hostname=a.hostname
        WHERE 1=1
    """
    sql_params = []

    if params.get('service_name'):
        service_name = params.get('service_name')
        base_sql += " AND d.service_name LIKE %s"
        sql_params.append(f"%{service_name}%")

    if params.get('instance'):
        instance = params.get('instance')
        base_sql += " AND d.instance LIKE %s"
        sql_params.append(f'%{instance}%')

    if params.get('ip'):
        ip = params.get('ip')
        base_sql += " AND a.ip LIKE %s"
        sql_params.append(f"%{ip}%")

    if params.get('hostname'):
        hostname = params.get('hostname')
        base_sql += " AND d.hostname LIKE %s"
        sql_params.append(f"%{hostname}%")

    if params.get('oper'):
        base_sql += selected_sql('d.oper', params.get('oper'), sql_params)

    if params.get('dbms'):
        base_sql += selected_sql('d.dbms', params.get('dbms'), sql_params)

    # if queryone_status:
    #     base_sql += " AND queryone_status IN ({})".format(", ".join(["%s"] * len(dbms)))
    #     params.extend(dbms)

    if params.get('dbsafer_port'):
        dbsafer_port = params.get('dbsafer_port')
        base_sql += " AND d.dbsafer_port LIKE %s"
        sql_params.append(f'%{dbsafer_port}%')

    data_sql += base_sql
    count_sql += base_sql
    # total = db.execute_query(count_sql, sql_params)[0]['total']

    page = params.get('page')
    per_page = params.get('per_page')
    offset = params.get('offset')

    # data_sql += " LIMIT %s OFFSET %s"
    # sql_params.append(per_page)
    # sql_params.append(offset)

    database_list = db.execute_query(data_sql, sql_params)

    database_df = pd.DataFrame(database_list)

    # queryone merge
    queryone_df = get_queryone()
    queryone_df = queryone_df[['db_seq', 'port_no', 'use_flag']].reset_index(drop=True).rename(columns={'port_no': 'dbsafer_port', 'db_seq': 'id'})
    queryone_df['dbsafer_port'] = pd.to_numeric(queryone_df['dbsafer_port'], errors='coerce')
    database_df = database_df.merge(queryone_df, on=['id', 'dbsafer_port'], how='left')

    # queryone filter
    queryone_status = params.get('queryone_status')
    database_df = database_df[database_df['use_flag'].isin(queryone_status)]

    total = len(database_df)
    database_df = database_df.iloc[offset:offset+per_page]

    database_df = database_df.to_json(orient='records')

    return {
        "data": json.loads(database_df),
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page
    }



# 데이터베이스 정보 조회
def get_database_info(id):

    sql = """
        SELECT d.id, d.service_name, d.oper, d.db_name, d.dbms, d.sw_idx, s.sw_name, s.sw_version, d.ip, d.port, d.dbsafer_port, d.isoper, d.hostname, d.instance,
        d.avl_cd
        FROM total_database d
        LEFT JOIN info_software s ON d.sw_idx=s.sw_idx
        LEFT JOIN total_asset a ON d.hostname=a.hostname
        WHERE d.id=%s
    """
    database_info = db.execute_query(sql, id, False)

    return database_info


# 데이터베이스 추가
def add_database_info(params=None):

    if params is None:
        params = {}

    sql = """
        INSERT INTO total_database (service_name, ip, port, dbsafer_port, hostname, instance, db_name, dbms, sw_idx, oper, characterset, created_at, updated_at, memo, avl_cd)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    port = int(params.get('port')) if params.get('port') else None
    dbsafer_port = int(params.get('dbsafer_port')) if params.get('dbsafer_port') else None
    sw_idx = int(params.get('sw_idx')) if params.get('sw_idx') else None
    created_at = datetime.now()
    updated_at = datetime.now()

    return db.execute_query(sql, (
        params.get('service_name'),
        params.get('ip, None'),
        port,
        dbsafer_port,
        params.get('hostname', None),
        params.get('instance', None),
        params.get('db_name', None),
        params.get('dbms', None),
        sw_idx,
        params.get('oper', None),
        params.get('characterset', None),
        created_at,
        updated_at,
        params.get('memo', None),
        params.get('avl_cd', None)
    ))

# 데이터베이스 정보 수정
def update_database_info_by_id(id, params=None):

    if params is None:
        params = {}

    port = int(params.get('port')) if params.get('port') else None
    dbsafer_port = int(params.get('dbsafer_port')) if params.get('dbsafer_port') else None
    sw_idx = int(params.get('sw_idx')) if params.get('sw_idx') else None
    updated_at = datetime.now()
    
    sql = """
        UPDATE total_database 
        SET service_name=%s, oper=%s, instance=%s, ip=%s, port=%s, dbsafer_port=%s, hostname=%s,
        db_name=%s, dbms=%s, sw_idx=%s, memo=%s, characterset=%s, avl_cd=%s, updated_at=%s
        WHERE id=%s 
    """

    return db.execute_query(sql, (
        params.get('service_name'),
        params.get('oper'),
        params.get('instance'),
        params.get('ip'),
        port,
        dbsafer_port,
        params.get('hostname'),
        params.get('db_name'),
        params.get('dbms'),
        sw_idx,
        params.get('memo'),
        params.get('characterset'),
        params.get('avl_cd'),
        updated_at,
        id
    ))


# 서버 정보 조회
def get_server_info(hostname):

    base_sql = """
        SELECT a.pnum, a.hostname, a.ip, a.servername, a.center, a.loc1, a.loc2, a.group, a.vcenter, a.os, o.state, a.osver
        FROM total_asset a
        LEFT JOIN info_os o ON a.os=o.os
        WHERE 1=1
    """
    server_info = None

    if hostname:
        sql = base_sql + " AND hostname=%s"
        server_info = db.execute_query(sql, (hostname, ), False)

        # 논리 자산일 경우, 물리 자산 위치로 변경
        if server_info is not None and server_info['group'] == 1 and server_info['vcenter']:
            pnum = server_info['vcenter']

            sql = base_sql + " AND a.pnum=%s"
            rac_info = db.execute_query(sql, (pnum, ), False)

            server_info['loc1'] = rac_info['loc1']
            server_info['loc2'] = rac_info['loc2']

    return server_info


# database 버전 목록 조회
def get_database_version_list(dbms_type):

    sql = """
        SELECT s.sw_idx, s.sw_type, s.sw_name, s.sw_version, s.sw_eos, s.sw_eosl
        FROM info_software s
        WHERE sw_name=%s
    """
    version_list = db.execute_query(sql, dbms_type)

    return version_list

# 쿼리원 정보 가져오기
def get_queryone():

    sql = """
            SELECT db_seq, db_name, port_no, data_source, use_flag
            FROM da2s_db
        """
    queryone = qo_db.OrclSQLpy(sql)

    return queryone


# Queryone seq로 쿼리원 정보 찾기
def get_queryone_by_seq(id) -> Tuple[int, str, int, str, str]:

    sql = """
        SELECT db_seq, db_name, port_no, data_source, use_flag
        FROM da2s_db
        WHERE db_seq= :db_seq
    """
    queryone_info = qo_db.execute_query(sql, {'db_seq': id}, False)

    return queryone_info


def get_dbsafer_by_port(port):

    sql = """
        SELECT obj_seq, service_name, dbms, ip, port, dbsafer_port, status
        FROM tb_dbsafer_db_list_01
        WHERE dbsafer_port= :dbsafer_port
    """

    dbsafer_info = qo_db.execute_query(sql, {'dbsafer_port': port}, False)

    return dbsafer_info


# ITSM 데이터베이스 목록 가져오기
def get_itsm_list():
    return


# 백업 로그 분석
# - 백업 누락 확인, 백업 주기 계산, 백업 예정일 계산
# - 추후 분리 필요
def analyze_backup_intervals_v2_2(std_threshold=2):
    today = datetime.combine(date.today(), datetime.min.time())

    df = get_backup_by_recent_month()

    # summury용 분리
    cols = ['db_type', 'target_db', 'host_name', 'instance_name']
    database_df = df[cols].drop_duplicates().reset_index(drop=True)

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['instance_name', 'reg_dt', 'time'])
    df = df.drop_duplicates(subset=['instance_name', 'date'], keep='last')

    # 오늘자 백업 데이터 active 상태 확인
    active_df = df[df['reg_dt'].dt.date == today.date()]
    active_df = active_df.sort_values(by=['instance_name', 'time'], ascending=[True, False])
    active_df = active_df.drop_duplicates(subset=['instance_name'], keep='first')
    active_df = active_df[['instance_name', 'online_bk_status', 'time']].reset_index(drop=True)

    # 백업 요일 확인
    weekday_pattern = (
        df.groupby('instance_name')['weekday']
        .apply(lambda x: sorted(x.dropna().unique()) if x.dropna().size > 0 else [])
        .reset_index(name='backup_days')
    )
    df = df.merge(weekday_pattern, on='instance_name', how='left')

    # 기본 diff 계산
    df['backup_interval'] = df.groupby('instance_name')['date'].diff()
    df['backup_interval_days'] = df['backup_interval'].dt.days

    # DB별 평균/표준편차
    stats = df.groupby('instance_name')['backup_interval_days'].agg(['mean', 'std']).reset_index()
    df = df.merge(stats, on='instance_name', how='left')

    # 평균 백업 시작 시간 계산
    hour_df = df.groupby(['instance_name', 'hour']).size().reset_index(name="count")
    idx = hour_df.groupby('instance_name')['count'].idxmax()
    hour_df = hour_df.loc[idx].drop(columns='count').reset_index(drop=True)

    last_backup_df = (
        df.groupby('instance_name')['time']
        .max()
        .reset_index()
        .rename(columns={'time': 'last_backup_date'})
    )
    last_backup_df['last_backup_date_str'] = last_backup_df['last_backup_date'].dt.strftime('%Y-%m-%d %H:%M')

    database_df = database_df.merge(active_df, on='instance_name', how='left')
    database_df = database_df.merge(stats, on='instance_name', how='left')
    database_df = database_df.merge(weekday_pattern, on='instance_name', how='left')
    database_df = database_df.merge(hour_df, on='instance_name', how='left')
    database_df = database_df.merge(last_backup_df, on='instance_name', how='left')

    # DB별 평균 interval + 요일 패턴으로 주기 분류
    def classify_period(mean, weekdays):
        weekdays = [w for w in weekdays if w != 'unknown']
        weekday_count = len(weekdays)

        if pd.isna(mean):
            return 'unknown'
        # 한 주 내 7일 백업이면 daily
        if mean <= 1.5 and weekday_count == 7:
            return 'daily'
        # mean 1~2일, 요일 일부 빠짐 → weekly
        if mean < 3 and weekday_count < 7:
            return 'weekly'
        # mean 3~10일 → weekly
        if 3 <= mean <= 10:
            return 'weekly'
        # mean > 10 → monthly
        if mean > 10:
            return 'monthly'
        return 'unknown'

    database_df['backup_period_type'] = database_df.apply(
        lambda r: classify_period(r['mean'], r['backup_days']),
        axis=1
    )

    # 요일 패턴 merge
    df = df.merge(database_df[['instance_name', 'backup_period_type']], on='instance_name', how='left')

    # 기본 이상치 탐지
    df['is_abnormal'] = (
            (df['backup_interval_days'] > df['mean'] + std_threshold * df['std']) |
            (df['backup_interval_days'] < df['mean'] - std_threshold * df['std'])
    )

    # 요일 패턴 기반 이상치 보정
    def adjust_abnormal(row):
        # gap 없거나 1일이면 정상
        if pd.isna(row['backup_interval_days']) or row['backup_interval_days'] <= 1:
            return False

            # gap 시작일부터 종료일까지 요일 확인
        days_gap = pd.date_range(
            end=row['date'],
            periods=int(row['backup_interval_days']) + 1
        )

        gap_weekdays = [d.weekday() for d in days_gap]
        non_backup_days = set([0, 1, 2, 3, 4, 5, 6]) - set(row['backup_days'])

        # gap 내 모든 요일이 원래 백업 제외 요일이면 정상
        if all(day in non_backup_days for day in gap_weekdays[1:-1]):
            return False
        return True

    df['is_abnormal_adjusted'] = df.apply(adjust_abnormal, axis=1)

    # 누락 추정
    df['expected_missing_count'] = np.where(
        df['is_abnormal_adjusted'],
        (df['backup_interval_days'] / df['mean']).round() - 1,
        0
    )
    df['expected_missing_count'] = df['expected_missing_count'].clip(lower=0)

    # 정상 구간 평균 주기
    # normal_df = df[df['is_abnormal_adjusted'] == False]
    # avg_normal_interval = (
    #     normal_df.groupby(db_col)['backup_interval_days']
    #     .mean()
    #     .reset_index()
    #     .rename(columns={'backup_interval_days': 'avg_normal_backup_days'})
    # )

    # 입력 기준일 다음 백업일자 확인
    def get_next_backup_date(row, day):
        days = row['backup_days']
        if not isinstance(days, (list, tuple)) or len(days) == 0:
            return pd.NaT

        current_day = day if row['hour'] < 12 else day - timedelta(days=1)

        # 매일 백업이라면
        if row['backup_period_type'] == 'daily':
            return current_day + timedelta(days=1)

        # 매주 백업이라면
        elif row['backup_period_type'] == 'weekly':
            current_weekday = current_day.weekday()
            future_weekday = [d for d in days if d > current_weekday]

            delta = (future_weekday[0] - current_weekday) if future_weekday else (7 - current_weekday + days[0])
            return current_day + pd.Timedelta(days=delta)

        # 매달 백업이라면
        elif row['backup_period_type'] == 'monthly':
            return get_future_fourth_saturday(current_day)

    database_df['next_backup_date'] = database_df.apply(lambda x: get_next_backup_date(x, today), axis=1)
    database_df['next_backup_date_str'] = database_df['next_backup_date'].dt.strftime('%Y-%m-%d')

    # 전일 기준 다음 백업일 확인
    def check_backup_status(row):

        yesterday = today - timedelta(days=1)
        backup_date = get_next_backup_date(row, yesterday)

        return backup_date

    database_df['backup_check'] = database_df.apply(check_backup_status, axis=1)
    database_df['backup_check_str'] = database_df['backup_check'].dt.strftime('%Y-%m-%d')

    # 백업 실패로 초기화
    database_df['status'] = 'failed'

    # 백업 성공
    mask_success = (
            database_df['last_backup_date'].notna() &
            (database_df['backup_check'].dt.date == database_df['last_backup_date'].dt.date)
    )
    database_df.loc[mask_success, 'status'] = 'success'

    # 백업 대기
    mask_pending = (
            database_df['last_backup_date'].notna() &
            (database_df['backup_check'].dt.date == database_df['next_backup_date'].dt.date)
    )
    database_df.loc[mask_pending, 'status'] = 'pending'

    database_df = database_df.sort_values(by=['status', 'next_backup_date', 'last_backup_date', 'target_db'],
                                          key=lambda x: (x.map({'failed': 0, 'success': 1, 'pending': 3}))
                                            if x.name == 'status' else x)
    database = database_df.to_json(orient='records')

    data = {
        'updated_date': (today + timedelta(hours=10)).strftime('%Y-%m-%d %H:%M'),
        'summary': get_summary(database_df),
        'database': json.loads(database)
    }

    return data


# 백업 현황 요약
def get_summary(database_df):
    summary_df = database_df.groupby('status')['status'].count().reset_index(name='count')
    summary = summary_df.set_index('status')['count'].to_dict()
    summary['active'] = len(database_df[database_df['online_bk_status'] == 'ACTIVE'])

    return summary


# 최근 두 달간 백업 데이터 가져오기
# - 추후 날짜 구간 설정으로 변경
def get_backup_by_recent_month():
    sql = """
            SELECT reg_dt, db_type, target_db, host_name, instance_name, online_bk_status, time
            FROM TB_MON_DB_ALL_BACKUP_STATUS
        """

    df = dirst_db.OrclSQLpy(sql)

    df['reg_dt'] = pd.to_datetime(df['reg_dt'].astype(str))
    df['time'] = pd.to_datetime(df['time'].astype(str))

    before_month = datetime.today().date() - timedelta(days=62)
    df = df[df['reg_dt'].dt.date >= before_month]

    df['date'] = df['time'].dt.date
    df['date'] = pd.to_datetime(df['date'].astype(str))
    df['hour'] = df['time'].dt.hour
    df['weekday'] = df['date'].dt.weekday

    df['reg_dt_str'] = df['reg_dt'].dt.strftime('%y-%m-%d %H:%M:%S')
    df['time_str'] = df['time'].dt.strftime('%y-%m-%d %H:%M:%S')

    df['week_number'] = df['time'].dt.strftime('%U')

    return df


# 지정일보다 미래의 4째주 토요일 찾기
def get_future_fourth_saturday(current_day):
    saturday = get_fourth_saturday(current_day.year, current_day.month)

    if current_day >= saturday:
        first_day = date(current_day.year, current_day.month, 1)
        next_first_day = (first_day + timedelta(days=32)).replace(day=1)

        saturday = get_fourth_saturday(next_first_day.year, next_first_day.month)

    return saturday


# 4째주 토요일 찾기
# - 추후 요일, 주차 입력하면 날짜 확인할 수 있도록 함수 변경
def get_fourth_saturday(year, month):
    first_day = date(year, month, 1)

    first_saturday_day = 1 + (5 - first_day.weekday()) % 7
    if first_day.weekday() > 5:
        first_saturday_day = first_day.weekday() - 5 + 1

    fourth_saturday_day = first_saturday_day + 21

    return datetime.combine(date(year, month, fourth_saturday_day), datetime.min.time())


# status가 active인 DB 확인
def check_active(instance_name):
    # DB링크 생성

    # active 조회

    # 현재도 active인지 리턴

    #  sql = "SELECT COUNT(status) FROM V$BACKUP@DL_P_" + instance_name
    # + " WHERE status='ACTIVE'"

    # backup_status = dirst_db.execute_query(sql)
    # return backup_status => boolean 값으로

    return