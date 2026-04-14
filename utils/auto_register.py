import os
import time
import pandas as pd
import schedule
import threading
import shutil
import re
from datetime import datetime
from utils.db import execute_query, get_db_connection

# 자동 등록 설정
AUTO_REGISTER_FOLDER = 'autodata/vmware'
CHECK_INTERVAL_MINUTES = 60  # 매시간 정각마다 확인


def setup_auto_register():
    """자동 등록 기능 설정"""
    # 폴더가 없으면 생성
    if not os.path.exists(AUTO_REGISTER_FOLDER):
        os.makedirs(AUTO_REGISTER_FOLDER, exist_ok=True)

    schedule.every().hour.at(":30").do(check_rvtools_files)

    # 백그라운드 스레드에서 스케줄러 실행
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()

    print(f"자동 등록 기능이 설정되었습니다. {AUTO_REGISTER_FOLDER} 폴더를 매시간 정각마다 확인합니다.")

    # 시작 시 한 번 실행
    check_rvtools_files()


def run_scheduler():
    """스케줄러 실행"""
    while True:
        schedule.run_pending()
        time.sleep(1)


def check_rvtools_files():
    """RVTools 파일 확인 및 처리"""
    print(f"[{datetime.now()}] RVTools 파일 확인 중...")

    # 폴더 내 모든 파일 확인
    for filename in os.listdir(AUTO_REGISTER_FOLDER):
        if filename.startswith('VMList_') and filename.endswith('.xlsx'):
            file_path = os.path.join(AUTO_REGISTER_FOLDER, filename)
            print(f"VMware 파일 발견: {filename}")

            try:
                # 파일명에서 클러스터 호스트 추출
                cluster_host = extract_cluster_host(filename)

                # 파일 처리
                process_rvtools_file(file_path, cluster_host)

                shutil.move(file_path, os.path.join(AUTO_REGISTER_FOLDER + '/VMList_old', filename))
                #os.remove(file_path)
                print(f"파일 처리 완료 및 삭제: {filename}")
            except Exception as e:
                print(f"파일 처리 중 오류 발생: {str(e)}")
                try:
                    os.remove(file_path)
                    print(f"오류 발생한 파일 삭제: {filename}")
                except:
                    pass


def extract_cluster_host(filename):
    """파일명에서 클러스터 호스트 추출"""
    # VMList_{IP or Domain}_YYYY-MM-DD_HH-mm-ss.xlsx 형식
    pattern = r'VMList_(.+?)_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xlsx'
    match = re.match(pattern, filename)
    if match:
        return match.group(1)
    return None


def process_rvtools_file(file_path, cluster_host):
    """RVTools 파일 처리"""
    try:
        # Excel 파일 로드
        df = pd.read_excel(file_path, sheet_name='vInfo')

        required_columns = [
            'VM', 'DNS Name', 'Powerstate', 'CPUs', 'Memory',
            'Primary IP Address', 'Annotation', 'Host',
            'OS according to the configuration file', 'OS according to the VMware Tools',
            'Creation date'
        ]

        # 필요한 열이 모두 있는지 확인
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"경고: 다음 열이 Excel 파일에 없습니다: {', '.join(missing_columns)}")

        # 각 VM에 대해 처리
        for _, row in df.iterrows():
            process_vm_data(row, cluster_host)

        return True
    except Exception as e:
        print(f"Excel 파일 처리 중 오류: {str(e)}")
        raise


def process_vm_data(row, cluster_host):
    """VM 데이터 처리"""
    vm_name = row.get('VM')
    if pd.isna(vm_name):
        print(f"VM 이름이 없는 행 건너뜀")
        return

    hostname = row.get('DNS Name') if pd.notna(row.get('DNS Name')) else vm_name

    powerstate = row.get('Powerstate')
    cpus = row.get('CPUs')
    memory = row.get('Memory')  # MB 단위
    ip_address = row.get('Primary IP Address')
    servername = row.get('Annotation')
    host = row.get('Host')

    if host and not pd.isna(host):
        update_or_create_host(cluster_host, host)

    os_version = row.get('OS according to the VMware Tools')
    if pd.isna(os_version):
        os_version = row.get('OS according to the configuration file')

    creation_date = row.get('Creation Date')
    if pd.notna(creation_date):
        if isinstance(creation_date, str):
            try:
                creation_date = datetime.strptime(creation_date, '%Y-%m-%d %H:%M:%S').date()
            except:
                try:
                    creation_date = datetime.strptime(creation_date, '%Y-%m-%d').date()
                except:
                    creation_date = None
        elif isinstance(creation_date, datetime):
            creation_date = creation_date.date()
    else:
        creation_date = None

    # 빈 값 처리
    if pd.isna(ip_address):
        print(f"IP 주소가 없는 VM None 처리: {vm_name}")
        ip_address="None"

    is_powered_on = (powerstate == 'poweredOn')

    # 메모리 GB로 변환 (MB에서)
    memory_gb = int(memory / 1024) if not pd.isna(memory) else None

    sql = """
    SELECT * FROM vmware_assets 
    WHERE vm_name = %s AND cluster_host = %s
    """
    existing_vms = execute_query(sql, (vm_name, cluster_host))

    if existing_vms:
        # 기존 VM이 있으면 업데이트
        update_existing_vm(existing_vms[0], vm_name, hostname, ip_address, servername,
                           is_powered_on, cpus, memory_gb, host, os_version,
                           creation_date, cluster_host, powerstate)
    else:
        # if not is_powered_on:
        #     print(f"poweredOff 상태의 VM은 신규 등록하지 않음: {vm_name} ({ip_address})")
        #     return

        # 새 VM 추가
        add_new_vm(vm_name, hostname, ip_address, servername, is_powered_on,
                   cpus, memory_gb, host, os_version, creation_date, cluster_host)


