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


# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────

def get_all_storage():
    return execute_query(
        "SELECT DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP FROM total_storage"
    )


def get_storage_latest_dates():
    """최신 날짜와 하루 전 날짜 반환 (end_date, start_date)"""
    end = execute_query(
        "SELECT MAX(DATEIN) AS end_date FROM total_storage", fetch_all=False
    )
    start = execute_query(
        "SELECT DATE_SUB(MAX(DATEIN), INTERVAL 1 DAY) AS start_date FROM total_storage",
        fetch_all=False,
    )
    return end["end_date"], start["start_date"]


def get_storage_by_date_range(start_date, end_date):
    sql = (
        "SELECT STORAGE, PID, DATEIN, AV_CAP, TP_CAP, TL_CAP "
        "FROM total_storage WHERE DATEIN BETWEEN %s AND %s"
    )
    return execute_query(sql, (start_date, end_date))


def check_storage_dates(start_date, end_date):
    return execute_query(
        "SELECT DATEIN FROM total_storage WHERE DATEIN IN (%s, %s)",
        (start_date, end_date),
    )


def insert_storage_row(date, storage_type, pid, av_cap, tp_cap, tl_cap):
    sql = (
        "INSERT INTO total_storage (DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    execute_query(sql, (date, storage_type, pid, av_cap, tp_cap, tl_cap), fetch_all=False)


# ─────────────────────────────────────────────
# Asset (raw)
# ─────────────────────────────────────────────

def get_all_assets():
    return execute_query("SELECT * FROM total_asset")


def insert_assets_bulk(valid_data):
    sql = """INSERT INTO total_asset
             (itamnum, servername, ip, hostname, center, loc1, loc2, isvm, vcenter,
              datein, dateout, charge, charge2, isoper, oper, power, pdu, os, osver,
              maker, model, serial, domain, charge3)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    execute_many(sql, valid_data)


def insert_rv_assets_bulk(valid_data):
    sql = """INSERT INTO total_asset
             (servername, ip, hostname, center, isvm, vcenter,
              isoper, oper, os, domain, cpucore, memory)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    execute_many(sql, valid_data)


# ─────────────────────────────────────────────
# OS 트렌드
# ─────────────────────────────────────────────

def get_asset_os_list():
    sql = (
        "SELECT io_os.state AS os "
        "FROM hli_asset.total_asset ta "
        "JOIN hli_asset.info_os io_os ON ta.os = io_os.os"
    )
    return execute_query(sql)


def get_asset_os_with_date():
    sql = (
        "SELECT ta.datein, io_os.state AS os "
        "FROM hli_asset.total_asset ta "
        "JOIN hli_asset.info_os io_os ON ta.os = io_os.os"
    )
    return execute_query(sql)


# ─────────────────────────────────────────────
# 랙
# ─────────────────────────────────────────────

def get_distinct_loc1():
    return execute_query("SELECT DISTINCT loc1 FROM total_asset")


def get_rack_info_by_locs(loc_list):
    sql = "SELECT loc, rackname, rackenable FROM rack_info WHERE loc IN %s"
    return execute_query(sql, (tuple(loc_list),))


def upsert_rack_info(loc, rackname, rackenable):
    result = execute_query(
        "SELECT COUNT(*) AS count FROM rack_info WHERE loc = %s", (loc,), fetch_all=False
    )
    exists = result["count"] if result else 0
    if exists > 0:
        execute_query(
            "UPDATE rack_info SET rackname = %s, rackenable = %s WHERE loc = %s",
            (rackname, rackenable, loc),
            fetch_all=False,
        )
    else:
        execute_query(
            "INSERT INTO rack_info (loc, rackname, rackenable) VALUES (%s, %s, %s)",
            (loc, rackname, rackenable),
            fetch_all=False,
        )


def get_physical_asset_locs():
    return execute_query("SELECT loc1 FROM total_asset WHERE isvm = 0")


def get_all_rack_info():
    return execute_query("SELECT loc, rackname, rackenable FROM rack_info")


def get_rack_assets():
    return execute_query(
        "SELECT loc1, loc2, servername, charge, maker, model, usize FROM total_asset"
    )


# ─────────────────────────────────────────────
# 위치 헬퍼
# ─────────────────────────────────────────────

def get_locations_by_floor_column(floor, column):
    return execute_query(
        "SELECT loc1 FROM total_asset WHERE loc1 LIKE %s", (f"{floor}-{column}-%",)
    )


def get_columns_by_floor(floor):
    return execute_query(
        "SELECT DISTINCT loc1 FROM total_asset WHERE loc1 LIKE %s", (f"{floor}-%",)
    )


# ─────────────────────────────────────────────
# 자산 + JOIN 정보 (index / index_detail)
# ─────────────────────────────────────────────

_SQL_ASSETS_WITH_INFO = """
    SELECT ta.*,
           id.state          AS domain_state,
           io_isoper.state   AS isoper_state,
           io_oper.state     AS oper_state,
           io_power.state    AS power_state,
           io_os.state       AS os_state
    FROM total_asset ta
    JOIN info_domain id ON ta.domain = id.domain
    LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
    LEFT JOIN info_oper   io_oper   ON ta.oper   = io_oper.oper
    LEFT JOIN info_power  io_power  ON ta.power  = io_power.power
    LEFT JOIN info_os     io_os     ON ta.os     = io_os.os
"""

_STR_FILTER_FIELDS = {
    "itamnum", "servername", "ip", "hostname", "center", "loc1",
    "datein", "dateout", "charge", "charge2", "pdu", "os", "osver",
    "maker", "model", "serial", "domain", "charge3",
}
_INT_FILTER_FIELDS = {"loc2", "isvm", "vcenter", "isoper", "oper", "power"}


def get_assets_with_info(filters=None):
    """filters: dict {field: value}. 문자열 필드는 LIKE, 정수 필드는 =."""
    sql = _SQL_ASSETS_WITH_INFO + " WHERE 1=1 ORDER BY ta.dateinsert"
    params = []
    if filters:
        for field, value in filters.items():
            if value is None:
                continue
            if field in _STR_FILTER_FIELDS:
                sql += f" AND {field} LIKE %s"
                params.append(f"%{value}%")
            elif field in _INT_FILTER_FIELDS:
                sql += f" AND {field} = %s"
                params.append(value)
    return execute_query(sql, params)


def get_assets_for_graph():
    sql = """
        SELECT ta.*,
               id.state          AS domain_state,
               io_isoper.state   AS isoper_state,
               io_oper.state     AS oper_state,
               io_power.state    AS power_state,
               io_os.state       AS os_state
        FROM hli_asset.total_asset ta
        JOIN hli_asset.info_domain id ON ta.domain = id.domain
        LEFT JOIN hli_asset.info_isoper io_isoper ON ta.isoper = io_isoper.isoper
        LEFT JOIN hli_asset.info_oper   io_oper   ON ta.oper   = io_oper.oper
        LEFT JOIN hli_asset.info_power  io_power  ON ta.power  = io_power.power
        LEFT JOIN hli_asset.info_os     io_os     ON ta.os     = io_os.os
        ORDER BY ta.dateinsert
    """
    return execute_query(sql)


# ─────────────────────────────────────────────
# info 옵션 테이블
# ─────────────────────────────────────────────

def get_info_options():
    """(isoper_options, oper_options, power_options, os_options, domain_options) 반환"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM info_isoper")
            isoper = cursor.fetchall()
            cursor.execute("SELECT * FROM info_oper")
            oper = cursor.fetchall()
            cursor.execute("SELECT * FROM info_power")
            power = cursor.fetchall()
            cursor.execute("SELECT * FROM info_os")
            os = cursor.fetchall()
            cursor.execute("SELECT * FROM info_domain")
            domain = cursor.fetchall()
    finally:
        conn.close()
    return isoper, oper, power, os, domain


def get_asset_with_options(pnum):
    """편집 화면용: (asset_data, isoper, oper, os_options, domain_options, power_options) 반환"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ta.*,
                       io_isoper.state AS isoper,
                       io_oper.state   AS oper,
                       io_os.state     AS os,
                       io_domain.state AS domain,
                       io_power.state  AS power
                FROM total_asset ta
                LEFT JOIN info_isoper io_isoper ON ta.isoper = io_isoper.isoper
                LEFT JOIN info_oper   io_oper   ON ta.oper   = io_oper.oper
                LEFT JOIN info_os     io_os     ON ta.os     = io_os.os
                LEFT JOIN info_domain io_domain ON ta.domain = io_domain.domain
                LEFT JOIN info_power  io_power  ON ta.power  = io_power.power
                WHERE ta.pnum = %s
            """, (pnum,))
            asset = cursor.fetchone()
            cursor.execute("SELECT * FROM info_isoper")
            isoper = cursor.fetchall()
            cursor.execute("SELECT * FROM info_oper")
            oper = cursor.fetchall()
            cursor.execute("SELECT * FROM info_os")
            os_opts = cursor.fetchall()
            cursor.execute("SELECT * FROM info_domain")
            domain = cursor.fetchall()
            cursor.execute("SELECT * FROM info_power")
            power = cursor.fetchall()
    finally:
        conn.close()
    return asset, isoper, oper, os_opts, domain, power


def lookup_info_code(table, col, state):
    """state 문자열을 정수 코드로 변환. 없으면 None 반환."""
    result = execute_query(
        f"SELECT {col} FROM {table} WHERE state = %s", (state,), fetch_all=False
    )
    return result[col] if result else None


# ─────────────────────────────────────────────
# 자산 CRUD
# ─────────────────────────────────────────────

def insert_asset(data_tuple):
    sql = """INSERT INTO total_asset
             (itamnum, servername, ip, hostname, center, loc1, loc2, isvm, vcenter,
              datein, dateout, charge, charge2, isoper, oper, power, pdu, os, osver,
              maker, model, serial, domain, charge3)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    execute_query(sql, data_tuple, fetch_all=False)


def update_asset(pnum, data_tuple):
    sql = """UPDATE total_asset
             SET itamnum=%s, servername=%s, ip=%s, hostname=%s, center=%s,
                 loc1=%s, loc2=%s, isvm=%s, datein=%s, dateout=%s,
                 charge=%s, charge2=%s, isoper=%s, oper=%s, power=%s,
                 pdu=%s, os=%s, osver=%s, maker=%s, model=%s,
                 serial=%s, domain=%s, charge3=%s
             WHERE pnum=%s"""
    execute_query(sql, (*data_tuple, pnum), fetch_all=False)


def delete_asset(pnum):
    execute_query("DELETE FROM total_asset WHERE pnum = %s", (pnum,), fetch_all=False)


# =============================================================
# asset_info (새 자산정보 테이블)
# =============================================================

# 새 테이블의 모든 컬럼 (pnum, dateinsert 제외)
_ASSET_INFO_COLS = (
    "hostname", "servername", "grp", "oper", "center", "network_zone",
    "asset_type", "purpose", "loc1", "loc2", "usize",
    "maker", "model", "serial", "os", "osver",
    "cpucore", "cpusocket", "memory",
    "datein", "dateout", "hw_eos", "hw_eosl",
    "status", "importance", "power", "watt", "ampere",
    "charge", "charge2", "charge3", "memo",
)

_SQL_SELECT_ASSET_INFO = """
    SELECT ai.*,
           GROUP_CONCAT(DISTINCT aip.ip ORDER BY aip.id SEPARATOR ',') AS ip
    FROM asset_info ai
    LEFT JOIN asset_ip aip ON ai.pnum = aip.asset_pnum
"""

_NEW_STR_FILTER  = {
    "hostname", "servername", "grp", "oper", "center", "network_zone",
    "asset_type", "purpose", "loc1", "os", "osver", "maker", "model",
    "serial", "status", "importance", "power",
    "charge", "charge2", "charge3", "memo",
}
_NEW_INT_FILTER  = {"loc2", "usize", "cpucore", "cpusocket"}


def get_asset_info_list(filters=None):
    """asset_info 목록 조회 (IP 콤마 합산 포함). filters: dict {field: value}"""
    sql    = _SQL_SELECT_ASSET_INFO + " WHERE 1=1"
    params = []
    if filters:
        for field, value in filters.items():
            if value is None:
                continue
            if field in _NEW_STR_FILTER:
                sql += f" AND ai.{field} LIKE %s"
                params.append(f"%{value}%")
            elif field in _NEW_INT_FILTER:
                sql += f" AND ai.{field} = %s"
                params.append(value)
    sql += " GROUP BY ai.pnum ORDER BY ai.dateinsert DESC"
    return execute_query(sql, params)


def get_asset_info_by_pnum(pnum):
    """단일 자산 상세 조회 (IP 포함)"""
    sql = _SQL_SELECT_ASSET_INFO + " WHERE ai.pnum = %s GROUP BY ai.pnum"
    return execute_query(sql, (pnum,), fetch_all=False)


def insert_asset_info(data: dict):
    """asset_info 단건 삽입. data: 컬럼명→값 dict. pnum(AUTO) 반환."""
    cols   = [c for c in _ASSET_INFO_COLS if c in data]
    vals   = [data[c] for c in cols]
    ph     = ", ".join(["%s"] * len(cols))
    sql    = f"INSERT INTO asset_info ({', '.join(cols)}) VALUES ({ph})"
    conn   = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, vals)
            new_pnum = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return new_pnum


