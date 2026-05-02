from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from utils.db import execute_query
from utils.auto_register import handle_auto_registered_assets, auto_map_assets, sync_vmware_relation, sync_all_vmware_relations
from datetime import datetime
import json

vmware_bp = Blueprint('vmware', __name__)


@vmware_bp.route('/')
def index():
    """VMware 자산 관리 메인 페이지"""
    cluster_sql = """
    SELECT 
        va.cluster_host,
        COUNT(*) as vm_count,
        SUM(CASE WHEN va.status = '사용' THEN 1 ELSE 0 END) as active_count,
        SUM(CASE WHEN va.status = '폐기' THEN 1 ELSE 0 END) as inactive_count,
        SUM(CASE WHEN va.pnum IS NOT NULL THEN 1 ELSE 0 END) as mapped_count,
        SUM(CASE WHEN va.pnum IS NULL THEN 1 ELSE 0 END) as unmapped_count
    FROM vmware_assets va
    GROUP BY va.cluster_host
    ORDER BY va.cluster_host
    """
    clusters = execute_query(cluster_sql)

    # 전체 통계
    total_sql = """
    SELECT 
        COUNT(*) as total_vms,
        SUM(CASE WHEN status = '사용' THEN 1 ELSE 0 END) as total_active,
        SUM(CASE WHEN status = '폐기' THEN 1 ELSE 0 END) as total_inactive,
        SUM(CASE WHEN pnum IS NOT NULL THEN 1 ELSE 0 END) as total_mapped,
        SUM(CASE WHEN pnum IS NULL THEN 1 ELSE 0 END) as total_unmapped
    FROM vmware_assets
    """
    total_stats = execute_query(total_sql, fetch_all=False)

    # 최근 변경 이력 조회
    changes_sql = """
    SELECT 
        vc.change_id,
        vc.vm_name,
        vc.cluster_host,
        vc.hostname,
        vc.ip,
        vc.change_type,
        vc.review_status,
        vc.created_at,
        va.servername,
        va.parent_host
    FROM vmware_changes vc
    JOIN vmware_assets va ON vc.vm_id = va.vm_id
    WHERE vc.review_status = '확인필요'
    ORDER BY vc.created_at DESC
    LIMIT 50
    """
    recent_changes = execute_query(changes_sql)

    # VM 목록 조회
    vm_sql = """
        SELECT 
            va.*,
            ta.servername as mapped_servername,
            ta.itamnum as mapped_itamnum,
            vh.pnum as host_pnum,
            host_ta.servername as host_servername
        FROM vmware_assets va
        LEFT JOIN total_asset ta ON va.pnum = ta.pnum
        LEFT JOIN vmware_hosts vh ON (va.cluster_host = vh.cluster_host AND va.parent_host = vh.host_name)
        LEFT JOIN total_asset host_ta ON vh.pnum = host_ta.pnum
        ORDER BY va.hostname
        """
    vms = execute_query(vm_sql)

    return render_template('vmware/index.html',
                           clusters=clusters,
                           total_stats=total_stats,
                           recent_changes=recent_changes,
                           vms=vms)

@vmware_bp.route('/cluster/<cluster_host>')
def cluster_detail(cluster_host):
    """클러스터별 VM 목록"""
    # VM 목록 조회
    vm_sql = """
    SELECT 
        va.*,
        ta.servername as mapped_servername,
        ta.itamnum as mapped_itamnum,
        vh.pnum as host_pnum,
        host_ta.servername as host_servername
    FROM vmware_assets va
    LEFT JOIN total_asset ta ON va.pnum = ta.pnum
    LEFT JOIN vmware_hosts vh ON (va.cluster_host = vh.cluster_host AND va.parent_host = vh.host_name)
    LEFT JOIN total_asset host_ta ON vh.pnum = host_ta.pnum
    WHERE va.cluster_host = %s
    ORDER BY va.hostname
    """
    vms = execute_query(vm_sql, (cluster_host,))

    # 클러스터 통계
    stats_sql = """
    SELECT 
        COUNT(*) as total_vms,
        SUM(CASE WHEN status = '사용' THEN 1 ELSE 0 END) as active_count,
        SUM(CASE WHEN status = '폐기' THEN 1 ELSE 0 END) as inactive_count,
        SUM(CASE WHEN pnum IS NOT NULL THEN 1 ELSE 0 END) as mapped_count,
        SUM(CASE WHEN pnum IS NULL THEN 1 ELSE 0 END) as unmapped_count,
        SUM(cpu_cores) as total_cpu,
        SUM(memory_gb) as total_memory
    FROM vmware_assets
    WHERE cluster_host = %s
    """
    stats = execute_query(stats_sql, (cluster_host,), fetch_all=False)

    hosts_sql = """
    SELECT vh.*, ta.servername as host_servername, COUNT(va.vm_id) as vm_count
    FROM vmware_hosts vh
    LEFT JOIN total_asset ta ON vh.pnum = ta.pnum
    LEFT JOIN vmware_assets va ON (vh.cluster_host = va.cluster_host AND vh.host_name = va.parent_host)
    WHERE vh.cluster_host = %s
    GROUP BY vh.host_id, ta.servername
    ORDER BY vh.host_name
    """
    hosts = execute_query(hosts_sql, (cluster_host,))

    return render_template('vmware/cluster_detail.html',
                           cluster_host=cluster_host,
                           vms=vms,
                           stats=stats,
                           hosts=hosts)