def update_or_create_host(cluster_host, host_name):
    """Host 정보 업데이트 또는 생성"""
    now = datetime.now()

    # Host가 존재하는지 확인
    check_sql = """
    SELECT host_id FROM vmware_hosts 
    WHERE cluster_host = %s AND host_name = %s
    """
    existing = execute_query(check_sql, (cluster_host, host_name), fetch_all=False)

    if existing:
        # 마지막 확인 시간 업데이트
        update_sql = """
        UPDATE vmware_hosts 
        SET last_seen = %s 
        WHERE cluster_host = %s AND host_name = %s
        """
        execute_query(update_sql, (now, cluster_host, host_name), fetch_all=False)
    else:
        # 새 Host 생성
        insert_sql = """
        INSERT INTO vmware_hosts (cluster_host, host_name, last_seen, created_at)
        VALUES (%s, %s, %s, %s)
        """
        execute_query(insert_sql, (cluster_host, host_name, now, now), fetch_all=False)
        print(f"새 Host 추가: {host_name} (클러스터: {cluster_host})")


def update_existing_vm(vm, vm_name, hostname, ip_address, servername, is_powered_on, cpus, memory_gb, host, os_version,
                       creation_date, cluster_host, powerstate):
    """기존 VM 업데이트"""
    # 변경 사항 확인
    changes = {}
    change_type = 'modified'  # 기본값

    if vm['cluster_host'] != cluster_host:
        changes['cluster_host'] = {'old': vm['cluster_host'], 'new': cluster_host}

    if vm['parent_host'] != host and not pd.isna(host):
        changes['parent_host'] = {'old': vm['parent_host'], 'new': host}

    if vm['hostname'] != hostname:
        changes['hostname'] = {'old': vm['hostname'], 'new': hostname}

    if vm['ip'] != ip_address:
        changes['ip'] = {'old': vm['ip'], 'new': ip_address}

    if vm['cpu_cores'] != cpus and not pd.isna(cpus):
        changes['cpu_cores'] = {'old': vm['cpu_cores'], 'new': cpus}

    if vm['memory_gb'] != memory_gb and not pd.isna(memory_gb):
        changes['memory_gb'] = {'old': vm['memory_gb'], 'new': memory_gb}

    # OS 버전 변경 확인
    # if vm['os_version'] != os_version and not pd.isna(os_version):
    #     changes['os_version'] = {'old': vm['os_version'], 'new': os_version}

    if vm['powerstate'] != powerstate:
        changes['powerstate'] = {'old': vm['powerstate'], 'new': powerstate}
        if powerstate == 'poweredOff':
            change_type = 'deleted'
            changes['status'] = {'old': vm['status'], 'new': '폐기'}
        elif powerstate == 'poweredOn' and vm['powerstate'] == 'poweredOff':
            changes['status'] = {'old': vm['status'], 'new': '사용'}

    # 변경 사항이 있으면 업데이트
    if changes:
        update_data = {
            'hostname': hostname,
            'ip': ip_address,
            'cluster_host': cluster_host,
            'last_updated': datetime.now()
        }

        if not pd.isna(cpus):
            update_data['cpu_cores'] = cpus
        if not pd.isna(memory_gb):
            update_data['memory_gb'] = memory_gb
        if not pd.isna(host):
            update_data['parent_host'] = host
        if not pd.isna(os_version):
            update_data['os_version'] = os_version
        if powerstate:
            update_data['powerstate'] = powerstate
            if powerstate == 'poweredOff':
                update_data['status'] = '폐기'
            elif powerstate == 'poweredOn':
                update_data['status'] = '사용'

        # SQL 쿼리 생성
        set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(vm['vm_id'])  # WHERE 조건용

        sql = f"UPDATE vmware_assets SET {set_clause} WHERE vm_id = %s"

        # 쿼리 실행
        execute_query(sql, values, fetch_all=False)

        if 'parent_host' in changes and vm['pnum']:
            update_vcenter_from_host(vm['pnum'], host, cluster_host)

        if not is_vm_exception(vm_name, ip_address):
            save_change_history(vm['vm_id'], vm_name, cluster_host, hostname, ip_address, change_type, changes)

        print(f"VM 업데이트 (vm_id: {vm['vm_id']}, vm_name: {vm_name}): {len(changes)}개 항목 변경")


