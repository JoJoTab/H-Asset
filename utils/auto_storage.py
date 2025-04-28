import os
import time
import pandas as pd
import schedule
import threading
import re
from datetime import datetime
from utils.db import execute_query, get_db_connection

# 자동 등록 설정
AUTO_STORAGE_FOLDER = 'autodata/storage'
CHECK_INTERVAL = 10  # 10분마다 확인


def setup_auto_storage():
    """스토리지 자동 등록 기능 설정"""
    # 폴더가 없으면 생성
    if not os.path.exists(AUTO_STORAGE_FOLDER):
        os.makedirs(AUTO_STORAGE_FOLDER, exist_ok=True)

    # 스케줄러 설정
    schedule.every(CHECK_INTERVAL).minutes.do(check_storage_files)

    # 백그라운드 스레드에서 스케줄러 실행
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()

    print(f"스토리지 자동 등록 기능이 설정되었습니다. {AUTO_STORAGE_FOLDER} 폴더를 {CHECK_INTERVAL}분마다 확인합니다.")


def run_scheduler():
    """스케줄러 실행"""
    while True:
        schedule.run_pending()
        time.sleep(1)


def check_storage_files():
    """스토리지 용량 파일 확인 및 처리"""
    print(f"[{datetime.now()}] 스토리지 용량 파일 확인 중...")

    # 폴더 내 모든 파일 확인
    for filename in os.listdir(AUTO_STORAGE_FOLDER):
        if filename.startswith('capa_') and filename.endswith('.csv'):
            file_path = os.path.join(AUTO_STORAGE_FOLDER, filename)
            print(f"스토리지 용량 파일 발견: {filename}")

            try:
                # 파일 처리
                process_storage_file(file_path)

                # 처리 후 파일 삭제
                os.remove(file_path)
                print(f"파일 처리 완료 및 삭제: {filename}")
            except Exception as e:
                print(f"파일 처리 중 오류 발생: {str(e)}")


def process_storage_file(file_path):
    """스토리지 용량 파일 처리"""
    try:
        # CSV 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        if not lines:
            raise ValueError("파일이 비어 있습니다.")

        # 첫 번째 줄에서 날짜 추출
        date_str = lines[0].strip()
        try:
            # 날짜 형식 확인 (YYYY-MM-DD)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"잘못된 날짜 형식: {date_str}")

        # 스토리지 데이터 파싱
        current_storage = None
        storage_data = []

        for line in lines[1:]:
            line = line.strip()

            # 빈 줄 무시
            if not line:
                continue

            # 구분선 무시
            if line.startswith('='):
                continue

            # 스토리지 이름 확인
            if not line.startswith('PID'):
                # 스토리지 이름 라인
                current_storage = line.strip()
                continue

            # PID 헤더 라인 무시
            if line.startswith('PID  POLS'):
                continue

            # 데이터 라인 처리
            parts = re.split(r'\s+', line)
            if len(parts) >= 11:  # 최소 필요한 컬럼 수 확인
                pid = int(parts[0])
                av_cap = int(parts[3])
                tp_cap = int(parts[4])
                tl_cap = int(parts[9])

                storage_data.append({
                    'date': date_obj,
                    'storage': current_storage,
                    'pid': pid,
                    'av_cap': av_cap,
                    'tp_cap': tp_cap,
                    'tl_cap': tl_cap
                })

        # 데이터베이스에 저장
        save_storage_data(storage_data)

        return True
    except Exception as e:
        print(f"스토리지 파일 처리 중 오류: {str(e)}")
        raise


def save_storage_data(storage_data):
    """스토리지 데이터를 데이터베이스에 저장"""
    if not storage_data:
        print("저장할 스토리지 데이터가 없습니다.")
        return

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 기존 데이터 확인 및 삭제 (같은 날짜, 같은 스토리지, 같은 PID)
            for data in storage_data:
                check_sql = """
                SELECT idx FROM total_storage 
                WHERE DATEIN = %s AND STORAGE = %s AND PID = %s
                """
                cursor.execute(check_sql, (data['date'], data['storage'], data['pid']))
                existing = cursor.fetchone()

                if existing:
                    # 기존 데이터 삭제
                    delete_sql = "DELETE FROM total_storage WHERE idx = %s"
                    cursor.execute(delete_sql, (existing['idx'],))

            # 새 데이터 삽입
            insert_sql = """
            INSERT INTO total_storage (DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP)
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            for data in storage_data:
                cursor.execute(
                    insert_sql,
                    (
                        data['date'],
                        data['storage'],
                        data['pid'],
                        data['av_cap'],
                        data['tp_cap'],
                        data['tl_cap']
                    )
                )

            connection.commit()
            print(f"{len(storage_data)}개의 스토리지 데이터가 저장되었습니다.")
    except Exception as e:
        connection.rollback()
        print(f"스토리지 데이터 저장 중 오류: {str(e)}")
        raise
    finally:
        connection.close()