def update_asset_info(pnum, data: dict):
    """asset_info 단건 수정. data: 컬럼명→값 dict."""
    cols = [c for c in _ASSET_INFO_COLS if c in data]
    if not cols:
        return
    set_clause = ", ".join(f"{c} = %s" for c in cols)
    vals = [data[c] for c in cols] + [pnum]
    execute_query(
        f"UPDATE asset_info SET {set_clause} WHERE pnum = %s",
        vals, fetch_all=False
    )


def delete_asset_info(pnum):
    """asset_info 단건 삭제 (FK CASCADE 로 관련 테이블 자동 삭제)"""
    execute_query("DELETE FROM asset_info WHERE pnum = %s", (pnum,), fetch_all=False)


def bulk_insert_asset_info(rows: list):
    """asset_info 다건 삽입. rows: list of dict"""
    if not rows:
        return
    cols = [c for c in _ASSET_INFO_COLS if c in rows[0]]
    ph   = ", ".join(["%s"] * len(cols))
    sql  = f"INSERT INTO asset_info ({', '.join(cols)}) VALUES ({ph})"
    data = [[row.get(c) for c in cols] for row in rows]
    execute_many(sql, data)


# =============================================================
# asset_ip (자산 IP)
# =============================================================

def get_ips_by_asset(pnum):
    return execute_query(
        "SELECT * FROM asset_ip WHERE asset_pnum = %s ORDER BY id", (pnum,)
    )