@vmware_bp.route('/vm/<int:vm_id>')
def vm_detail(vm_id):
    """VM 상세 정보"""
    # VM 정보 조회
    vm_sql = """
    SELECT 
        va.*,
        ta.servername as mapped_servername,
        ta.itamnum as mapped_itamnum,
        ta.center as mapped_center,
        ta.loc1 as mapped_loc1
    FROM vmware_assets va
    LEFT JOIN total_asset ta ON va.pnum = ta.pnum
    WHERE va.vm_id = %s
    """
    vm = execute_query(vm_sql, (vm_id,), fetch_all=False)

    if not vm:
        flash('VM을 찾을 수 없습니다.', 'error')
        return redirect(url_for('vmware.index'))

    # 변경 이력 조회
    changes_sql = """
    SELECT *
    FROM vmware_changes
    WHERE vm_id = %s
    ORDER BY created_at DESC
    """
    changes = execute_query(changes_sql, (vm_id,))

    # changes JSON 파싱
    for change in changes:
        if change['changes']:
            try:
                change['changes_parsed'] = json.loads(change['changes'])
            except:
                change['changes_parsed'] = {}

    return render_template('vmware/vm_detail.html', vm=vm, changes=changes)


@vmware_bp.route('/map/<int:vm_id>', methods=['GET', 'POST'])
def map_asset(vm_id):
    """자산 맵핑"""
    if request.method == 'POST':
        pnum = request.form.get('pnum', type=int)

        if not pnum:
            flash('자산을 선택해주세요.', 'error')
            return redirect(request.url)

        execute_query("UPDATE vmware_assets SET pnum = %s WHERE vm_id = %s", (pnum, vm_id), fetch_all=False)

        # 맵핑 후 자산 관계(VM 상위) 즉시 동기화
        vm = execute_query("SELECT cluster_host, parent_host FROM vmware_assets WHERE vm_id = %s", (vm_id,), fetch_all=False)
        if vm:
            sync_vmware_relation(pnum, vm['cluster_host'], vm['parent_host'])

        flash('자산 맵핑이 완료되었습니다.', 'success')
        return redirect(url_for('vmware.vm_detail', vm_id=vm_id))

    # VM 정보 조회
    vm_sql = "SELECT * FROM vmware_assets WHERE vm_id = %s"
    vm = execute_query(vm_sql, (vm_id,), fetch_all=False)

    if not vm:
        flash('VM을 찾을 수 없습니다.', 'error')
        return redirect(url_for('vmware.index'))

    search_sql = """
    SELECT pnum, servername, hostname, ip, center, loc1
    FROM total_asset
    WHERE `group` = 0 AND (
        hostname LIKE %s OR 
        ip LIKE %s OR
        servername LIKE %s
    )
    LIMIT 20
    """
    search_term = f"%{vm['hostname']}%"
    ip_term = f"%{vm['ip']}%"
    suggested_assets = execute_query(search_sql, (search_term, ip_term, search_term))

    return render_template('vmware/map_asset.html', vm=vm, suggested_assets=suggested_assets)


@vmware_bp.route('/unmap/<int:vm_id>', methods=['POST'])
def unmap_asset(vm_id):
    """자산 맵핑 해제"""
    sql = "UPDATE vmware_assets SET pnum = NULL WHERE vm_id = %s"
    execute_query(sql, (vm_id,), fetch_all=False)

    flash('자산 맵핑이 해제되었습니다.', 'success')
    return redirect(url_for('vmware.vm_detail', vm_id=vm_id))


@vmware_bp.route('/auto_map', methods=['POST'])
def auto_map():
    """자동 맵핑 실행"""
    try:
        auto_map_assets()
        flash('자동 맵핑이 완료되었습니다.', 'success')
    except Exception as e:
        flash(f'자동 맵핑 중 오류가 발생했습니다: {str(e)}', 'error')

    return redirect(url_for('vmware.index'))


