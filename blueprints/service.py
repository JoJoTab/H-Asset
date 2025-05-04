from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from utils.db import execute_query, get_db_connection
from datetime import datetime

service_bp = Blueprint('service', __name__)


@service_bp.route('/')
def index():
    """서비스 관리 메인 페이지"""
    # 서비스 데이터 조회
    sql = """
        SELECT * FROM info_service 
        ORDER BY app_idx DESC
    """
    services = execute_query(sql)

    return render_template('service/index.html', services=services)


@service_bp.route('/add', methods=['GET', 'POST'])
def add_service():
    """서비스 추가 페이지 및 처리"""
    if request.method == 'POST':
        # 폼 데이터 가져오기
        app_servicecode = request.form.get('app_servicecode')
        app_name = request.form.get('app_name')
        app_group = request.form.get('app_group')
        app_domain = request.form.get('app_domain')
        app_appcode = request.form.get('app_appcode')

        # 필수 값 검증
        if not app_servicecode or not app_name:
            flash('서비스 코드와 서비스명은 필수 입력 항목입니다.', 'danger')
            return render_template('service/add.html')

        # 데이터 삽입
        sql = """
            INSERT INTO info_service 
            (app_servicecode, app_name, app_group, app_domain, app_appcode) 
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(sql, (app_servicecode, app_name, app_group, app_domain, app_appcode), fetch_all=False)

        flash('서비스가 성공적으로 추가되었습니다.', 'success')
        return redirect(url_for('service.index'))

    return render_template('service/add.html')


@service_bp.route('/edit/<int:app_idx>', methods=['GET', 'POST'])
def edit_service(app_idx):
    """서비스 수정 페이지 및 처리"""
    if request.method == 'POST':
        # 폼 데이터 가져오기
        app_servicecode = request.form.get('app_servicecode')
        app_name = request.form.get('app_name')
        app_group = request.form.get('app_group')
        app_domain = request.form.get('app_domain')
        app_appcode = request.form.get('app_appcode')

        # 필수 값 검증
        if not app_servicecode or not app_name:
            flash('서비스 코드와 서비스명은 필수 입력 항목입니다.', 'danger')
            return redirect(url_for('service.edit_service', app_idx=app_idx))

        # 데이터 업데이트
        sql = """
            UPDATE info_service 
            SET app_servicecode = %s, app_name = %s, app_group = %s, app_domain = %s, app_appcode = %s
            WHERE app_idx = %s
        """
        execute_query(sql, (app_servicecode, app_name, app_group, app_domain, app_appcode, app_idx), fetch_all=False)

        flash('서비스가 성공적으로 수정되었습니다.', 'success')
        return redirect(url_for('service.index'))

    # 서비스 데이터 조회
    sql = "SELECT * FROM info_service WHERE app_idx = %s"
    service = execute_query(sql, (app_idx,), fetch_all=False)

    if not service:
        flash('해당 서비스를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('service.index'))

    # 연계된 자산 정보 조회
    assets_sql = """
        SELECT ta.pnum, ta.servername, ta.ip, ta.hostname, 
               id.state AS domain_state, io_isoper.state AS isoper_state
        FROM total_service ts
        JOIN total_asset ta ON ts.service_pnum = ta.pnum
        JOIN info_domain id ON ta.domain = id.domain
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        WHERE ts.service_appidx = %s
    """
    linked_assets = execute_query(assets_sql, (app_idx,))

    return render_template('service/edit.html', service=service, linked_assets=linked_assets)


@service_bp.route('/delete/<int:app_idx>', methods=['POST'])
def delete_service(app_idx):
    """서비스 삭제 처리"""
    # 먼저 total_service에서 연계된 레코드 삭제
    delete_links_sql = "DELETE FROM total_service WHERE service_appidx = %s"
    execute_query(delete_links_sql, (app_idx,), fetch_all=False)

    # 서비스 삭제
    delete_service_sql = "DELETE FROM info_service WHERE app_idx = %s"
    execute_query(delete_service_sql, (app_idx,), fetch_all=False)

    flash('서비스가 성공적으로 삭제되었습니다.', 'success')
    return redirect(url_for('service.index'))


@service_bp.route('/search_assets', methods=['GET'])
def search_assets():
    """자산 검색 API"""
    search_term = request.args.get('term', '')

    if not search_term:
        return jsonify([])

    sql = """
        SELECT ta.pnum, ta.servername, ta.ip, ta.hostname,
               id.state AS domain_state, io_isoper.state AS isoper_state
        FROM total_asset ta
        JOIN info_domain id ON ta.domain = id.domain
        LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        WHERE ta.servername LIKE %s OR ta.ip LIKE %s OR ta.hostname LIKE %s
        LIMIT 50
    """

    search_param = f'%{search_term}%'
    assets = execute_query(sql, (search_param, search_param, search_param))

    return jsonify(assets)


@service_bp.route('/link_assets', methods=['POST'])
def link_assets():
    """자산과 서비스 연계 처리"""
    app_idx = request.form.get('app_idx', type=int)
    asset_pnums = request.form.getlist('asset_pnums[]')

    if not app_idx or not asset_pnums:
        return jsonify({"success": False, "message": "필요한 데이터가 누락되었습니다."})

    # 이미 연계된 자산 확인
    existing_sql = "SELECT service_pnum FROM total_service WHERE service_appidx = %s"
    existing_assets = execute_query(existing_sql, (app_idx,))
    existing_pnums = [asset['service_pnum'] for asset in existing_assets]

    # 새로 연계할 자산만 필터링
    new_pnums = [int(pnum) for pnum in asset_pnums if int(pnum) not in existing_pnums]

    if not new_pnums:
        return jsonify({"success": True, "message": "모든 자산이 이미 연계되어 있습니다.", "added": 0})

    # 새 연계 데이터 추가
    insert_sql = "INSERT INTO total_service (service_appidx, service_pnum) VALUES (%s, %s)"

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for pnum in new_pnums:
                cursor.execute(insert_sql, (app_idx, pnum))
            conn.commit()
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "message": f"{len(new_pnums)}개의 자산이 성공적으로 연계되었습니다.",
        "added": len(new_pnums)
    })


@service_bp.route('/unlink_asset', methods=['POST'])
def unlink_asset():
    """자산과 서비스 연계 해제 처리"""
    app_idx = request.form.get('app_idx', type=int)
    pnum = request.form.get('pnum', type=int)

    if not app_idx or not pnum:
        return jsonify({"success": False, "message": "필요한 데이터가 누락되었습니다."})

    # 연계 해제
    sql = "DELETE FROM total_service WHERE service_appidx = %s AND service_pnum = %s"
    execute_query(sql, (app_idx, pnum), fetch_all=False)

    return jsonify({"success": True, "message": "자산 연계가 해제되었습니다."})


@service_bp.route('/get_linked_services/<int:pnum>')
def get_linked_services(pnum):
    """자산에 연계된 서비스 조회"""
    sql = """
        SELECT is.*
        FROM total_service ts
        JOIN info_service is ON ts.service_appidx = is.app_idx
        WHERE ts.service_pnum = %s
    """
    services = execute_query(sql, (pnum,))

    return jsonify(services)
