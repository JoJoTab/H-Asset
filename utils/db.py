import pymysql
from config import Config

# 전역 DB 연결 객체
db_connection = None


def init_db_pool():
    """데이터베이스 연결 풀 초기화 (동기식 버전)"""
    global db_connection
    try:
        db_connection = get_db_connection()
        print("데이터베이스 연결 풀 초기화 완료")
        return db_connection
    except Exception as e:
        print(f"데이터베이스 연결 풀 초기화 실패: {e}")
        return None


def close_db_pool():
    """데이터베이스 연결 풀 종료 (동기식 버전)"""
    global db_connection
    if db_connection:
        try:
            db_connection.close()
            print("데이터베이스 연결 풀 종료 완료")
        except Exception as e:
            print(f"데이터베이스 연결 풀 종료 실패: {e}")
        finally:
            db_connection = None


def get_db_connection():
    """데이터베이스 연결 가져오기"""
    global db_connection

    # 기존 연결이 있고 유효하면 재사용
    if db_connection:
        try:
            db_connection.ping(reconnect=True)
            return db_connection
        except:
            # 연결이 끊어졌으면 새로 생성
            pass

    # 새 연결 생성
    return pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        db=Config.DB_NAME,
        charset=Config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor
    )


def execute_query(query, params=None, fetch_all=True):
    """SQL 쿼리 실행 및 결과 반환"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()
            return result
    finally:
        conn.commit()
        conn.close()


def execute_many(query, params_list):
    """여러 SQL 쿼리 실행"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(query, params_list)
            conn.commit()
    finally:
        conn.close()