@vmware_bp.route('/sync_relations', methods=['POST'])
def sync_relations():
    """VMware 자산 연동: IP+hostname 매칭 → pnum 갱신 → 자산 관계(VM 상위) 일괄 동기화"""
    try:
        result = sync_all_vmware_relations()
        flash(
            f"자산 연동 완료: 매칭 {result['matched']}건 / "
            f"관계 동기화 {result['synced']}건 / "
            f"skip {result['skipped']}건 (host 미맵핑)",
            'success'
        )
    except Exception as e:
        flash(f'자산 연동 중 오류가 발생했습니다: {str(e)}', 'error')

    return redirect(url_for('vmware.index'))


@vmware_bp.route('/changes')
def changes():
    """변경 이력 목록"""
    # 필터링 옵션
    review_status = request.args.get('review_status', '확인필요')
    change_type = request.args.get('change_type', '')
    cluster_host = request.args.get('cluster_host', '')

    # 기본 쿼리
    sql = """
    SELECT 
        vc.*,
        va.servername,
        va.pnum,
        va.powerstate,
        va.parent_host
    FROM vmware_changes vc
    JOIN vmware_assets va ON vc.vm_id = va.vm_id
    LEFT JOIN vmware_exceptions ve ON (vc.vm_name = ve.vm_name AND vc.ip = ve.ip)
    WHERE ve.exception_id IS NULL
    """
    params = []

    if review_status:
        sql += " AND vc.review_status = %s"
        params.append(review_status)

    if change_type:
        sql += " AND vc.change_type = %s"
        params.append(change_type)

    if cluster_host:
        sql += " AND vc.cluster_host = %s"
        params.append(cluster_host)

    sql += " ORDER BY vc.created_at DESC"

    changes = execute_query(sql, params if params else None)

    # changes JSON 파싱
    for change in changes:
        if change['changes']:
            try:
                change['changes_parsed'] = json.loads(change['changes'])
            except:
                change['changes_parsed'] = {}

    # 클러스터 목록 (필터용)
    cluster_sql = "SELECT DISTINCT cluster_host FROM vmware_assets ORDER BY cluster_host"
    clusters = execute_query(cluster_sql)

    return render_template('vmware/changes.html',
                           changes=changes,
                           clusters=clusters,
                           review_status=review_status,
                           change_type=change_type,
                           cluster_host=cluster_host)


@vmware_bp.route('/review', methods=['POST'])
def review_changes():
    """변경 이력 검수"""
    action = request.form.get('action')
    selected_changes = request.form.getlist('selected_changes[]')

    if not selected_changes:
        flash('선택된 항목이 없습니다.', 'warning')
        return redirect(url_for('vmware.changes'))

    if action == "apply":
        # 반영 처리 - review_status를 '반영됨'으로 변경
        for change_id in selected_changes:
            update_sql = """
            UPDATE vmware_changes 
            SET review_status = '반영됨', reviewed_at = %s
            WHERE change_id = %s
            """
            execute_query(update_sql, (datetime.now(), change_id), fetch_all=False)

        flash(f'{len(selected_changes)}개 변경 이력이 반영되었습니다.', 'success')
        return redirect(url_for('vmware.changes'))

    if action == "exception":
        # 예외 처리 - review_status를 '예외'로 변경
        for change_id in selected_changes:
            # Get vm_name and IP from change record
            change_sql = "SELECT vm_name, ip FROM vmware_changes WHERE change_id = %s"
            change = execute_query(change_sql, (change_id,), fetch_all=False)

            if change:
                # Add to exception list
                exception_sql = """
                INSERT INTO vmware_exceptions (vm_name, ip, created_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE created_at = VALUES(created_at)
                """
                execute_query(exception_sql, (change['vm_name'], change['ip'], datetime.now()), fetch_all=False)

                # Mark change as exception
                update_sql = """
                UPDATE vmware_changes 
                SET review_status = '예외', reviewed_at = %s
                WHERE change_id = %s
                """
                execute_query(update_sql, (datetime.now(), change_id), fetch_all=False)

        flash(f'{len(selected_changes)}개 변경 이력이 예외 처리되었습니다.', 'success')
        return redirect(url_for('vmware.changes'))

    flash('알 수 없는 작업입니다.', 'error')
    return redirect(url_for('vmware.changes'))


