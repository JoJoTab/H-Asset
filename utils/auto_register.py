import os
import time
import pandas as pd
import schedule
import threading
from datetime import datetime
from utils.db import execute_query, get_db_connection

# 자동 등록 설정
AUTO_REGISTER_FOLDER = 'autodata/vmware'
CHECK_INTERVAL = 10  # 10분마다 확인


def setup_auto_register():
    """자동 등록 기능 설정"""
    # 폴더가 없으면 생성
    if not os.path.exists(AUTO_REGISTER_FOLDER):
        os.makedirs(AUTO_REGISTER_FOLDER, exist_ok=True)

    # 스케줄러 설정
    schedule.every(CHECK_INTERVAL).minutes.do(check_rvtools_files)

    # 백그라운드 스레드에서 스케줄러 실행
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()

    print(f"자동 등록 기능이 설정되었습니다. {AUTO_REGISTER_FOLDER} 폴더를 {CHECK_INTERVAL}분마다 확인합니다.")


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
        if filename.startswith('RVTools') and filename.endswith('.xlsx'):
            file_path = os.path.join(AUTO_REGISTER_FOLDER, filename)
            print(f"RVTools 파일 발견: {filename}")

            try:
                # 파일 처리
                process_rvtools_file(file_path)

                # 처리 후 파일 삭제
                os.remove(file_path)
                print(f"파일 처리 완료 및 삭제: {filename}")
            except Exception as e:
                print(f"파일 처리 중 오류 발생: {str(e)}")


def process_rvtools_file(file_path):
    """RVTools 파일 처리"""
    try:
        # Excel 파일 로드
        df = pd.read_excel(file_path, sheet_name='vInfo')

        # 필요한 열만 선택
        required_columns = [
            'VM', 'Powerstate', 'Guest state', 'CPUs', 'Memory',
            'Primary IP Address', 'Annotation', 'Host',
            'OS according to the configuration file'
        ]

        # 필요한 열이 모두 있는지 확인
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"필수 열 '{col}'이 Excel 파일에 없습니다.")

        # 각 VM에 대해 처리
        for _, row in df.iterrows():
            process_vm_data(row)

        return True
    except Exception as e:
        print(f"Excel 파일 처리 중 오류: {str(e)}")
        raise


def process_vm_data(row):
    """VM 데이터 처리"""
    # 필요한 데이터 추출
    hostname = row['VM']
    powerstate = row['Powerstate']
    guest_state = row['Guest state']
    cpus = row['CPUs']
    memory = row['Memory']  # MB 단위
    ip_address = row['Primary IP Address']
    servername = row['Annotation']
    host = row['Host']
    os_version = row['OS according to the configuration file']

    # 빈 값 처리
    if pd.isna(hostname) or pd.isna(ip_address):
        print(f"호스트명 또는 IP 주소가 없는 VM 건너뜀: {hostname if not pd.isna(hostname) else 'Unknown'}")
        return

    # 사용 여부 확인 (Powerstate가 poweredOn이고 Guest state가 running인 경우만 사용)
    is_active = (powerstate == 'poweredOn' and guest_state == 'running')

    # 메모리 GB로 변환 (MB에서)
    memory_gb = int(memory / 1024) if not pd.isna(memory) else None

    # DB에서 해당 VM 검색 (IP 또는 호스트명으로)
    sql = """
    SELECT * FROM total_asset 
    WHERE ip = %s OR hostname = %s
    """
    existing_assets = execute_query(sql, (ip_address, hostname))

    if existing_assets:
        # 기존 자산이 있으면 업데이트
        update_existing_asset(existing_assets[0], hostname, ip_address, servername,
                              is_active, cpus, memory_gb, host, os_version)
    else:
        # 새 자산 추가
        add_new_asset(hostname, ip_address, servername, is_active,
                      cpus, memory_gb, host, os_version)


def update_existing_asset(asset, hostname, ip_address, servername, is_active, cpus, memory_gb, host, os_version):
    """기존 자산 업데이트"""
    # 변경 사항 확인
    changes = {}

    # 호스트명 변경 확인
    if asset['hostname'] != hostname:
        changes['hostname'] = hostname

    # IP 주소 변경 확인
    if asset['ip'] != ip_address:
        changes['ip'] = ip_address

    # 서버명 변경 확인 (Annotation)
    if asset['servername'] != servername and not pd.isna(servername):
        changes['servername'] = servername

    # CPU 코어 변경 확인
    if asset['cpucore'] != cpus and not pd.isna(cpus):
        changes['cpucore'] = cpus

    # 메모리 변경 확인
    if asset['memory'] != memory_gb and not pd.isna(memory_gb):
        changes['memory'] = memory_gb

    # OS 버전 변경 확인
    if asset['osver'] != os_version and not pd.isna(os_version):
        changes['osver'] = os_version

    # 상위 자산 IP 변경 확인 (Host)
    if not pd.isna(host):
        # 상위 자산 IP로 자산 검색
        sql_host = "SELECT pnum FROM total_asset WHERE ip = %s AND isvm = 0"
        host_asset = execute_query(sql_host, (host,), fetch_all=False)

        if host_asset and asset['vcenter'] != host_asset['pnum']:
            changes['vcenter'] = host_asset['pnum']

    # 사용 여부 변경 확인
    isoper_value = 0 if is_active else 2  # 0: 사용, 2: 사용안함
    if asset['isoper'] != isoper_value:
        changes['isoper'] = isoper_value

    # 변경 사항이 있으면 업데이트
    if changes:
        # isfix를 0으로 설정 (확인 완료 상태)
        changes['isfix'] = 0
        changes['dateupdate'] = datetime.now()

        # SQL 쿼리 생성
        set_clause = ", ".join([f"{key} = %s" for key in changes.keys()])
        values = list(changes.values())
        values.append(asset['pnum'])  # WHERE 조건용

        sql = f"UPDATE total_asset SET {set_clause} WHERE pnum = %s"

        # 쿼리 실행
        execute_query(sql, values, fetch_all=False)
        print(
            f"자산 업데이트 (pnum: {asset['pnum']}): {', '.join([f'{k}={v}' for k, v in changes.items() if k != 'dateupdate'])}")


