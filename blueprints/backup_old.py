from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from utils.db import execute_query, get_db_connection
import pandas as pd
import os
from datetime import datetime, timedelta
import csv
from collections import defaultdict
import re

backup_bp = Blueprint('backup', __name__)


@backup_bp.route('/')
def index():
    """백업 관리 메인 페이지"""
    return render_template('backup/index.html')


@backup_bp.route('/schedules')
def get_schedules():
    """백업 스케줄 목록 조회"""
    try:
        query = """
                SELECT bs.*,
                       COUNT(bh.id)                   as execution_count,
                       MAX(bh.job_start_time)         as last_execution,
                       SUM(bh.protected_data_size_mb) as total_data_size_mb
                FROM backup_schedule bs
                         LEFT JOIN backup_history bh ON bs.id = bh.schedule_id
                GROUP BY bs.id
                ORDER BY bs.client_name, bs.policy_name \
                """
        schedules = execute_query(query)

        # 데이터 포맷팅
        for schedule in schedules:
            if schedule['total_data_size_mb']:
                schedule['total_data_size_gb'] = round(schedule['total_data_size_mb'] / 1024, 2)
            else:
                schedule['total_data_size_gb'] = 0

        return jsonify(schedules)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/schedule/<int:schedule_id>')
def get_schedule_detail(schedule_id):
    """특정 스케줄의 상세 정보 조회"""
    try:
        # 스케줄 기본 정보
        schedule_query = "SELECT * FROM backup_schedule WHERE id = %s"
        schedule = execute_query(schedule_query, (schedule_id,), fetch_all=False)

        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404

        # 최근 3개월 실행 이력
        history_query = """
                        SELECT * \
                        FROM backup_history
                        WHERE schedule_id = %s
                          AND job_start_time >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
                        ORDER BY job_start_time DESC \
                        """
        history = execute_query(history_query, (schedule_id,))

        # 총 사용 용량 계산
        total_capacity_query = """
                               SELECT SUM(protected_data_size_mb) as total_mb
                               FROM backup_history
                               WHERE schedule_id = %s
                                 AND job_start_time >= DATE_SUB(NOW(), INTERVAL 3 MONTH) \
                               """
        total_result = execute_query(total_capacity_query, (schedule_id,), fetch_all=False)
        total_capacity_gb = round(total_result['total_mb'] / 1024, 2) if total_result['total_mb'] else 0

        return jsonify({
            'schedule': schedule,
            'history': history,
            'total_capacity_gb': total_capacity_gb
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/history')
def get_backup_history():
    """백업 이력 조회"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 기본값: 최근 1개월
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        query = """
                SELECT bh.*, bs.backup_solution, bs.filesystem_info
                FROM backup_history bh
                         LEFT JOIN backup_schedule bs ON bh.schedule_id = bs.id
                WHERE DATE (bh.job_start_time) BETWEEN %s \
                  AND %s
                ORDER BY bh.job_start_time DESC \
                """

        history = execute_query(query, (start_date, end_date))

        return jsonify({
            'history': history,
            'start_date': start_date,
            'end_date': end_date
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/storage-info')
def get_storage_info():
    """백업 스토리지 정보 조회"""
    try:
        query = "SELECT * FROM backup_storage ORDER BY storage_name"
        storage_info = execute_query(query)

        # 사용률 계산
        for storage in storage_info:
            if storage['total_capacity_gb'] and storage['total_capacity_gb'] > 0:
                usage_percent = (storage['used_capacity_gb'] / storage['total_capacity_gb']) * 100
                storage['usage_percent'] = round(usage_percent, 1)
            else:
                storage['usage_percent'] = 0
        print(storage_info)
        return jsonify(storage_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_bp.route('/upload-csv', methods=['POST'])
def upload_csv():
    """CSV 파일 업로드 및 처리"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv') and not file.filename.endswith('.CSV'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400

        # CSV 파일 읽기
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(csv_content.splitlines())

        processed_count = 0
        error_count = 0

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for row in csv_reader:
                    try:
                        # 데이터 파싱 및 정리
                        print(row)
                        job_start_time = parse_datetime(row.get('\ufeffJob Start Time', ''))
                        job_end_time = parse_datetime(row.get('Job End Time', ''))

                        if not job_start_time:
                            error_count += 1
                            continue

                        # 스케줄 정보 확인/생성
                        schedule_id = get_or_create_schedule(
                            cursor,
                            client_name=row.get('Client Name', ''),
                            policy_name=row.get('Policy Name', ''),
                            schedule_name=row.get('Schedule Name', ''),
                            job_type=row.get('Job Type', '')
                        )

                        # 백업 이력 삽입
                        insert_backup_history(
                            cursor,
                            schedule_id=schedule_id,
                            job_start_time=job_start_time,
                            job_end_time=job_end_time,
                            job_duration=row.get('Job Duration', ''),
                            job_status=row.get('Job Status', ''),
                            status_code=int(row.get('Status Code', 0)),
                            client_name=row.get('Client Name', ''),
                            policy_name=row.get('Policy Name', ''),
                            schedule_name=row.get('Schedule Name', ''),
                            protected_data_size_mb=float(row.get('Protected Data Size(MB)', '0').replace(',', '')),
                            job_type=row.get('Job Type', ''),
                            report_date=job_start_time.date()
                        )

                        processed_count += 1

                    except Exception as e:
                        print(f"Error processing row: {e}")
                        error_count += 1
                        continue

                conn.commit()

        finally:
            conn.close()

        # 스케줄 패턴 업데이트
        update_schedule_patterns()

        return jsonify({
            'message': 'CSV file processed successfully',
            'processed_count': processed_count,
            'error_count': error_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def parse_datetime(datetime_str):
    """날짜시간 문자열 파싱"""
    if not datetime_str:
        return None

    try:
        # 다양한 날짜 형식 지원
        formats = [
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M',
            '%m/%d/%Y %H:%M:%S'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        return None
    except:
        return None


def get_or_create_schedule(cursor, client_name, policy_name, schedule_name, job_type):
    """스케줄 정보 조회 또는 생성"""
    # 기존 스케줄 확인
    cursor.execute("""
                   SELECT id
                   FROM backup_schedule
                   WHERE client_name = %s
                     AND policy_name = %s
                     AND schedule_name = %s
                   """, (client_name, policy_name, schedule_name))

    result = cursor.fetchone()
    if result:
        return result['id']

    # 새 스케줄 생성
    cursor.execute("""
                   INSERT INTO backup_schedule (client_name, policy_name, schedule_name, job_type)
                   VALUES (%s, %s, %s, %s)
                   """, (client_name, policy_name, schedule_name, job_type))

    return cursor.lastrowid


def insert_backup_history(cursor, **kwargs):
    """백업 이력 삽입"""
    # 중복 체크
    cursor.execute("""
                   SELECT id
                   FROM backup_history
                   WHERE client_name = %s
                     AND policy_name = %s
                     AND schedule_name = %s
                     AND job_start_time = %s
                   """,
                   (kwargs['client_name'], kwargs['policy_name'], kwargs['schedule_name'], kwargs['job_start_time']))

    if cursor.fetchone():
        return  # 이미 존재하는 이력

    cursor.execute("""
                   INSERT INTO backup_history (schedule_id, job_start_time, job_end_time, job_duration, job_status,
                                               status_code, client_name, policy_name, schedule_name,
                                               protected_data_size_mb,
                                               job_type, report_date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   """, (
                       kwargs['schedule_id'], kwargs['job_start_time'], kwargs['job_end_time'],
                       kwargs['job_duration'], kwargs['job_status'], kwargs['status_code'],
                       kwargs['client_name'], kwargs['policy_name'], kwargs['schedule_name'],
                       kwargs['protected_data_size_mb'], kwargs['job_type'], kwargs['report_date']
                   ))


def update_schedule_patterns():
    """백업 이력을 바탕으로 스케줄 패턴 업데이트"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 모든 스케줄 조회
            cursor.execute("SELECT id, client_name, policy_name, schedule_name FROM backup_schedule")
            schedules = cursor.fetchall()

            for schedule in schedules:
                # 해당 스케줄의 최근 실행 이력 조회
                cursor.execute("""
                               SELECT DAYOFWEEK(job_start_time) as day_of_week, TIME (job_start_time) as start_time, COUNT (*) as frequency
                               FROM backup_history
                               WHERE schedule_id = %s
                                 AND job_start_time >= DATE_SUB(NOW()
                                   , INTERVAL 3 MONTH)
                               GROUP BY DAYOFWEEK(job_start_time), TIME (job_start_time)
                               ORDER BY frequency DESC
                                   LIMIT 5
                               """, (schedule['id'],))

                patterns = cursor.fetchall()

                if patterns:
                    # 패턴 문자열 생성
                    pattern_parts = []
                    for pattern in patterns:
                        day_names = ['', '일', '월', '화', '수', '목', '금', '토']
                        day_name = day_names[pattern['day_of_week']]
                        time_str = str(pattern['start_time'])
                        pattern_parts.append(f"{day_name}요일 {time_str}")

                    schedule_pattern = ', '.join(pattern_parts[:3])  # 상위 3개만

                    # 스케줄 패턴 업데이트
                    cursor.execute("""
                                   UPDATE backup_schedule
                                   SET schedule_pattern = %s
                                   WHERE id = %s
                                   """, (schedule_pattern, schedule['id']))

            conn.commit()

    except Exception as e:
        print(f"Error updating schedule patterns: {e}")
    finally:
        if conn:
            conn.close()


@backup_bp.route('/update-schedule/<int:schedule_id>', methods=['POST'])
def update_schedule(schedule_id):
    """스케줄 정보 업데이트"""
    try:
        data = request.get_json()

        query = """
                UPDATE backup_schedule
                SET filesystem_info = %s, \
                    memo            = %s, \
                    updated_at      = NOW()
                WHERE id = %s \
                """

        execute_query(query, (
            data.get('filesystem_info', ''),
            data.get('memo', ''),
            schedule_id
        ), fetch_all=False)

        return jsonify({'message': 'Schedule updated successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