@vmware_bp.route('/exceptions')
def exceptions():
    """예외 목록"""
    sql = """
    SELECT 
        ve.*,
        COUNT(vc.change_id) as blocked_changes
    FROM vmware_exceptions ve
    LEFT JOIN vmware_changes vc ON (ve.vm_name = vc.vm_name AND ve.ip = vc.ip AND vc.review_status = '확인필요')
    GROUP BY ve.exception_id
    ORDER BY ve.created_at DESC
    """
    exceptions = execute_query(sql)

    return render_template('vmware/exceptions.html', exceptions=exceptions)


@vmware_bp.route('/remove_exception/<int:exception_id>', methods=['POST'])
def remove_exception(exception_id):
    """예외 해제"""
    # Get exception details
    exception_sql = "SELECT vm_name, ip FROM vmware_exceptions WHERE exception_id = %s"
    exception = execute_query(exception_sql, (exception_id,), fetch_all=False)

    if not exception:
        flash('예외 항목을 찾을 수 없습니다.', 'error')
        return redirect(url_for('vmware.exceptions'))

    # Delete exception
    delete_sql = "DELETE FROM vmware_exceptions WHERE exception_id = %s"
    execute_query(delete_sql, (exception_id,), fetch_all=False)

    # Reset related changes back to '확인필요'
    reset_sql = """
    UPDATE vmware_changes 
    SET review_status = '확인필요', reviewed_at = NULL
    WHERE vm_name = %s AND ip = %s AND review_status = '예외'
    """
    execute_query(reset_sql, (exception['vm_name'], exception['ip']), fetch_all=False)

    flash(f"예외가 해제되었습니다: {exception['vm_name']} ({exception['ip']})", 'success')
    return redirect(url_for('vmware.exceptions'))


@vmware_bp.route('/search_assets')
def search_assets():
    """자산 검색 API"""
    term = request.args.get('term', '')

    if not term or len(term) < 2:
        return jsonify([])

    sql = """
    SELECT pnum, servername, hostname, ip, center, loc1
    FROM total_asset
    WHERE `group` = 1 AND (
        hostname LIKE %s OR 
        ip LIKE %s OR
        servername LIKE %s
    )
    LIMIT 20
    """

    search_term = f"%{term}%"
    results = execute_query(sql, (search_term, search_term, search_term))

    return jsonify(results)


@vmware_bp.route('/hosts')
def hosts():
    """Host 목록"""
    sql = """
    SELECT 
        vh.*,
        ta.servername as host_servername,
        ta.ip as host_ip,
        COUNT(va.vm_id) as vm_count
    FROM vmware_hosts vh
    LEFT JOIN total_asset ta ON vh.pnum = ta.pnum
    LEFT JOIN vmware_assets va ON (vh.cluster_host = va.cluster_host AND vh.host_name = va.parent_host)
    GROUP BY vh.host_id, ta.servername, ta.ip
    ORDER BY vh.cluster_host, vh.host_name
    """
    hosts = execute_query(sql)

    return render_template('vmware/hosts.html', hosts=hosts)


@vmware_bp.route('/map_host/<int:host_id>', methods=['GET', 'POST'])
def map_host(host_id):
    """Host 자산 맵핑"""
    if request.method == 'POST':
        pnum = request.form.get('pnum', type=int)

        if not pnum:
            flash('자산을 선택해주세요.', 'error')
            return redirect(request.url)

        # Host의 pnum 업데이트
        sql = "UPDATE vmware_hosts SET pnum = %s WHERE host_id = %s"
        execute_query(sql, (pnum, host_id), fetch_all=False)

        flash('Host 맵핑이 완료되었습니다.', 'success')
        return redirect(url_for('vmware.hosts'))

    # Host 정보 조회
    host_sql = """
    SELECT vh.*, ta.servername, ta.hostname, ta.ip
    FROM vmware_hosts vh
    LEFT JOIN total_asset ta ON vh.pnum = ta.pnum
    WHERE vh.host_id = %s
    """
    host = execute_query(host_sql, (host_id,), fetch_all=False)

    if not host:
        flash('Host를 찾을 수 없습니다.', 'error')
        return redirect(url_for('vmware.hosts'))

    return render_template('vmware/map_host.html', host=host)


@vmware_bp.route('/search_physical_assets')
def search_physical_assets():
    """물리 자산 검색 API (Host 맵핑용)"""
    term = request.args.get('term', '')

    if not term or len(term) < 2:
        return jsonify([])

    # 물리 서버만 검색 (group=0)
    sql = """
    SELECT pnum, servername, hostname, ip, center, loc1
    FROM total_asset
    WHERE `group` = 0 AND (
        hostname LIKE %s OR 
        ip LIKE %s OR
        servername LIKE %s
    )
    LIMIT 20
    """

    search_term = f"%{term}%"
    results = execute_query(sql, (search_term, search_term, search_term))

    return jsonify(results)