def add_new_asset(hostname, ip_address, servername, is_active, cpus, memory_gb, host, os_version):
    """새 자산 추가"""
    # 상위 자산 검색 (Host IP로)
    vcenter = None
    if not pd.isna(host):
        sql_host = "SELECT pnum FROM total_asset WHERE ip = %s AND isvm = 0"
        host_asset = execute_query(sql_host, (host,), fetch_all=False)
        if host_asset:
            vcenter = host_asset['pnum']

    # 사용 여부 설정
    isoper = 0 if is_active else 2  # 0: 사용, 2: 사용안함

    # OS 코드 가져오기
    os_code = None
    if not pd.isna(os_version):
        # OS 이름 추출 (예: "Microsoft Windows Server 2019" -> "Windows")
        os_name = None
        if "windows" in os_version.lower():
            os_name = "Windows"
        elif "linux" in os_version.lower():
            os_name = "Linux"
        elif "centos" in os_version.lower():
            os_name = "Linux"
        elif "ubuntu" in os_version.lower():
            os_name = "Linux"
        elif "red hat" in os_version.lower() or "redhat" in os_version.lower():
            os_name = "Linux"
        elif "aix" in os_version.lower():
            os_name = "AIX"
        elif "hp-ux" in os_version.lower():
            os_name = "HP-UX"

        if os_name:
            sql_os = "SELECT os FROM info_os WHERE state = %s"
            os_result = execute_query(sql_os, (os_name,), fetch_all=False)
            if os_result:
                os_code = os_result['os']

    # 현재 시간
    now = datetime.now()

    # SQL 쿼리
    sql = """
    INSERT INTO total_asset (
        servername, ip, hostname, isvm, vcenter, datein, isoper, os, osver, 
        cpucore, memory, domain, isfix, dateinsert, dateupdate
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    # 값 설정
    values = (
        servername if not pd.isna(servername) else hostname,  # servername
        ip_address,  # ip
        hostname,  # hostname
        1,  # isvm (VM이므로 1)
        vcenter,  # vcenter
        now.date(),  # datein
        isoper,  # isoper
        os_code if os_code else 0,  # os
        os_version if not pd.isna(os_version) else None,  # osver
        cpus if not pd.isna(cpus) else None,  # cpucore
        memory_gb if not pd.isna(memory_gb) else None,  # memory
        0,  # domain (서버로 설정)
        0,  # isfix (확인 완료 상태로 설정)
        now,  # dateinsert
        now  # dateupdate
    )

    # 쿼리 실행
    execute_query(sql, values, fetch_all=False)
    print(f"새 자산 추가: {hostname} ({ip_address})")


def handle_auto_registered_assets(action, selected_assets):
    """자동 등록된 자산 처리"""
    if not selected_assets:
        return False, "선택된 자산이 없습니다."

    if action == "apply":
        # 반영 처리 (isfix를 0으로 변경)
        for pnum in selected_assets:
            # 현재 자산 정보 가져오기
            sql_get = "SELECT ip, hostname FROM total_asset WHERE pnum = %s"
            asset = execute_query(sql_get, (pnum,), fetch_all=False)

            if not asset:
                continue

            # 동일한 IP와 호스트명을 가진 다른 자산이 있는지 확인
            sql_check = """
            SELECT pnum FROM total_asset 
            WHERE (ip = %s OR hostname = %s) 
            AND pnum != %s AND isfix != 2
            """
            duplicates = execute_query(sql_check, (asset['ip'], asset['hostname'], pnum))

            if duplicates:
                # 중복 자산이 있으면 해�� 자산을 사용안함, 폐기 상태로 변경
                for dup in duplicates:
                    sql_update_dup = """
                    UPDATE total_asset 
                    SET isoper = 2, dateout = %s, dateupdate = %s 
                    WHERE pnum = %s
                    """
                    execute_query(sql_update_dup, (datetime.now().date(), datetime.now(), dup['pnum']), fetch_all=False)

            # 현재 자산의 isfix를 0으로 변경
            sql_update = "UPDATE total_asset SET isfix = 0, dateupdate = %s WHERE pnum = %s"
            execute_query(sql_update, (datetime.now(), pnum), fetch_all=False)

        return True, f"{len(selected_assets)}개 자산이 반영되었습니다."

    elif action == "delete":
        # 삭제 처리
        for pnum in selected_assets:
            sql_delete = "DELETE FROM total_asset WHERE pnum = %s AND isfix = 2"
            execute_query(sql_delete, (pnum,), fetch_all=False)

        return True, f"{len(selected_assets)}개 자산이 삭제되었습니다."

    return False, "잘못된 작업입니다."