def add_new_vm(vm_name, hostname, ip_address, servername, is_powered_on, cpus, memory_gb, host, os_version,
               creation_date, cluster_host):
    """새 VM 추가"""
    # 현재 시간
    now = datetime.now()

    is_exception = is_vm_exception(vm_name, ip_address)

    # SQL 쿼리
    sql = """
    INSERT INTO vmware_assets (
        vm_name, cluster_host, hostname, ip, servername, cpu_cores, memory_gb, 
        parent_host, os_version, install_date, powerstate, status, 
        pnum, last_updated, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    # 값 설정
    values = (
        vm_name,  # Added vm_name as first value
        cluster_host,
        hostname,
        ip_address,
        servername if not pd.isna(servername) else hostname,
        cpus if not pd.isna(cpus) else None,
        memory_gb if not pd.isna(memory_gb) else None,
        host if not pd.isna(host) else None,
        os_version if not pd.isna(os_version) else None,
        creation_date,
        'poweredOn' if is_powered_on else 'poweredOff',
        '사용' if is_powered_on else '폐기',
        None,  # pnum - 아직 맵핑되지 않음
        now,
        now
    )

    # 쿼리 실행
    result = execute_query(sql, values, fetch_all=False)

    # 새로 추가된 VM의 ID 가져오기
    vm_id_sql = """SELECT vm_id FROM vmware_assets WHERE vm_name = %s AND cluster_host = %s"""
    vm_id_result = execute_query(vm_id_sql, (vm_name, cluster_host), fetch_all=False)
    vm_id = vm_id_result['vm_id'] if vm_id_result else None
    print(vm_id, is_exception)
    if vm_id and not is_exception:
        save_change_history(vm_id, vm_name, cluster_host, hostname, ip_address, 'new', {
            'servername': servername,
            'cpu_cores': cpus,
            'memory_gb': memory_gb,
            'os_version': os_version,
            'parent_host': host
        })

    print(f"새 VM 추가: {vm_name} ({hostname}, {ip_address})")


def is_vm_exception(vm_name, ip_address):
    """VM이 예외 목록에 있는지 확인"""
    sql = """
    SELECT exception_id FROM vmware_exceptions 
    WHERE vm_name = %s AND ip = %s
    """
    result = execute_query(sql, (vm_name, ip_address), fetch_all=False)
    return result is not None


def save_change_history(vm_id, vm_name, cluster_host, hostname, ip_address, change_type, changes):
    """변경 이력 저장"""
    sql = """
    INSERT INTO vmware_changes (
        vm_id, vm_name, cluster_host, hostname, ip, change_type, changes, 
        review_status, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    # changes를 JSON 문자열로 변환
    import json
    changes_json = json.dumps(changes, default=str, ensure_ascii=False)

    values = (
        vm_id,
        vm_name,  # Added vm_name
        cluster_host,
        hostname,
        ip_address,
        change_type,  # 'new', 'modified', 'deleted'
        changes_json,
        '확인필요',  # 기본 상태
        datetime.now()
    )

    execute_query(sql, values, fetch_all=False)


def auto_map_assets():
    """자동 자산 맵핑 - Hostname과 IP가 모두 같은 자산 자동 연결"""
    sql = """
    UPDATE vmware_assets va
    JOIN total_asset ta ON (va.hostname = ta.hostname AND va.ip = ta.ip)
    SET va.pnum = ta.pnum
    WHERE va.pnum IS NULL
    """

    result = execute_query(sql, fetch_all=False)

    print("자동 자산 맵핑 완료")


def update_vcenter_from_host(vm_pnum, host_name, cluster_host):
    """Host의 pnum을 사용하여 VM 자산의 vcenter 업데이트"""
    pass


def handle_auto_registered_assets(action, selected_assets):
    """자동 등록된 자산 처리"""
    if not selected_assets:
        return False, "선택된 자산이 없습니다."

    if action == "exception":
        # 예외 처리
        for vm_id in selected_assets:
            update_change_sql = """
            UPDATE vmware_changes 
            SET review_status = '예외', reviewed_at = %s
            WHERE vm_id = %s AND review_status = '확인필요'
            """
            execute_query(update_change_sql, (datetime.now(), vm_id), fetch_all=False)

        return True, f"{len(selected_assets)}개 VM이 예외 처리되었습니다."

    return False, "잘못된 작업입니다."
