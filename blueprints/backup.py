from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from utils.db import execute_query, get_db_connection
from datetime import datetime, timedelta, time
import pandas as pd
import io
from decimal import Decimal
import json

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')


def format_time(time_value):
    """TIME 또는 timedelta를 문자열로 변환"""
    if time_value is None:
        return '-'
    if isinstance(time_value, timedelta):
        total_seconds = int(time_value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f'{hours:02d}:{minutes:02d}'
    if isinstance(time_value, time):
        return time_value.strftime('%H:%M')
    return str(time_value)


def get_status_display(status_code):
    """상태 코드를 표시용 텍스트로 변환"""
    if status_code in [0, 112]:
        return 'Success'
    elif status_code == 1:
        return 'Partial Success'
    else:
        return 'Failed'


def get_status_class(status_code):
    """상태 코드에 따른 CSS 클래스 반환"""
    if status_code in [0, 112]:
        return 'success'
    elif status_code == 1:
        return 'warning'
    else:
        return 'danger'


def format_schedule_times(schedule_times):
    """백업 시간 목록을 문자열로 포맷"""
    if not schedule_times:
        return '-'

    time_strings = []
    for st in schedule_times:
        day = st['day_of_week']
        time_str = format_time(st['backup_time'])

        day_display = {
            'DAILY': '매일',
            'HOURLY': '매시간',
            'MON': '월요일',
            'TUE': '화요일',
            'WED': '수요일',
            'THU': '목요일',
            'FRI': '금요일',
            'SAT': '토요일',
            'SUN': '일요일',
            'SPECIFIC': '지정'
        }.get(day, day)

        time_strings.append(f'{day_display} {time_str}')

    return ' | '.join(time_strings)


def parse_schedule_times_input(time_input):
    """
    사용자 입력을 파싱하여 백업 시간 리스트로 변환
    입력 형식:
    - 지정: "지정 2024-12-25T14:30"
    - 반복: "월요일 23:10, 금요일 23:10" 또는 "매일 07:00"
    """
    if not time_input or not time_input.strip():
        return []

    day_mapping = {
        '매일': 'DAILY',
        '매시간': 'HOURLY',
        '월요일': 'MON',
        '화요일': 'TUE',
        '수요일': 'WED',
        '목요일': 'THU',
        '금요일': 'FRI',
        '토요일': 'SAT',
        '일요일': 'SUN'
    }

    result = []

    if time_input.startswith('지정 '):
        datetime_str = time_input.replace('지정 ', '').strip()
        result.append({'day_of_week': 'SPECIFIC', 'backup_time': datetime_str})
        return result

    entries = [e.strip() for e in time_input.split(',')]

    for entry in entries:
        parts = entry.split()
        if len(parts) >= 2:
            day_str = parts[0]
            time_str = parts[1]

            day_code = day_mapping.get(day_str, 'DAILY')
            result.append({'day_of_week': day_code, 'backup_time': time_str})

    return result


@backup_bp.route('/')
def index():
    """백업 관리 메인 페이지"""
    try:
        # 날짜 계산
        current_date = datetime.now().date()

        # 최근 데이터 날짜 조회
        latest_date = get_latest_storage_history_date()
        if latest_date:
            end_date = latest_date
            start_date = end_date - timedelta(days=3)
        else:
            end_date = current_date
            start_date = current_date - timedelta(days=3)

        # 백업 스토리지 정보 조회
        backup_storages = get_backup_storages()

        # 스토리지 사용량 이력 조회 (기본 3일)
        storage_usage_history = get_storage_usage_history(start_date, end_date)

        # 백업 현황 조회 (24시간 전후)
        current_time = datetime.now()
        past_backups = get_backup_status(current_time - timedelta(hours=24), current_time, 'past')
        future_backups = get_backup_status(current_time, current_time + timedelta(hours=24), 'future')

        # 백업 이력 조회 (기본 7일)
        backup_history = get_backup_history(start_date, end_date)

        return render_template('backup/index.html',
                               backup_storages=backup_storages,
                               storage_usage_history=storage_usage_history,
                               past_backups=past_backups,
                               future_backups=future_backups,
                               backup_history=backup_history,
                               start_date=start_date.strftime('%Y-%m-%d'),
                               end_date=end_date.strftime('%Y-%m-%d'),
                               get_status_display=get_status_display,
                               get_status_class=get_status_class)
    except Exception as e:
        flash(f'데이터를 불러오는 중 오류가 발생했습니다: {str(e)}', 'error')
        current_date = datetime.now().date()
        start_date = current_date - timedelta(days=7)
        return render_template('backup/index.html',
                               backup_storages=[],
                               storage_usage_history=[],
                               past_backups=[],
                               future_backups=[],
                               backup_history=[],
                               start_date=start_date.strftime('%Y-%m-%d'),
                               end_date=current_date.strftime('%Y-%m-%d'),
                               get_status_display=get_status_display,
                               get_status_class=get_status_class)


@backup_bp.route('/schedule')
def schedule():
    """스케줄 관리 페이지"""
    try:
        # 전체 스케줄 조회
        schedules = get_all_schedules()

        # 각 스케줄의 백업 시간 및 연계 자산 정보 조회
        for sch in schedules:
            # 백업 시간 조회
            sch['schedule_times'] = get_schedule_times(sch['id'])
            sch['schedule_times_display'] = format_schedule_times(sch['schedule_times'])

            # 연계된 자산 정보 조회
            sch['linked_asset'] = get_linked_asset_info(sch['id'])

        # 컬럼 정보 조회
        columns = get_schedule_columns()

        return render_template('backup/schedule.html',
                               schedules=schedules,
                               columns=columns)
    except Exception as e:
        flash(f'스케줄 데이터를 불러오는 중 오류가 발생했습니다: {str(e)}', 'error')
        return render_template('backup/schedule.html',
                               schedules=[],
                               columns=[])


def get_latest_storage_history_date():
    """최근 스토리지 이력 날짜 조회"""
    sql = "SELECT MAX(record_date) as latest_date FROM backup_storage_history"

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            return result['latest_date'] if result and result['latest_date'] else None
    finally:
        connection.close()


def get_backup_storages():
    """백업 스토리지 정보 조회"""
    sql = """
    SELECT 
        bs.id,
        bs.storage_name,
        bs.total_capacity_tb,
        bs.location,
        bs.storage_type,
        bs.storage_source,
        COALESCE(bsh.used_capacity_tb, 0) as used_capacity_tb,
        (bs.total_capacity_tb - COALESCE(bsh.used_capacity_tb, 0)) as available_capacity_tb,
        COALESCE(bsh.usage_percentage, 0) as usage_percentage
    FROM backup_storage bs
    LEFT JOIN (
        SELECT storage_id, used_capacity_tb, usage_percentage
        FROM backup_storage_history
        WHERE record_date = (
            SELECT MAX(record_date) 
            FROM backup_storage_history bsh2 
            WHERE bsh2.storage_id = backup_storage_history.storage_id
        )
    ) bsh ON bs.id = bsh.storage_id
    ORDER BY bs.storage_name
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        connection.close()


def get_storage_usage_history(start_date, end_date, storage_ids=None):
    """스토리지 사용량 이력 조회"""
    if storage_ids:
        placeholders = ','.join(['%s'] * len(storage_ids))
        sql = f"""
        SELECT 
            bs.id as storage_id,
            bs.storage_name,
            bs.total_capacity_tb,
            bsh.record_date,
            bsh.used_capacity_tb,
            bsh.usage_percentage
        FROM backup_storage_history bsh
        JOIN backup_storage bs ON bsh.storage_id = bs.id
        WHERE bsh.record_date BETWEEN %s AND %s
        AND bsh.storage_id IN ({placeholders})
        ORDER BY bs.storage_name, bsh.record_date
        """
        params = [start_date, end_date] + storage_ids
    else:
        sql = """
        SELECT 
            bs.id as storage_id,
            bs.storage_name,
            bs.total_capacity_tb,
            bsh.record_date,
            bsh.used_capacity_tb,
            bsh.usage_percentage
        FROM backup_storage_history bsh
        JOIN backup_storage bs ON bsh.storage_id = bs.id
        WHERE bsh.record_date BETWEEN %s AND %s
        ORDER BY bs.storage_name, bsh.record_date
        """
        params = [start_date, end_date]

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        connection.close()


def get_backup_status(start_time, end_time, status_type):
    """백업 현황 조회"""
    if status_type == 'past':
        sql = """
        SELECT 
            bh.id,
            bh.job_start_time,
            bh.job_end_time,
            bh.policy_name,
            bh.schedule_name,
            bh.job_status,
            bh.actual_size_gb,
            bs.hostname
        FROM backup_history bh
        LEFT JOIN backup_schedule bs ON (bh.policy_name = bs.backup_policy AND bh.schedule_name = bs.backup_schedule)
        WHERE bh.job_start_time BETWEEN %s AND %s
        ORDER BY bh.job_start_time DESC
        """
    else:  # future
        # 다음 백업 예정 시간 계산 (간단한 버전)
        sql = """
        SELECT 
            bs.id,
            bs.backup_policy as policy_name,
            bs.backup_schedule as schedule_name,
            -1 as job_status,
            0 as actual_size_gb,
            bs.hostname
        FROM backup_schedule bs
        WHERE bs.is_active = TRUE
        ORDER BY bs.hostname
        LIMIT 10
        """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (start_time, end_time) if status_type == 'past' else ())
            results = cursor.fetchall()

            # future인 경우 시간 정보 추가
            if status_type == 'future':
                current_time = datetime.now()
                for result in results:
                    # 예상 시작/종료 시간 (실제로는 schedule_times 참조 필요)
                    result['job_start_time'] = current_time + timedelta(hours=1)
                    result['job_end_time'] = current_time + timedelta(hours=1, minutes=30)

            return results
    finally:
        connection.close()


def get_backup_history(start_date, end_date):
    """백업 이력 조회"""
    sql = """
    SELECT 
        bh.id,
        bh.job_start_time,
        bh.job_end_time,
        bh.policy_name,
        bh.schedule_name,
        bh.job_status,
        bh.backup_type,
        bh.data_size_gb,
        bh.deduplication_rate,
        bh.actual_size_gb,
        bs.hostname
    FROM backup_history bh
    LEFT JOIN backup_schedule bs ON (bh.policy_name = bs.backup_policy AND bh.schedule_name = bs.backup_schedule)
    WHERE DATE(bh.job_start_time) BETWEEN %s AND %s
    ORDER BY bh.job_start_time DESC
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (start_date, end_date))
            return cursor.fetchall()
    finally:
        connection.close()