def replace_asset_ips(pnum, ip_list: list):
    """기존 IP 전부 삭제 후 새 목록으로 교체. ip_list: [{'ip':..,'ip_type':..}]"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM asset_ip WHERE asset_pnum = %s", (pnum,))
            if ip_list:
                cursor.executemany(
                    "INSERT INTO asset_ip (asset_pnum, ip, ip_type) VALUES (%s, %s, %s)",
                    [(pnum, r["ip"], r.get("ip_type", "내부")) for r in ip_list]
                )
        conn.commit()
    finally:
        conn.close()


def parse_ip_input(raw: str) -> list:
    """콤마 구분 IP 문자열 → [{'ip':..,'ip_type':'내부'}] 변환"""
    if not raw:
        return []
    return [{"ip": ip.strip(), "ip_type": "내부"}
            for ip in raw.split(",") if ip.strip()]


# =============================================================
# asset_link (자산연계)
# =============================================================

def get_links_by_asset(pnum):
    return execute_query(
        "SELECT * FROM asset_link WHERE asset_pnum = %s ORDER BY system_type", (pnum,)
    )


def replace_asset_links(pnum, links: list):
    """기존 연계정보 전부 삭제 후 새 목록으로 교체.
    links: [{'system_type':..,'system_id':..}]"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM asset_link WHERE asset_pnum = %s", (pnum,))
            if links:
                cursor.executemany(
                    "INSERT INTO asset_link (asset_pnum, system_type, system_id) VALUES (%s, %s, %s)",
                    [(pnum, lk["system_type"], lk["system_id"]) for lk in links]
                )
        conn.commit()
    finally:
        conn.close()


