from datetime import datetime
from typing import Tuple

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from utils import db, qo_db, dirst_db
import pandas as pd
import numpy as np 


database_bp = Blueprint('database', __name__, url_prefix='/database')

# DB 자산 목록 조회 페이지
@database_bp.route('/index')
def database_index():
    return render_template('database/index.html')


# DB 자산 목록 조회
@database_bp.route('/', methods=['GET'])
def get_database():

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20)) 

    offset = (page - 1) * per_page

    service_name = request.args.get('service_name', '')
    instance = request.args.get('instance', '')
    ip = request.args.get('ip', '')
    hostname = request.args.get('hostname', '')
    oper = request.args.getlist('oper')
    dbms = request.args.getlist('dbms')
    status = request.args.getlist('status', '')   # isoper
    queryone_status = request.args.getlist('queryone_status')
    dbsafer_port = request.args.get('dbsafer_port', '')
    
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
    params = []

    if service_name:
        base_sql += " AND d.service_name LIKE %s"
        params.append(f"%{service_name}%")

    if instance:
        base_sql += " AND d.instance LIKE %s"
        params.append(f'%{instance}%')

    if ip:
        base_sql += " AND a.ip LIKE %s"
        params.append(f"%{ip}%")

    if hostname:
        base_sql += " AND d.hostname LIKE %s"
        params.append(f"%{hostname}%")  

    if oper:
        base_sql += selected_sql('d.oper', oper, params)
    
    if dbms:
        base_sql += selected_sql('d.dbms', dbms, params)

    # if status:
    #     base_sql += " AND s.sw_name IN ({})".format(", ".join(["%s"] * len(status)))
    #     params.extend(status)

    # if queryone_status:
    #     base_sql += " AND queryone_status IN ({})".format(", ".join(["%s"] * len(dbms)))
    #     params.extend(dbms)
    
    if dbsafer_port:
        base_sql += " AND d.dbsafer_port LIKE %s"
        params.append(f'%{dbsafer_port}%')

    data_sql += base_sql
    count_sql += base_sql
    total = db.execute_query(count_sql, params)[0]['total']

    data_sql += " LIMIT %s OFFSET %s"
    params.append(per_page)
    params.append(offset)

    database_list = db.execute_query(data_sql, params)

    return jsonify({
        "data": database_list,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page
    })


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
    dbsafer_port = database_detail['dbsafer_port']

    server_detail = get_server_info(hostname)
    queryone = get_queryone(dbsafer_port)
    use_flag = queryone[4]

    # use_flag = 'ENABLE'

    return render_template('database/detail.html', 
                            database=database_detail,
                            server=server_detail,
                            use_flag=use_flag)
    

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
@database_bp.route('/backup/dashboard')
def backup_dashboard():
    return render_template('database/backup.html')

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

    sql = """
        SELECT a.pnum, a.hostname, a.ip, a.servername, a.center, a.loc1, a.loc2, a.os, o.state, a.osver
        FROM total_asset a
        LEFT JOIN info_os o ON a.os=o.os
        WHERE 1=1
    """
    server_info = None
    if hostname:
        sql += " AND hostname=%s"
        server_info = db.execute_query(sql, (hostname, ), False)
    
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

# 쿼리원
def get_queryone(port_no) -> Tuple[int, str, int, str, str]:

    sql = """
        SELECT db_seq, db_name, port_no, data_source, use_flag
        FROM da2s_db
        WHERE port_no= :port_no
    """
    queryone_info = qo_db.execute_query(sql, {'port_no': port_no}, False)

    return queryone_info

# ITSM 데이터베이스 목록 가져오기
def get_itsm_list():
    return


# 일별 데이터베이스 백업 현황
def get_backup_by_date():

    sql = """
        SELECT id, reg_dt, db_type, target_db, host_name, instance_name, online_bk_status, time
        FROM hli_asset.database_backup_status
        WHERE red_gt=

    """

    return


# 백업 DB 목록 확인
def backup_db_list():

    sql = """
        SELECT id, reg_dt, db_type, target_db, host_name, instance_name, online_bk_status, time
        FROM hli_asset.database_backup_status
        WHERE red_gt=
    """


    return


# 백업 주기 확인
# 최근 3개월 백업 현황 가져오기?
@database_bp.route("/backup/list")
def cal_backup_route():

    # sql = """
    #     SELECT reg_dt, db_type, target_db, host_name, instance_name, online_bk_status, time
    #     FROM TB_MON_DB_ALL_BACKUP_STATUS
    # """

    sql = """
        SELECT *
        FROM TB_MON_DB_ALL_BACKUP_STATUS
    """

    backup = dirst_db.execute_query(sql)
    df = pd.DataFrame(backup)
    
    #df['time'] = pd.to_datetime(df['time'], errors='coerce')
    # df['time'] = pd.to_datetime(df['time'].astype(str), errors='coerce')
    # df['date'] = df['time'].dt.date
    # df['weekday'] = df['time'].dt.weekday  # 요일 (e.g., Monday)
    # df['hour'] = df['time'].dt.hour

    #df[df['reg_dt'] == '2025-09']

    # df = df.where(pd.notnull(df), None)


    return jsonify(df.to_json(orient='records'))


# 매일 백업되는지 확인
def check_daily_backup():



    return