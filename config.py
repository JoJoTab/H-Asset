import os


class Config:
    SECRET_KEY = "secret"  # CSRF 공격 방지 토큰
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    EXPORT_FOLDER = os.path.join(os.getcwd(), 'exports')

    # hli_asset 데이터베이스 설정
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "a980911"
    DB_NAME = "hli_asset"
    DB_CHARSET = "utf8"

    # queryone 데이터베이스 설정
    QO_DB_HOST = "10.10.8.35"
    QO_DB_PORT = 1530
    QO_DB_USER = "qoadmin"
    QO_DB_PASSWORD = "qoad_0904"
    QO_DB_NAME = "qone"

    # dirst 데이터베이스 설정
    DIRST_DB_HOST = "10.10.20.133"
    DIRST_DB_PORT = 1525
    DIRST_DB_USER = "IRDMOW"
    DIRST_DB_PASSWORD = "D$eksoRj18"
    DIRST_DB_NAME = "DIRST1"

    # 캐시 설정
    CACHE_TIMEOUT = 300  # 5분

    # 페이지네이션 설정
    PER_PAGE = 20

    # 폴스타(Polaris) 모니터링 서버 REST API 설정
    POLARIS_BASE_URL = "https://hsms.hanwhalife.com/rest"
    POLARIS_FW_MONITOR_TYPE = (
        "com.nkia.cygnus.plugins.server.domain."
        "ScriptCustomMonitor-924fe3c4-9129-4916-8230-c9026ed09def"
    )