# =============================================================
# asset_relation (자산관계)
# =============================================================

def get_relations_by_asset(pnum):
    """특정 자산의 상위/하위 관계 목록 조회"""
    sql = """
        SELECT ar.*,
               p.hostname AS parent_hostname, p.servername AS parent_servername,
               c.hostname AS child_hostname,  c.servername AS child_servername
        FROM asset_relation ar
        JOIN asset_info p ON ar.parent_pnum = p.pnum
        JOIN asset_info c ON ar.child_pnum  = c.pnum
        WHERE ar.parent_pnum = %s OR ar.child_pnum = %s
    """
    return execute_query(sql, (pnum, pnum))


def replace_asset_relations(pnum, relations: list):
    """해당 자산이 child 인 관계 전부 삭제 후 새 목록 교체.
    relations: [{'parent_pnum':..,'relation_type':..}]"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM asset_relation WHERE child_pnum = %s", (pnum,)
            )
            if relations:
                cursor.executemany(
                    "INSERT INTO asset_relation (parent_pnum, child_pnum, relation_type) VALUES (%s,%s,%s)",
                    [(r["parent_pnum"], pnum, r["relation_type"]) for r in relations]
                )
        conn.commit()
    finally:
        conn.close()


def add_asset_relation(parent_pnum, child_pnum, relation_type, description=None):
    execute_query(
        """INSERT IGNORE INTO asset_relation
           (parent_pnum, child_pnum, relation_type, description)
           VALUES (%s,%s,%s,%s)""",
        (parent_pnum, child_pnum, relation_type, description),
        fetch_all=False
    )


def delete_asset_relation(relation_id):
    execute_query(
        "DELETE FROM asset_relation WHERE id = %s", (relation_id,), fetch_all=False
    )


# =============================================================
# 자산 검색 (AJAX autocomplete)
# =============================================================

def search_asset_info(keyword, grp_filter=None, limit=20):
    """servername / hostname / IP 로 자산 검색"""
    sql = """
        SELECT DISTINCT ai.pnum, ai.hostname, ai.servername, ai.grp, ai.status,
               GROUP_CONCAT(aip.ip SEPARATOR ',') AS ip
        FROM asset_info ai
        LEFT JOIN asset_ip aip ON ai.pnum = aip.asset_pnum
        WHERE (ai.servername LIKE %s OR ai.hostname LIKE %s OR aip.ip LIKE %s)
    """
    params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
    if grp_filter:
        sql += " AND ai.grp LIKE %s"
        params.append(f"%{grp_filter}%")
    sql += " GROUP BY ai.pnum LIMIT %s"
    params.append(limit)
    return execute_query(sql, params)


# =============================================================
# ENUM 옵션 상수 (info_ 테이블 대체)
# =============================================================

ASSET_OPTIONS = {
    "grp": [
        "서버>x86", "서버>Unix", "서버>Public Cloud", "서버>기타",
        "스토리지>스토리지 장비", "스토리지>SAN 스위치", "스토리지>기타 스토리지",
        "백업장비>백업장비", "백업장비>PTL", "백업장비>기타 백업장비",
    ],
    "oper":         ["DEV", "PROD", "QA", "DR"],
    "center":       ["IDC", "63DR"],
    "network_zone": ["내부", "외부"],
    "asset_type":   ["물리", "논리"],
    "purpose":      ["WEB", "WAS", "DB", "VDI", "콘솔", "FS", "SW"],
    "os":           ["LINUX", "WINDOWS", "AIX", "HPUX", "기타"],
    "status":       ["사용", "유휴", "폐기"],
    "importance":   ["일반", "핵심"],
    "power":        ["이중화(AB)", "단일(A)", "단일(B)", "단일(S)"],
    "relation_type":["VM", "DR", "이중화(A-A)", "이중화(A-S)", "기타"],
    "link_type":    ["ITSM", "ITMS", "HiON", "기타"],
    "ip_type":      ["내부", "외부", "관리", "기타"],
}
