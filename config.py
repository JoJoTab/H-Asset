import os


class Config:
    SECRET_KEY = "secret"  # CSRF 공격 방지 토큰
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    EXPORT_FOLDER = os.path.join(os.getcwd(), 'exports')

    # 데이터베이스 설정
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "a980911"
    DB_NAME = "hli_asset"
    DB_CHARSET = "utf8"

    # 캐시 설정
    CACHE_TIMEOUT = 300  # 5분

    # 페이지네이션 설정
    PER_PAGE = 20