def get_all_schedules():
    """전체 스케줄 조회"""
    sql = """
    SELECT 
        id, unique_id, category, business_name, hostname, ip_address,
        introduction_year, vendor, model_name, os, os_version,
        installation_location, redundancy_config, backup_method,
        retention_period, offsite_cycle, offsite_location, offsite_equipment,
        offsite_retention, backup_target, storage_media, backup_policy,
        backup_schedule, dbms, target_filesystem, memo, is_active, 
        created_at, updated_at
    FROM backup_schedule
    ORDER BY hostname, backup_policy
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        connection.close()


def get_schedule_times(schedule_id):
    """특정 스케줄의 백업 시간 조회"""
    sql = """
    SELECT id, day_of_week, backup_time
    FROM backup_schedule_times
    WHERE schedule_id = %s
    ORDER BY id
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (schedule_id,))
            results = cursor.fetchall()
            for result in results:
                result['backup_time'] = format_time(result['backup_time'])
            return results
    finally:
        connection.close()


def get_linked_asset_info(schedule_id):
    """스케줄에 연계된 자산 정보 조회"""
    sql = """
    SELECT 
        bsal.asset_pnum,
        bsal.linked_at,
        ta.servername,
        ta.hostname as asset_hostname,
        ta.ip as asset_ip
    FROM backup_schedule_asset_link bsal
    JOIN total_asset ta ON bsal.asset_pnum = ta.pnum
    WHERE bsal.schedule_id = %s
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (schedule_id,))
            return cursor.fetchone()
    finally:
        connection.close()


def get_schedule_display_data(schedule_id):
    """스케줄의 표시용 데이터 조회 (자산 연계 시 자산 데이터 우선)"""
    # 스케줄 기본 정보
    schedule_sql = "SELECT * FROM backup_schedule WHERE id = %s"

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(schedule_sql, (schedule_id,))
            schedule = cursor.fetchone()

            if not schedule:
                return None

            # 연계된 자산 정보 확인
            linked_asset = get_linked_asset_info(schedule_id)

            if linked_asset:
                # 자산 상세 정보 조회
                asset_sql = """
                SELECT 
                    ta.servername as business_name,
                    ta.hostname,
                    ta.ip as ip_address,
                    ta.datein,
                    ta.maker as vendor,
                    ta.model,
                    io_os.state as os,
                    ta.osver as os_version,
                    ta.center as installation_location
                FROM total_asset ta
                LEFT JOIN info_os io_os ON ta.os = io_os.os
                WHERE ta.pnum = %s
                """
                cursor.execute(asset_sql, (linked_asset['asset_pnum'],))
                asset = cursor.fetchone()

                if asset:
                    # 자산 데이터로 덮어쓰기
                    schedule['business_name'] = asset['business_name']
                    schedule['hostname'] = asset['hostname']
                    schedule['ip_address'] = asset['ip_address']
                    schedule['introduction_year'] = asset['datein'].year if asset['datein'] else None
                    schedule['vendor'] = asset['vendor']
                    schedule['model_name'] = asset['model']
                    schedule['os'] = asset['os']
                    schedule['os_version'] = asset['os_version']
                    schedule['installation_location'] = asset['installation_location']
                    schedule['is_linked'] = True
                    schedule['linked_asset_pnum'] = linked_asset['asset_pnum']
            else:
                schedule['is_linked'] = False

            return schedule
    finally:
        connection.close()


def get_schedule_columns():
    """스케줄 테이블 컬럼 정보"""
    return [
        {'key': 'unique_id', 'name': '고유번호', 'visible': False},
        {'key': 'category', 'name': '구분', 'visible': True},
        {'key': 'business_name', 'name': '업무명', 'visible': True},
        {'key': 'hostname', 'name': '호스트명', 'visible': True},
        {'key': 'ip_address', 'name': 'IP주소', 'visible': True},
        {'key': 'introduction_year', 'name': '도입년도', 'visible': False},
        {'key': 'vendor', 'name': '벤더', 'visible': False},
        {'key': 'model_name', 'name': '모델명', 'visible': False},
        {'key': 'os', 'name': 'OS', 'visible': True},
        {'key': 'os_version', 'name': 'OS version', 'visible': False},
        {'key': 'installation_location', 'name': '설치 장소', 'visible': True},
        {'key': 'redundancy_config', 'name': '이중화 구성', 'visible': False},
        {'key': 'backup_method', 'name': '백업 방식', 'visible': True},
        {'key': 'retention_period', 'name': '보관 주기', 'visible': True},
        {'key': 'schedule_times_display', 'name': '백업 시간', 'visible': True},
        {'key': 'offsite_cycle', 'name': '소산 주기', 'visible': False},
        {'key': 'offsite_location', 'name': '소산 장소', 'visible': False},
        {'key': 'offsite_equipment', 'name': '소산 장비', 'visible': False},
        {'key': 'offsite_retention', 'name': '소산 보관주기', 'visible': False},
        {'key': 'backup_target', 'name': '백업 대상', 'visible': True},
        {'key': 'storage_media', 'name': '저장 매체', 'visible': False},
        {'key': 'backup_policy', 'name': '백업 정책명', 'visible': True},
        {'key': 'backup_schedule', 'name': '백업 스케줄명', 'visible': True},
        {'key': 'dbms', 'name': 'DBMS', 'visible': False},
        {'key': 'target_filesystem', 'name': '타겟 파일시스템', 'visible': False}
    ]


def parse_retention_period(retention_period):
    """보관 주기를 일수로 변환"""
    if not retention_period:
        return 30

    retention_period = retention_period.upper()
    if 'M' in retention_period:
        months = int(retention_period.replace('M', ''))
        return months * 30
    elif 'W' in retention_period:
        weeks = int(retention_period.replace('W', ''))
        return weeks * 7
    elif 'D' in retention_period:
        days = int(retention_period.replace('D', ''))
        return days
    else:
        return 30


# AJAX 엔드포인트들
@backup_bp.route('/api/storage', methods=['POST'])
def api_add_storage():
    """백업 스토리지 추가"""
    try:
        data = request.get_json()

        sql = """
        INSERT INTO backup_storage (storage_name, total_capacity_tb, location, storage_type, storage_source)
        VALUES (%s, %s, %s, %s, %s)
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (
                    data['storage_name'],
                    data['total_capacity_tb'],
                    data.get('location', ''),
                    data.get('storage_type', 'Disk'),
                    data.get('storage_source', '직접입력')
                ))
                connection.commit()
                return jsonify({'success': True, 'message': '스토리지가 추가되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/storage/<int:storage_id>', methods=['DELETE'])
def api_delete_storage(storage_id):
    """백업 스토리지 삭제"""
    try:
        sql = "DELETE FROM backup_storage WHERE id = %s"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (storage_id,))
                connection.commit()
                return jsonify({'success': True, 'message': '스토리지가 삭제되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/storage-history', methods=['POST'])
def api_add_storage_history():
    """백업 스토리지 이력 추가"""
    try:
        data = request.get_json()

        storage_id = data['storage_id']
        used_capacity_tb = float(data['used_capacity_tb'])

        # 총용량 조회
        storage_sql = "SELECT total_capacity_tb FROM backup_storage WHERE id = %s"
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(storage_sql, (storage_id,))
                storage = cursor.fetchone()

                if not storage:
                    return jsonify({'error': '스토리지을 찾을 수 없습니다.'}), 404

                total_capacity_tb = float(storage['total_capacity_tb'])
                usage_percentage = (used_capacity_tb / total_capacity_tb * 100) if total_capacity_tb > 0 else 0

                sql = """
                INSERT INTO backup_storage_history (storage_id, used_capacity_tb, usage_percentage, record_date)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    used_capacity_tb = VALUES(used_capacity_tb),
                    usage_percentage = VALUES(usage_percentage)
                """

                cursor.execute(sql, (
                    storage_id,
                    used_capacity_tb,
                    usage_percentage,
                    data['record_date']
                ))
                connection.commit()
                return jsonify({'success': True, 'message': '스토리지 이력이 추가되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/storage-history/<int:history_id>', methods=['DELETE'])
def api_delete_storage_history(history_id):
    """백업 스토리지 이력 삭제"""
    try:
        sql = "DELETE FROM backup_storage_history WHERE id = %s"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (history_id,))
                connection.commit()
                return jsonify({'success': True, 'message': '스토리지 이력이 삭제되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/storage-history-list')
def api_storage_history_list():
    """스토리지 이력 목록 조회"""
    try:
        sql = """
        SELECT 
            bsh.id,
            bs.storage_name,
            bsh.used_capacity_tb,
            bsh.usage_percentage,
            bsh.record_date
        FROM backup_storage_history bsh
        JOIN backup_storage bs ON bsh.storage_id = bs.id
        ORDER BY bsh.record_date DESC, bs.storage_name
        LIMIT 100
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                history = cursor.fetchall()

                # 날짜 형식 변환
                for item in history:
                    if item['record_date']:
                        item['record_date'] = item['record_date'].strftime('%Y-%m-%d')

                return jsonify(history)
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/storage-usage-history')
def api_storage_usage_history():
    """스토리지 사용량 이력 API"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        storage_ids_str = request.args.get('storage_ids')

        # 최근 날짜 조회
        if not end_date:
            latest_date = get_latest_storage_history_date()
            end_date = latest_date.strftime('%Y-%m-%d') if latest_date else datetime.now().date().strftime('%Y-%m-%d')

        if not start_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            start_date = (end_date_obj - timedelta(days=7)).strftime('%Y-%m-%d')

        # 스토리지 ID 파싱
        storage_ids = None
        if storage_ids_str:
            storage_ids = [int(sid) for sid in storage_ids_str.split(',') if sid]

        history = get_storage_usage_history(start_date, end_date, storage_ids)

        # 날짜 형식 변환
        for item in history:
            if item['record_date']:
                item['record_date'] = item['record_date'].strftime('%Y-%m-%d')

        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/storage-usage-export')
def api_storage_usage_export():
    """스토리지 사용량 Excel 내보내기"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        storage_ids_str = request.args.get('storage_ids')

        # 스토리지 ID 파싱
        storage_ids = None
        if storage_ids_str:
            storage_ids = [int(sid) for sid in storage_ids_str.split(',') if sid]

        history = get_storage_usage_history(start_date, end_date, storage_ids)

        # 데이터 변환 (행: 스토리지명별, 열: 날짜)
        data_dict = {}
        dates = set()

        for item in history:
            storage_name = item['storage_name']
            record_date = item['record_date'].strftime('%Y-%m-%d')
            dates.add(record_date)

            if storage_name not in data_dict:
                data_dict[storage_name] = {
                    'usage': {},
                    'percentage': {}
                }

            data_dict[storage_name]['usage'][record_date] = item['used_capacity_tb']
            data_dict[storage_name]['percentage'][record_date] = item['usage_percentage']

        # 날짜 정렬
        sorted_dates = sorted(list(dates))

        # Excel 데이터 생성
        excel_data = []

        for storage_name, values in data_dict.items():
            # 사용량 행
            usage_row = {'구분': f'{storage_name} - 사용량(TB)'}
            for date in sorted_dates:
                usage_row[date] = values['usage'].get(date, 0)
            excel_data.append(usage_row)

            # 사용률 행
            percentage_row = {'구분': f'{storage_name} - 사용률(%)'}
            for date in sorted_dates:
                percentage_row[date] = values['percentage'].get(date, 0)
            excel_data.append(percentage_row)

        df = pd.DataFrame(excel_data)

        # Excel 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='스토리지 사용량', index=False)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'storage_usage_{start_date}_{end_date}.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/backup-history')
def api_backup_history():
    """백업 이력 API"""
    try:
        start_date = request.args.get('start_date', (datetime.now().date() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().date().strftime('%Y-%m-%d'))

        history = get_backup_history(start_date, end_date)

        # 날짜 형식 변환 및 상태 표시 추가
        for item in history:
            if item['job_start_time']:
                item['job_start_time'] = item['job_start_time'].strftime('%Y-%m-%d %H:%M:%S')
            if item['job_end_time']:
                item['job_end_time'] = item['job_end_time'].strftime('%Y-%m-%d %H:%M:%S')
            item['status_display'] = get_status_display(item['job_status'])
            item['status_class'] = get_status_class(item['job_status'])

        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/schedule-by-policy')
def api_schedule_by_policy():
    """Policy와 Schedule로 스케줄 조회"""
    try:
        policy_name = request.args.get('policy_name')
        schedule_name = request.args.get('schedule_name')

        sql = "SELECT * FROM backup_schedule WHERE backup_policy = %s AND backup_schedule = %s"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (policy_name, schedule_name))
                schedule = cursor.fetchone()

                if not schedule:
                    return jsonify({'error': 'Schedule not found'}), 404

                # 백업 시간 조회
                schedule['schedule_times'] = get_schedule_times(schedule['id'])
                schedule['schedule_times_display'] = format_schedule_times(schedule['schedule_times'])

                # 관련 백업 이력 조회
                history_sql = """
                SELECT * FROM backup_history 
                WHERE policy_name = %s AND schedule_name = %s
                ORDER BY job_start_time DESC 
                LIMIT 100
                """
                cursor.execute(history_sql, (policy_name, schedule_name))
                history = cursor.fetchall()

                # 예상 용량 계산
                retention_days = parse_retention_period(schedule['retention_period'])
                expected_capacity_sql = """
                SELECT SUM(actual_size_gb) as expected_capacity
                FROM backup_history 
                WHERE policy_name = %s AND schedule_name = %s
                AND job_start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                """
                cursor.execute(expected_capacity_sql, (policy_name, schedule_name, retention_days))
                capacity_result = cursor.fetchone()
                expected_capacity = capacity_result['expected_capacity'] if capacity_result and capacity_result[
                    'expected_capacity'] else 0

                # 날짜 형식 변환 및 상태 표시
                for item in history:
                    if item['job_start_time']:
                        item['job_start_time'] = item['job_start_time'].strftime('%Y-%m-%d %H:%M:%S')
                    if item['job_end_time']:
                        item['job_end_time'] = item['job_end_time'].strftime('%Y-%m-%d %H:%M:%S')
                    item['status_display'] = get_status_display(item['job_status'])
                    item['status_class'] = get_status_class(item['job_status'])
                return jsonify({
                    'schedule': schedule,
                    'history': history,
                    'expected_capacity': expected_capacity
                })
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# JSON Encoder 클래스 정의
class DecimalEncoder(json.JSONEncoder):
    """Decimal과 timedelta를 JSON serializable하게 변환"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, timedelta):
            total_seconds = int(obj.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f'{hours:02d}:{minutes:02d}'
        if isinstance(obj, time):
            return obj.strftime('%H:%M')
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, (bytes, bytearray)):
            return obj.decode('utf-8')
        return super(DecimalEncoder, self).default(obj)

def convert_decimals(obj):
    """객체 내의 모든 Decimal을 float로 변환"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, timedelta):
        total_seconds = int(obj.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f'{hours:02d}:{minutes:02d}'
    elif isinstance(obj, time):
        return obj.strftime('%H:%M')
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return obj
def jsonify_with_encoder(data, status_code=200):
    """Decimal encoder를 사용하는 jsonify"""
    response = json.dumps(data, cls=DecimalEncoder, ensure_ascii=False)
    return (response, status_code, {'Content-Type': 'application/json; charset=utf-8'})


def get_schedules_by_asset(asset_pnum):
    """특정 자산에 연계된 스케줄 목록 조회"""
    sql = """
    SELECT 
        bs.id,
        bs.unique_id,
        bs.category,
        bs.backup_policy,
        bs.backup_schedule,
        bs.backup_method,
        bs.retention_period
    FROM backup_schedule bs
    JOIN backup_schedule_asset_link bsal ON bs.id = bsal.schedule_id
    WHERE bsal.asset_pnum = %s
    ORDER BY bs.backup_policy
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (asset_pnum,))
            schedules = cursor.fetchall()

            for sch in schedules:
                sch['schedule_times'] = get_schedule_times(sch['id'])
                sch['schedule_times_display'] = format_schedule_times(sch['schedule_times'])

            return convert_decimals(schedules)
    finally:
        connection.close()

@backup_bp.route('/api/asset/<int:asset_pnum>/schedules')
def api_asset_schedules(asset_pnum):
    """특정 자산에 연계된 스케줄 목록 조회 API"""
    try:
        schedules = get_schedules_by_asset(asset_pnum)
        return jsonify_with_encoder(schedules)
    except Exception as e:
        return jsonify_with_encoder({'error': str(e)}, 500)

@backup_bp.route('/api/schedule/<int:schedule_id>')
def api_schedule_detail(schedule_id):
    """스케줄 상세 정보 API"""
    try:
        schedule = get_schedule_display_data(schedule_id)

        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404

        # 백업 시간 조회
        schedule['schedule_times'] = get_schedule_times(schedule_id)
        schedule['schedule_times_display'] = format_schedule_times(schedule['schedule_times'])

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 관련 백업 이력 조회
                history_sql = """
                SELECT * FROM backup_history 
                WHERE policy_name = %s AND schedule_name = %s
                ORDER BY job_start_time DESC 
                LIMIT 100
                """
                cursor.execute(history_sql, (schedule['backup_policy'], schedule['backup_schedule']))
                history = cursor.fetchall()

                # 예상 용량 계산
                retention_days = parse_retention_period(schedule['retention_period'])
                expected_capacity_sql = """
                SELECT SUM(actual_size_gb) as expected_capacity
                FROM backup_history 
                WHERE policy_name = %s AND schedule_name = %s
                AND job_start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                """
                cursor.execute(expected_capacity_sql,
                               (schedule['backup_policy'], schedule['backup_schedule'], retention_days))
                capacity_result = cursor.fetchone()
                expected_capacity = capacity_result['expected_capacity'] if capacity_result and capacity_result[
                    'expected_capacity'] else 0

                # 날짜 형식 변환 및 상태 표시
                for item in history:
                    if item['job_start_time']:
                        item['job_start_time'] = item['job_start_time'].strftime('%Y-%m-%d %H:%M:%S')
                    if item['job_end_time']:
                        item['job_end_time'] = item['job_end_time'].strftime('%Y-%m-%d %H:%M:%S')
                    item['status_display'] = get_status_display(item['job_status'])
                    item['status_class'] = get_status_class(item['job_status'])

                return jsonify({
                    'schedule': schedule,
                    'history': history,
                    'expected_capacity': expected_capacity
                })
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------- START OF UPDATED CODE --------------------
@backup_bp.route('/api/schedule/<int:schedule_id>/linked-asset')
def api_get_linked_asset(schedule_id):
    """스케줄에 연계된 자산 정보 조회"""
    try:
        linked_asset = get_linked_asset_info(schedule_id)

        if linked_asset:
            # 자산 상세 정보 조회
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = """
                    SELECT pnum, servername, hostname, ip
                    FROM total_asset
                    WHERE pnum = %s
                    """
                    cursor.execute(sql, (linked_asset['asset_pnum'],))
                    asset = cursor.fetchone()

                    return jsonify({'asset': asset})
            finally:
                connection.close()
        else:
            return jsonify({'asset': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/schedule/<int:schedule_id>', methods=['PUT'])
def api_update_schedule(schedule_id):
    """스케줄 수정"""
    try:
        data = request.get_json()

        sql = """
        UPDATE backup_schedule SET
            unique_id = %s, category = %s, business_name = %s, hostname = %s, ip_address = %s,
            introduction_year = %s, vendor = %s, model_name = %s, os = %s, os_version = %s,
            installation_location = %s, redundancy_config = %s, backup_method = %s,
            retention_period = %s, offsite_cycle = %s, offsite_location = %s, offsite_equipment = %s,
            offsite_retention = %s, backup_target = %s, storage_media = %s, backup_policy = %s,
            backup_schedule = %s, dbms = %s, target_filesystem = %s, memo = %s,
            updated_at = NOW()
        WHERE id = %s
        """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (
                    data.get('unique_id'),
                    data.get('category'),
                    data.get('business_name'),
                    data.get('hostname'),
                    data.get('ip_address'),
                    data.get('introduction_year'),
                    data.get('vendor'),
                    data.get('model_name'),
                    data.get('os'),
                    data.get('os_version'),
                    data.get('installation_location'),
                    data.get('redundancy_config'),
                    data.get('backup_method'),
                    data.get('retention_period'),
                    data.get('offsite_cycle'),
                    data.get('offsite_location'),
                    data.get('offsite_equipment'),
                    data.get('offsite_retention'),
                    data.get('backup_target'),
                    data.get('storage_media'),
                    data.get('backup_policy'),
                    data.get('backup_schedule'),
                    data.get('dbms'),
                    data.get('target_filesystem'),
                    data.get('memo'),
                    schedule_id
                ))

                backup_times_input = data.get('backup_times', '')
                backup_times = parse_schedule_times_input(backup_times_input)

                # Delete existing times
                cursor.execute("DELETE FROM backup_schedule_times WHERE schedule_id = %s", (schedule_id,))

                # Insert new times
                if backup_times:
                    time_sql = """
                    INSERT INTO backup_schedule_times (schedule_id, day_of_week, backup_time)
                    VALUES (%s, %s, %s)
                    """
                    for bt in backup_times:
                        cursor.execute(time_sql, (schedule_id, bt['day_of_week'], bt['backup_time']))

                linked_asset_pnum = data.get('linked_asset_pnum')
                if linked_asset_pnum:
                    # Check existing link
                    check_sql = "SELECT id FROM backup_schedule_asset_link WHERE schedule_id = %s"
                    cursor.execute(check_sql, (schedule_id,))
                    existing = cursor.fetchone()

                    if existing:
                        # Update existing link
                        update_sql = """
                        UPDATE backup_schedule_asset_link 
                        SET asset_pnum = %s, linked_at = NOW()
                        WHERE schedule_id = %s
                        """
                        cursor.execute(update_sql, (linked_asset_pnum, schedule_id))
                    else:
                        # Create new link
                        insert_sql = """
                        INSERT INTO backup_schedule_asset_link (schedule_id, asset_pnum)
                        VALUES (%s, %s)
                        """
                        cursor.execute(insert_sql, (schedule_id, linked_asset_pnum))
                else:
                    # Unlink asset
                    cursor.execute("DELETE FROM backup_schedule_asset_link WHERE schedule_id = %s", (schedule_id,))

                connection.commit()
                return jsonify({'success': True, 'message': '스케줄이 수정되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/upload/schedule-asset-link', methods=['POST'])
def upload_schedule_asset_link():
    """스케줄-자산 일괄 연계 Excel 업로드"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Excel 파일만 업로드 가능합니다.'}), 400

        # Excel 파일 읽기
        df = pd.read_excel(file)

        # 필수 컬럼 확인
        required_columns = ['스케줄 고유 ID', '자산 번호']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'error': f'필수 컬럼이 누락되었습니다: {", ".join(missing_columns)}'}), 400

        # 데이터 처리 및 저장
        connection = get_db_connection()
        success_count = 0
        error_count = 0
        already_linked_count = 0

        try:
            with connection.cursor() as cursor:
                for index, row in df.iterrows():
                    try:
                        schedule_unique_id = row['스케줄 고유 ID']
                        asset_pnum = int(row['자산 번호']) if pd.notna(row['자산 번호']) else None

                        if not schedule_unique_id or not asset_pnum:
                            error_count += 1
                            continue

                        # 스케줄 ID 조회
                        cursor.execute("SELECT id FROM backup_schedule WHERE unique_id = %s", (schedule_unique_id,))
                        schedule_result = cursor.fetchone()

                        if not schedule_result:
                            error_count += 1
                            print(f"스케줄을 찾을 수 없음: {schedule_unique_id}")
                            continue

                        schedule_id = schedule_result['id']

                        # 자산 존재 확인
                        cursor.execute("SELECT COUNT(*) as cnt FROM total_asset WHERE pnum = %s", (asset_pnum,))
                        asset_result = cursor.fetchone()

                        if asset_result['cnt'] == 0:
                            error_count += 1
                            print(f"자산을 찾을 수 없음: {asset_pnum}")
                            continue

                        # 기존 연계 확인
                        cursor.execute("""
                            SELECT id FROM backup_schedule_asset_link 
                            WHERE schedule_id = %s
                        """, (schedule_id,))
                        existing = cursor.fetchone()

                        if existing:
                            # 기존 연계 업데이트
                            sql = """
                            UPDATE backup_schedule_asset_link 
                            SET asset_pnum = %s, linked_at = NOW()
                            WHERE schedule_id = %s
                            """
                            cursor.execute(sql, (asset_pnum, schedule_id))
                            already_linked_count += 1
                        else:
                            # 새 연계 생성
                            sql = """
                            INSERT INTO backup_schedule_asset_link (schedule_id, asset_pnum)
                            VALUES (%s, %s)
                            """
                            cursor.execute(sql, (schedule_id, asset_pnum))
                            success_count += 1

                    except Exception as e:
                        error_count += 1
                        print(f"Row {index + 1} error: {str(e)}")
                        continue

                connection.commit()

                message = f'업로드 완료: 신규 연계 {success_count}건, 업데이트 {already_linked_count}건'
                if error_count > 0:
                    message += f', 실패 {error_count}건'

                return jsonify({
                    'success': True,
                    'message': message
                })
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/download/schedule-asset-link-template')
def download_schedule_asset_link_template():
    """스케줄-자산 일괄 연계 템플릿 다운로드"""
    try:
        # 현재 등록된 스케줄 목록 조회
        schedules = get_all_schedules()

        # 템플릿 데이터
        template_data = {
            '스케줄 고유 ID': ['SCHEDULE001', 'SCHEDULE002'],
            '자산 번호': [1001, 1002]
        }

        df_template = pd.DataFrame(template_data)

        # 스케줄 목록 데이터
        schedule_list_data = []
        for schedule in schedules:
            schedule_list_data.append({
                '스케줄 고유 ID': schedule['unique_id'],
                '호스트명': schedule['hostname'],
                '백업 정책명': schedule['backup_policy'],
                '백업 스케줄명': schedule['backup_schedule']
            })

        df_schedules = pd.DataFrame(schedule_list_data)

        # Excel 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_template.to_excel(writer, sheet_name='스케줄-자산 연계', index=False)
            df_schedules.to_excel(writer, sheet_name='스케줄 목록', index=False)

            # 첫 번째 시트에 설명 추가
            workbook = writer.book
            worksheet = writer.sheets['스케줄-자산 연계']
            worksheet.insert_rows(0, 2)
            worksheet['A1'] = '스케줄 고유 ID: 백업 스케줄의 고유 ID (스케줄 목록 시트 참조)'
            worksheet['A2'] = '자산 번호: 연계할 자산의 pnum (자산 관리에서 확인)'

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='schedule_asset_link_template.xlsx'
        )

    except Exception as e:
        flash(f'템플릿 다운로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('backup.schedule'))


@backup_bp.route('/api/schedule', methods=['POST'])
def api_add_schedule():
    """스케줄 추가"""
    try:
        data = request.get_json()

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Generate unique_id: SCHEDULE_{hostname}_{timestamp}
                hostname = data.get('hostname', 'UNKNOWN')
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                unique_id = f"SCHEDULE_{hostname}_{timestamp}"

                # Ensure uniqueness
                check_sql = "SELECT COUNT(*) as cnt FROM backup_schedule WHERE unique_id = %s"
                cursor.execute(check_sql, (unique_id,))
                result = cursor.fetchone()

                # If duplicate, add a counter
                counter = 1
                original_unique_id = unique_id
                while result['cnt'] > 0:
                    unique_id = f"{original_unique_id}_{counter}"
                    cursor.execute(check_sql, (unique_id,))
                    result = cursor.fetchone()
                    counter += 1

                sql = """
                INSERT INTO backup_schedule (
                    unique_id, category, business_name, hostname, ip_address,
                    introduction_year, vendor, model_name, os, os_version,
                    installation_location, redundancy_config, backup_method,
                    retention_period, offsite_cycle, offsite_location, offsite_equipment,
                    offsite_retention, backup_target, storage_media, backup_policy,
                    backup_schedule, dbms, target_filesystem, memo
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(sql, (
                    unique_id,  # Use auto-generated unique_id
                    data.get('category'),
                    data.get('business_name'),
                    data.get('hostname'),
                    data.get('ip_address'),
                    data.get('introduction_year'),
                    data.get('vendor'),
                    data.get('model_name'),
                    data.get('os'),
                    data.get('os_version'),
                    data.get('installation_location'),
                    data.get('redundancy_config'),
                    data.get('backup_method'),
                    data.get('retention_period'),
                    data.get('offsite_cycle'),
                    data.get('offsite_location'),
                    data.get('offsite_equipment'),
                    data.get('offsite_retention'),
                    data.get('backup_target'),
                    data.get('storage_media'),
                    data.get('backup_policy'),
                    data.get('backup_schedule'),
                    data.get('dbms'),
                    data.get('target_filesystem'),
                    data.get('memo')
                ))

                schedule_id = cursor.lastrowid

                backup_times_input = data.get('backup_times', '')
                backup_times = parse_schedule_times_input(backup_times_input)

                if backup_times:
                    time_sql = """
                    INSERT INTO backup_schedule_times (schedule_id, day_of_week, backup_time)
                    VALUES (%s, %s, %s)
                    """
                    for bt in backup_times:
                        cursor.execute(time_sql, (schedule_id, bt['day_of_week'], bt['backup_time']))

                linked_asset_pnum = data.get('linked_asset_pnum')
                if linked_asset_pnum:
                    link_sql = """
                    INSERT INTO backup_schedule_asset_link (schedule_id, asset_pnum)
                    VALUES (%s, %s)
                    """
                    cursor.execute(link_sql, (schedule_id, linked_asset_pnum))

                connection.commit()
                return jsonify(
                    {'success': True, 'message': '스케줄이 추가되었습니다.', 'schedule_id': schedule_id, 'unique_id': unique_id})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/schedule/<int:schedule_id>/link-asset', methods=['POST'])
def api_link_asset(schedule_id):
    """스케줄에 자산 연계"""
    try:
        data = request.get_json()
        asset_pnum = data.get('asset_pnum')

        if not asset_pnum:
            return jsonify({'error': '자산을 선택해주세요.'}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 기존 연계 확인
                check_sql = "SELECT id FROM backup_schedule_asset_link WHERE schedule_id = %s"
                cursor.execute(check_sql, (schedule_id,))
                existing = cursor.fetchone()

                if existing:
                    # 기존 연계 업데이트
                    sql = """
                    UPDATE backup_schedule_asset_link 
                    SET asset_pnum = %s, linked_at = NOW()
                    WHERE schedule_id = %s
                    """
                    cursor.execute(sql, (asset_pnum, schedule_id))
                else:
                    # 새 연계 생성
                    sql = """
                    INSERT INTO backup_schedule_asset_link (schedule_id, asset_pnum)
                    VALUES (%s, %s)
                    """
                    cursor.execute(sql, (schedule_id, asset_pnum))

                connection.commit()
                return jsonify({'success': True, 'message': '자산이 연계되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/schedule/<int:schedule_id>/unlink-asset', methods=['POST'])
def api_unlink_asset(schedule_id):
    """스케줄과 자산 연계 해제"""
    try:
        sql = "DELETE FROM backup_schedule_asset_link WHERE schedule_id = %s"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (schedule_id,))
                connection.commit()
                return jsonify({'success': True, 'message': '자산 연계가 해제되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/search-assets')
def api_search_assets():
    """자산 검색 API"""
    try:
        search_term = request.args.get('term', '')

        if not search_term:
            return jsonify([])

        sql = """
        SELECT 
            ta.pnum,
            ta.servername,
            ta.hostname,
            ta.ip,
            io_os.state as os
        FROM total_asset ta
        LEFT JOIN info_os io_os ON ta.os = io_os.os
        WHERE ta.servername LIKE %s 
           OR ta.hostname LIKE %s 
           OR ta.ip LIKE %s
        LIMIT 20
        """

        search_param = f'%{search_term}%'

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (search_param, search_param, search_param))
                results = cursor.fetchall()
                return jsonify(results)
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/api/schedule/bulk-delete', methods=['POST'])
def api_bulk_delete_schedule():
    """스케줄 일괄 삭제"""
    try:
        data = request.get_json()
        schedule_ids = data.get('schedule_ids', [])

        if not schedule_ids:
            return jsonify({'error': '삭제할 스케줄을 선택해주세요.'}), 400

        placeholders = ','.join(['%s'] * len(schedule_ids))
        sql = f"DELETE FROM backup_schedule WHERE id IN ({placeholders})"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, schedule_ids)
                connection.commit()
                return jsonify({'success': True, 'message': f'{len(schedule_ids)}개의 스케줄이 삭제되었습니다.'})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/upload/backup-history', methods=['POST'])
def upload_backup_history():
    """백업 이력 Excel 업로드"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Excel 파일만 업로드 가능합니다.'}), 400

        # Excel 파일 읽기
        df = pd.read_excel(file, header=4)

        # 필수 컬럼 확인
        required_columns = ['시작시간', '종료시간', '정책명', '스케줄명', '상태', '용량(GB)', 'Type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'error': f'필수 컬럼이 누락되었습니다: {", ".join(missing_columns)}'}), 400

        # 데이터 처리 및 저장
        connection = get_db_connection()
        success_count = 0
        error_count = 0

        try:
            with connection.cursor() as cursor:
                for index, row in df.iterrows():
                    try:
                        # 상태 코드 변환 (int)
                        status_code = int(row['상태']) if pd.notna(row['상태']) else 0

                        # 용량 처리
                        data_size_gb = float(row['용량(GB)']) if pd.notna(row['용량(GB)']) else 0

                        # 중복제거률 처리 (없으면 0%)
                        deduplication_rate = float(row['중복제거률(%)']) if pd.notna(row.get('중복제거률(%)', 0)) else 0

                        # 실용량 계산: 용량 * (100 - 중복제거률) / 100
                        actual_size_gb = data_size_gb * (100 - deduplication_rate) / 100

                        # Type 처리
                        backup_type = row['Type'] if pd.notna(row['Type']) else 'Backup'

                        sql = """
                        INSERT INTO backup_history (
                            job_start_time, job_end_time, policy_name, schedule_name,
                            job_status, backup_type, data_size_gb, deduplication_rate, actual_size_gb
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """

                        cursor.execute(sql, (
                            pd.to_datetime(row['시작시간']) if pd.notna(row['시작시간']) else None,
                            pd.to_datetime(row['종료시간']) if pd.notna(row['종료시간']) else None,
                            row['정책명'] if pd.notna(row['정책명']) else None,
                            row['스케줄명'] if pd.notna(row['스케줄명']) else None,
                            status_code,
                            backup_type,
                            data_size_gb,
                            deduplication_rate,
                            actual_size_gb
                        ))
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Row {index + 1} error: {str(e)}")
                        continue

                connection.commit()

                return jsonify({
                    'success': True,
                    'message': f'업로드 완료: 성공 {success_count}건, 실패 {error_count}건'
                })
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/upload/schedule', methods=['POST'])
def upload_schedule():
    """백업 스케줄 Excel 업로드"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        file = request.files['file']
        upload_type = request.form.get('upload_type', 'insert')

        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Excel 파일만 업로드 가능합니다.'}), 400

        # Excel 파일 읽기
        df = pd.read_excel(file, sheet_name='백업스케줄템플릿', header=3)
        df = df.where(pd.notnull(df), "NULL")

        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)

        # 데이터 처리 및 저장
        connection = get_db_connection()
        success_count = 0
        error_count = 0

        try:
            with connection.cursor() as cursor:
                for index, row in df.iterrows():
                    try:
                        # 백업 시간 파싱
                        backup_times_input = row.get('백업 시간', '')
                        backup_times = parse_schedule_times_input(
                            str(backup_times_input) if pd.notna(backup_times_input) else '')

                        if upload_type == 'update' and pd.notna(row.get('고유번호')):
                            # 업데이트 모드 - unique_id는 변경하지 않음
                            sql = """
                            UPDATE backup_schedule SET
                                category = %s, business_name = %s, hostname = %s, ip_address = %s,
                                introduction_year = %s, vendor = %s, model_name = %s, os = %s,
                                os_version = %s, installation_location = %s, redundancy_config = %s,
                                backup_method = %s, retention_period = %s, offsite_cycle = %s,
                                offsite_location = %s, offsite_equipment = %s, offsite_retention = %s,
                                backup_target = %s, storage_media = %s, backup_policy = %s,
                                backup_schedule = %s, dbms = %s, target_filesystem = %s
                            WHERE unique_id = %s
                            """

                            cursor.execute(sql, (
                                row.get('구분'), row.get('업무명'), row.get('호스트명'), row.get('IP주소'),
                                row.get('도입년도(YYYY)'), row.get('벤더'), row.get('모델명'), row.get('OS'),
                                row.get('OS version'), row.get('설치 장소'), row.get('이중화 구성'),
                                row.get('백업 방식'), row.get('보관 주기'), row.get('소산 주기'),
                                row.get('소산 장소'), row.get('소산 장비'), row.get('소산 보관주기'),
                                row.get('백업 대상'), row.get('저장 매체'), row.get('백업 정책명'),
                                row.get('백업 스케줄명'), row.get('DBMS'), row.get('타겟 파일시스템'),
                                row.get('고유번호')
                            ))

                            # 스케줄 ID 조회
                            cursor.execute("SELECT id FROM backup_schedule WHERE unique_id = %s", (row.get('고유번호'),))
                            schedule_result = cursor.fetchone()
                            if schedule_result:
                                schedule_id = schedule_result['id']

                                # 기존 백업 시간 삭제
                                cursor.execute("DELETE FROM backup_schedule_times WHERE schedule_id = %s",
                                               (schedule_id,))

                                # 새 백업 시간 추가
                                if backup_times:
                                    time_sql = """
                                    INSERT INTO backup_schedule_times (schedule_id, day_of_week, backup_time)
                                    VALUES (%s, %s, %s)
                                    """
                                    for bt in backup_times:
                                        cursor.execute(time_sql, (schedule_id, bt['day_of_week'], bt['backup_time']))
                        else:
                            hostname = row.get('호스트명', 'UNKNOWN')
                            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                            unique_id = f"SCHEDULE_{hostname}_{timestamp}_{index}"

                            # Ensure uniqueness
                            check_sql = "SELECT COUNT(*) as cnt FROM backup_schedule WHERE unique_id = %s"
                            cursor.execute(check_sql, (unique_id,))
                            result = cursor.fetchone()

                            counter = 1
                            original_unique_id = unique_id
                            while result['cnt'] > 0:
                                unique_id = f"{original_unique_id}_{counter}"
                                cursor.execute(check_sql, (unique_id,))
                                result = cursor.fetchone()
                                counter += 1

                            sql = """
                            INSERT INTO backup_schedule (
                                unique_id, category, business_name, hostname, ip_address, introduction_year,
                                vendor, model_name, os, os_version, installation_location, redundancy_config,
                                backup_method, retention_period, offsite_cycle, offsite_location, offsite_equipment,
                                offsite_retention, backup_target, storage_media, backup_policy, backup_schedule,
                                dbms, target_filesystem
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            """

                            cursor.execute(sql, (
                                unique_id,  # Use auto-generated unique_id
                                row.get('구분'), row.get('업무명'), row.get('호스트명'),
                                row.get('IP주소'), row.get('도입년도(YYYY)'), row.get('벤더'), row.get('모델명'),
                                row.get('OS'), row.get('OS version'), row.get('설치 장소'), row.get('이중화 구성'),
                                row.get('백업 방식'), row.get('보관 주기'), row.get('소산 주기'), row.get('소산 장소'),
                                row.get('소산 장비'), row.get('소산 보관주기'), row.get('백업 대상'), row.get('저장 매체'),
                                row.get('백업 정책명'), row.get('백업 스케줄명'), row.get('DBMS'), row.get('타겟 파일시스템')
                            ))

                            schedule_id = cursor.lastrowid

                            # 백업 시간 추가
                            if backup_times:
                                time_sql = """
                                INSERT INTO backup_schedule_times (schedule_id, day_of_week, backup_time)
                                VALUES (%s, %s, %s)
                                """
                                for bt in backup_times:
                                    cursor.execute(time_sql, (schedule_id, bt['day_of_week'], bt['backup_time']))

                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Row {index + 1} error: {str(e)}")
                        continue

                connection.commit()

                return jsonify({
                    'success': True,
                    'message': f'업로드 완료: 성공 {success_count}건, 실패 {error_count}건'
                })
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/download/backup-history-template')
def download_backup_history_template():
    """백업 이력 템플릿 다운로드"""
    try:
        template_data = {
            '시작시간': ['2024-01-01 02:00'],
            '종료시간': ['2024-01-01 02:15'],
            '정책명': ['AML_ARCH'],
            '스케줄명': ['AML_ARCH_D'],
            '상태': [0],
            '용량(GB)': [1500.5],
            'Type': ['Backup'],
            '중복제거률(%)': [65.5]
        }

        df = pd.DataFrame(template_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='백업이력템플릿', index=False)

            # 시트에 설명 추가
            worksheet = writer.sheets['백업이력템플릿']
            worksheet.insert_rows(0, 3)
            worksheet['A1'] = '상태 코드: 0, 112 = 성공, 1 = 부분성공, 그 외 = 실패'
            worksheet['A2'] = 'Type: Backup, Archive, Replication'
            worksheet['A3'] = '중복제거률(%): 입력 없으면 0% (용량 = 실용량)'

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='backup_history_template.xlsx'
        )

    except Exception as e:
        flash(f'템플릿 다운로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('backup.index'))


@backup_bp.route('/download/schedule-template')
def download_schedule_template():
    """스케줄 템플릿 다운로드"""
    try:
        template_data = {
            '구분': ['Sample'],
            '업무명': ['AML 서버 (운영기)'],
            '호스트명': ['AML'],
            'IP주소': ['10.10.8.115'],
            '도입년도(YYYY)': [2010],
            '벤더': ['IBM'],
            '모델명': ['P780 RS6000'],
            'OS': ['AIX61'],
            'OS version': [''],
            '설치 장소': ['IDC'],
            '이중화 구성': ['X'],
            '백업 방식': ['Full Backup'],
            '보관 주기': ['1M'],
            '백업 시간': ['매일 02:00'],
            '소산 주기': ['일 소산'],
            '소산 장소': ['재해복구센터(DR센터)'],
            '소산 장비': ['drnbuappl01'],
            '소산 보관주기': ['3W'],
            '백업 대상': ['DATA 파일'],
            '저장 매체': ['Netbackup Appliance'],
            '백업 정책명': ['AML_ARCH'],
            '백업 스케줄명': ['AML_ARCH_D'],
            'DBMS': ['ORACLE'],
            '타겟 파일시스템': ['/hli_app/appl\n/hli_app/log']
        }

        df = pd.DataFrame(template_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='백업스케줄템플릿', index=False)

            # 시트에 설명 추가
            worksheet = writer.sheets['백업스케줄템플릿']
            worksheet.insert_rows(0, 3)
            worksheet['A1'] = '고유번호는 시스템에서 자동 생성됩니다.'
            worksheet['A2'] = '백업 시간 형식: "매일 07:00", "매시간 00:30", "월요일 23:10, 금요일 23:10"'
            worksheet['A3'] = '요일: 매일, 매시간, 월요일, 화요일, 수요일, 목요일, 금요일, 토요일, 일요일'

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='backup_schedule_template.xlsx'
        )

    except Exception as e:
        flash(f'템플릿 다운로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('backup.schedule'))


@backup_bp.route('/download/schedule-bulk-change-template')
def download_schedule_bulk_change_template():
    """스케줄 일괄변경 템플릿 다운로드"""
    try:
        # 현재 등록된 모든 스케줄 조회
        schedules = get_all_schedules()

        # DataFrame으로 변환
        data = []
        for schedule in schedules:
            # 백업 시간 조회
            schedule_times = get_schedule_times(schedule['id'])
            schedule_times_display = format_schedule_times(schedule_times)

            data.append({
                '고유번호': schedule['unique_id'],
                '구분': schedule['category'],
                '업무명': schedule['business_name'],
                '호스트명': schedule['hostname'],
                'IP주소': schedule['ip_address'],
                '도입년도(YYYY)': schedule['introduction_year'],
                '벤더': schedule['vendor'],
                '모델명': schedule['model_name'],
                'OS': schedule['os'],
                'OS version': schedule['os_version'],
                '설치 장소': schedule['installation_location'],
                '이중화 구성': schedule['redundancy_config'],
                '백업 방식': schedule['backup_method'],
                '보관 주기': schedule['retention_period'],
                '백업 시간': schedule_times_display,
                '소산 주기': schedule['offsite_cycle'],
                '소산 장소': schedule['offsite_location'],
                '소산 장비': schedule['offsite_equipment'],
                '소산 보관주기': schedule['offsite_retention'],
                '백업 대상': schedule['backup_target'],
                '저장 매체': schedule['storage_media'],
                '백업 정책명': schedule['backup_policy'],
                '백업 스케줄명': schedule['backup_schedule'],
                'DBMS': schedule['dbms'],
                '타겟 파일시스템': schedule['target_filesystem']
            })

        df = pd.DataFrame(data)

        # Excel 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='백업스케줄일괄변경', index=False)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='backup_schedule_bulk_change_template.xlsx'
        )

    except Exception as e:
        flash(f'템플릿 다운로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('backup.schedule'))


@backup_bp.route('/download/schedule-export')
def download_schedule_export():
    """스케줄 내려받기 (고유번호 제외)"""
    try:
        # 현재 등록된 모든 스케줄 조회
        schedules = get_all_schedules()

        # DataFrame으로 변환 (고유번호 제외)
        data = []
        for schedule in schedules:
            # 백업 시간 조회
            schedule_times = get_schedule_times(schedule['id'])
            schedule_times_display = format_schedule_times(schedule_times)

            # 연계된 자산 정보
            linked_asset = get_linked_asset_info(schedule['id'])
            linked_status = '연계됨' if linked_asset else '미연계'

            data.append({
                '구분': schedule['category'],
                '업무명': schedule['business_name'],
                '호스트명': schedule['hostname'],
                'IP주소': schedule['ip_address'],
                '도입년도(YYYY)': schedule['introduction_year'],
                '벤더': schedule['vendor'],
                '모델명': schedule['model_name'],
                'OS': schedule['os'],
                'OS version': schedule['os_version'],
                '설치 장소': schedule['installation_location'],
                '이중화 구성': schedule['redundancy_config'],
                '백업 방식': schedule['backup_method'],
                '보관 주기': schedule['retention_period'],
                '백업 시간': schedule_times_display,
                '소산 주기': schedule['offsite_cycle'],
                '소산 장소': schedule['offsite_location'],
                '소산 장비': schedule['offsite_equipment'],
                '소산 보관주기': schedule['offsite_retention'],
                '백업 대상': schedule['backup_target'],
                '저장 매체': schedule['storage_media'],
                '백업 정책명': schedule['backup_policy'],
                '백업 스케줄명': schedule['backup_schedule'],
                'DBMS': schedule['dbms'],
                '타겟 파일시스템': schedule['target_filesystem'],
                '자산연계': linked_status
            })

        df = pd.DataFrame(data)

        # Excel 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='백업스케줄목록', index=False)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='backup_schedule_export.xlsx'
        )

    except Exception as e:
        flash(f'내려받기 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('backup.schedule'))
