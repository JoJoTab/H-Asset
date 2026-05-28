"""
OS 방화벽 데이터 수집 및 방화벽 통과 확인 모듈

수집 흐름:
  1. GET /rest/resource/list?type=all  → server.Server 리소스 추출
  2. GET /rest/resource/list?type=management.MonitorGroup  → 모니터 그룹 (parentId=서버 id)
  3. GET /rest/resource/list?type=<fw_monitor_type>  → OS방화벽 서브모니터 (parentId=그룹 id)
  4. GET /rest/measure/custom?resourceId=<fw_monitor_id>  → ZONE1~ZONE10, HOSTS ALLOW 측정값
"""
import ipaddress
import re
import time
import threading
import traceback
from datetime import datetime

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

from utils.db import get_db_connection, execute_query


# ─────────────────────────────────────────────────────────
# 수집 진행 상태 (전역, 스레드 안전)
# ─────────────────────────────────────────────────────────
_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'message': '대기 중',
    'last_completed': None,
    'error': None,
}
_status_lock = threading.Lock()

_scheduler_thread = None
_scheduler_stop = threading.Event()


# ─────────────────────────────────────────────────────────
# 설정 관리
# ─────────────────────────────────────────────────────────
_DEFAULT_SETTINGS = {
    'polaris_base_url': 'https://hsms.hanwhalife.com/rest',
    'fw_monitor_type': (
        'com.nkia.cygnus.plugins.server.domain.'
        'ScriptCustomMonitor-924fe3c4-9129-4916-8230-c9026ed09def'
    ),
    'rate_limit_count': 1,
    'rate_limit_seconds': 1,
    'auto_collect_enabled': 0,
    'auto_collect_interval_hours': 6,
}


def get_fw_settings() -> dict:
    row = execute_query(
        "SELECT * FROM hli_asset_network_firewall_settings WHERE id = 1",
        fetch_all=False,
    )
    return dict(row) if row else dict(_DEFAULT_SETTINGS)


def save_fw_settings(data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO hli_asset_network_firewall_settings
                (id, polaris_base_url, fw_monitor_type,
                 rate_limit_count, rate_limit_seconds,
                 auto_collect_enabled, auto_collect_interval_hours)
            VALUES (1, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                polaris_base_url            = VALUES(polaris_base_url),
                fw_monitor_type             = VALUES(fw_monitor_type),
                rate_limit_count            = VALUES(rate_limit_count),
                rate_limit_seconds          = VALUES(rate_limit_seconds),
                auto_collect_enabled        = VALUES(auto_collect_enabled),
                auto_collect_interval_hours = VALUES(auto_collect_interval_hours)
        """, (
            data.get('polaris_base_url', _DEFAULT_SETTINGS['polaris_base_url']),
            data.get('fw_monitor_type',  _DEFAULT_SETTINGS['fw_monitor_type']),
            max(1, min(10, int(data.get('rate_limit_count', 1)))),
            max(1,          int(data.get('rate_limit_seconds', 1))),
            1 if data.get('auto_collect_enabled') else 0,
            max(1,          int(data.get('auto_collect_interval_hours', 6))),
        ))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────────────────
# REST API 호출
# ─────────────────────────────────────────────────────────
def _api_get(url: str, sess=None) -> dict:
    r = (sess or requests).get(url, timeout=10, verify=False)
    r.raise_for_status()
    return r.json()


def _get_resource_list(base_url: str, resource_type: str, sess=None) -> list:
    data = _api_get(f"{base_url}/resource/list?type={resource_type}", sess)
    return data.get('data', {}).get('list', [])


def _get_measurements(base_url: str, resource_id: int, sess=None) -> list:
    data = _api_get(f"{base_url}/measure/custom?resourceId={resource_id}", sess)
    return data.get('data', {}).get('measurement', [])


# ─────────────────────────────────────────────────────────
# 파싱
# ─────────────────────────────────────────────────────────
def _parse_zone_value(raw: str):
    """
    폴스타에서 수집된 ZONE 측정값 문자열을 파싱.
    예시:
      [ZONE]: 01_SMS
       [Sources] :10.0.0.0/8 10.253.16.0/22 ...
       [Ports] :80/tcp 443/tcp ...
       [Rich Rules] :
        rule family="ipv4" source address="10.x.x.x/32" port port="443" protocol="tcp" accept
    """
    if not raw or raw.strip() in ('None', ''):
        return None

    zone_name = None
    sources = []
    ports = []
    services = []
    interfaces = []
    rich_rules = []
    in_rich = False

    for line in raw.split('\n'):
        s = line.strip()
        if not s:
            continue

        if re.match(r'^\[?ZONE\]?:', s):
            zone_name = re.sub(r'^\[?ZONE\]?:\s*\[?', '', s).rstrip(']').strip()
            in_rich = False
        elif re.match(r'^\[Sources\]\s*:', s):
            sources = re.sub(r'^\[Sources\]\s*:\s*', '', s).split()
            in_rich = False
        elif re.match(r'^\[Ports\]\s*:', s):
            ports = re.sub(r'^\[Ports\]\s*:\s*', '', s).split()
            in_rich = False
        elif re.match(r'^\[Services\]\s*:', s):
            services = re.sub(r'^\[Services\]\s*:\s*', '', s).split()
            in_rich = False
        elif re.match(r'^\[Interfaces\]\s*:', s):
            interfaces = re.sub(r'^\[Interfaces\]\s*:\s*', '', s).split()
            in_rich = False
        elif re.match(r'^\[Rich Rules\]\s*:', s):
            in_rich = True
        elif in_rich:
            if s.startswith('rule '):
                rich_rules.append(s)
            # 'rich rules:' 레이블은 무시
        elif s.startswith('rule '):
            # Zone 헤더 없이 rich rule만 있는 경우 (예: ZONE9)
            rich_rules.append(s)

    # 아무 유효 데이터도 없으면 None 반환
    if not zone_name and not sources and not ports and not rich_rules:
        return None

    return {
        'zone_name': zone_name,
        'sources':    ' '.join(sources),
        'ports':      ' '.join(ports),
        'services':   ' '.join(services),
        'interfaces': ' '.join(interfaces),
        'rich_rules': '\n'.join(rich_rules),
        'raw_value':  raw,
    }


def _parse_measurements(measurements: list) -> dict:
    """측정값 리스트에서 ZONE 데이터, HOSTS ALLOW, 가용성을 추출."""
    zones = []
    hosts_allow = None
    availability = None
    error_msg = None

    for m in measurements:
        name  = m.get('definitionName', '')
        value = m.get('value', '') or ''

        if name == 'HOSTS ALLOW':
            hosts_allow = value if value not in ('None', '') else None
        elif name == '가용성':
            availability = value
        elif name == '오류 내용':
            error_msg = value if value else None
        elif re.match(r'^ZONE\d+$', name):
            parsed = _parse_zone_value(value)
            if parsed:
                zones.append(parsed)

    return {
        'zones':        zones,
        'hosts_allow':  hosts_allow,
        'availability': availability,
        'error_msg':    error_msg,
    }


# ─────────────────────────────────────────────────────────
# DB 저장
# ─────────────────────────────────────────────────────────
def _upsert_server(resource_id, name, ip_address,
                   monitor_group_id, fw_monitor_id,
                   availability, error_msg, collected_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO hli_asset_network_firewall_server
                (resource_id, name, ip_address, monitor_group_id, fw_monitor_id,
                 availability, error_msg, last_collected)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name             = VALUES(name),
                ip_address       = VALUES(ip_address),
                monitor_group_id = VALUES(monitor_group_id),
                fw_monitor_id    = VALUES(fw_monitor_id),
                availability     = VALUES(availability),
                error_msg        = VALUES(error_msg),
                last_collected   = VALUES(last_collected)
        """, (resource_id, name, ip_address, monitor_group_id, fw_monitor_id,
              availability, error_msg, collected_at))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _replace_zones(resource_id, zones: list, collected_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM hli_asset_network_firewall_zone WHERE resource_id = %s",
            (resource_id,)
        )
        if zones:
            cursor.executemany("""
                INSERT INTO hli_asset_network_firewall_zone
                    (resource_id, zone_name, sources, ports, services,
                     interfaces, rich_rules, raw_value, collected_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                (resource_id,
                 z['zone_name'], z['sources'], z['ports'], z['services'],
                 z['interfaces'], z['rich_rules'], z['raw_value'], collected_at)
                for z in zones
            ])
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _replace_hosts_allow(resource_id, hosts_allow, collected_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM hli_asset_network_firewall_hosts_allow WHERE resource_id = %s",
            (resource_id,)
        )
        if hosts_allow is not None:
            cursor.execute("""
                INSERT INTO hli_asset_network_firewall_hosts_allow
                    (resource_id, hosts_allow, collected_at)
                VALUES (%s, %s, %s)
            """, (resource_id, hosts_allow, collected_at))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────────────────
# 수집 메인 로직
# ─────────────────────────────────────────────────────────
def collect_all_firewall_data():
    """모든 서버의 OS 방화벽 데이터를 폴스타 REST API에서 수집하여 DB에 저장."""
    if not _REQUESTS_OK:
        with _status_lock:
            _status.update({'running': False, 'error': "'requests' 패키지가 설치되어 있지 않습니다."})
        return

    settings = get_fw_settings()
    base_url        = settings['polaris_base_url']
    fw_monitor_type = settings['fw_monitor_type']
    rate_count      = max(1, min(10, int(settings['rate_limit_count'])))
    rate_secs       = max(1,          int(settings['rate_limit_seconds']))

    with _status_lock:
        _status.update({
            'running': True, 'progress': 0, 'total': 0,
            'message': '수집 시작...', 'error': None,
        })

    sess = requests.Session()
    try:
        # 1단계: 서버 목록
        with _status_lock:
            _status['message'] = '1/4 서버 목록 수집 중...'
        all_res = _get_resource_list(base_url, 'all', sess)
        servers = {r['id']: r for r in all_res if r.get('resourceType') == 'server.Server'}

        # 2단계: 모니터 그룹
        with _status_lock:
            _status['message'] = '2/4 모니터 그룹 수집 중...'
        groups = _get_resource_list(base_url, 'management.MonitorGroup', sess)
        # server_id → [group_id, ...]
        srv_to_grps: dict[int, list[int]] = {}
        for g in groups:
            pid = g.get('parentId')
            if pid in servers:
                srv_to_grps.setdefault(pid, []).append(g['id'])

        # 3단계: OS방화벽 서브모니터
        with _status_lock:
            _status['message'] = '3/4 OS방화벽 모니터 수집 중...'
        fw_mons = _get_resource_list(base_url, fw_monitor_type, sess)
        # group_id → fw_monitor_id
        grp_to_fw: dict[int, int] = {m['parentId']: m['id'] for m in fw_mons}

        # 수집 대상: (server, group_id, fw_monitor_id)
        targets = []
        for srv_id, srv in servers.items():
            for grp_id in srv_to_grps.get(srv_id, []):
                fw_id = grp_to_fw.get(grp_id)
                if fw_id:
                    targets.append((srv, grp_id, fw_id))
                    break

        with _status_lock:
            _status['total'] = len(targets)
            _status['message'] = f'4/4 측정값 수집 중 (총 {len(targets)}개 서버)...'

        # 4단계: 측정값 수집 (rate limiting)
        req_count = 0
        for i, (srv, grp_id, fw_id) in enumerate(targets):
            try:
                with _status_lock:
                    _status['progress'] = i
                    _status['message'] = f"수집 중: {srv['name']} ({i + 1}/{len(targets)})"

                if req_count > 0 and req_count % rate_count == 0:
                    time.sleep(rate_secs)
                req_count += 1

                measurements = _get_measurements(base_url, fw_id, sess)
                parsed = _parse_measurements(measurements)
                now = datetime.now()

                _upsert_server(
                    resource_id=srv['id'],
                    name=srv['name'],
                    ip_address=srv.get('ipAddress'),
                    monitor_group_id=grp_id,
                    fw_monitor_id=fw_id,
                    availability=parsed['availability'],
                    error_msg=parsed['error_msg'],
                    collected_at=now,
                )
                _replace_zones(srv['id'], parsed['zones'], now)
                _replace_hosts_allow(srv['id'], parsed['hosts_allow'], now)

            except Exception as e:
                print(f"[FW Collector] {srv.get('name')} 수집 실패: {e}")
                continue

        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with _status_lock:
            _status.update({
                'running': False,
                'progress': len(targets),
                'message': f'수집 완료 ({len(targets)}개 서버)',
                'last_completed': completed_at,
                'error': None,
            })

    except Exception as e:
        with _status_lock:
            _status.update({
                'running': False,
                'message': '수집 실패',
                'error': str(e),
            })
        print(f"[FW Collector] 치명적 오류:\n{traceback.format_exc()}")


def get_collection_status() -> dict:
    with _status_lock:
        return dict(_status)


# ─────────────────────────────────────────────────────────
# 자동 스케줄러
# ─────────────────────────────────────────────────────────
def start_scheduler():
    global _scheduler_thread
    settings = get_fw_settings()
    if not settings.get('auto_collect_enabled'):
        return
    interval_secs = int(settings.get('auto_collect_interval_hours', 6)) * 3600

    _scheduler_stop.clear()

    def _run():
        while not _scheduler_stop.wait(interval_secs):
            try:
                collect_all_firewall_data()
            except Exception as e:
                print(f"[FW Scheduler] 오류: {e}")

    _scheduler_thread = threading.Thread(target=_run, daemon=True, name='fw-scheduler')
    _scheduler_thread.start()


def stop_scheduler():
    _scheduler_stop.set()


def restart_scheduler():
    stop_scheduler()
    time.sleep(0.2)
    start_scheduler()


# ─────────────────────────────────────────────────────────
# 조회 함수
# ─────────────────────────────────────────────────────────
def _dt(v):
    """datetime → 문자열 변환 (JSON 직렬화용)."""
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    return v


def _clean_row(row: dict) -> dict:
    return {k: _dt(v) for k, v in row.items()}


def get_all_fw_servers() -> list:
    rows = execute_query("""
        SELECT resource_id, name, ip_address,
               availability, error_msg, last_collected
        FROM hli_asset_network_firewall_server
        ORDER BY name
    """)
    return [_clean_row(r) for r in rows]


def search_fw_servers(keyword: str) -> list:
    kw = f"%{keyword}%"
    rows = execute_query("""
        SELECT resource_id, name, ip_address, availability, last_collected
        FROM hli_asset_network_firewall_server
        WHERE name LIKE %s OR ip_address LIKE %s
        ORDER BY name
        LIMIT 30
    """, (kw, kw))
    return [_clean_row(r) for r in rows]


def get_fw_server_detail(resource_id: int):
    server = execute_query("""
        SELECT resource_id, name, ip_address,
               availability, error_msg, last_collected
        FROM hli_asset_network_firewall_server
        WHERE resource_id = %s
    """, (resource_id,), fetch_all=False)
    if not server:
        return None

    zones = execute_query("""
        SELECT id, zone_name, sources, ports, services, interfaces, rich_rules, collected_at
        FROM hli_asset_network_firewall_zone
        WHERE resource_id = %s
        ORDER BY id
    """, (resource_id,))

    ha_row = execute_query("""
        SELECT hosts_allow FROM hli_asset_network_firewall_hosts_allow
        WHERE resource_id = %s
        ORDER BY id DESC LIMIT 1
    """, (resource_id,), fetch_all=False)

    result = _clean_row(server)
    result['zones'] = [_clean_row(z) for z in zones]
    result['hosts_allow'] = ha_row['hosts_allow'] if ha_row else None
    return result


def get_fw_server_by_ip(ip_address: str):
    row = execute_query("""
        SELECT resource_id, name, ip_address, availability, last_collected
        FROM hli_asset_network_firewall_server
        WHERE ip_address = %s
        LIMIT 1
    """, (ip_address,), fetch_all=False)
    return _clean_row(row) if row else None


# ─────────────────────────────────────────────────────────
# 방화벽 통과 확인
# ─────────────────────────────────────────────────────────
def _ip_in_source(ip_str: str, source_str: str) -> bool:
    """IP 주소가 source (IP 또는 CIDR)에 속하는지 확인."""
    try:
        return (
            ipaddress.ip_address(ip_str.strip())
            in ipaddress.ip_network(source_str.strip(), strict=False)
        )
    except ValueError:
        return ip_str.strip() == source_str.strip()


def check_firewall_access(src_ip: str, dst_ip: str,
                          dst_port: str, protocol: str = 'tcp') -> dict:
    """
    src_ip → dst_ip:dst_port 통신이 목적지 서버 OS방화벽에서 허용되는지 확인.

    반환:
        result      : 'ALLOWED' | 'BLOCKED' | 'UNKNOWN'
        server      : 서버 정보 (name, ip, availability, last_collected)
        matched     : 매칭된 규칙 목록 (result=ALLOWED 시)
        zones_checked: 검사한 Zone 수
    """
    server = get_fw_server_by_ip(dst_ip)
    if not server:
        return {
            'result': 'UNKNOWN',
            'reason': f'{dst_ip} 는 모니터링 대상 서버가 아닙니다.',
            'server': None,
            'matched': [],
            'zones_checked': 0,
        }

    zones = execute_query("""
        SELECT zone_name, sources, ports, services, rich_rules
        FROM hli_asset_network_firewall_zone
        WHERE resource_id = %s
    """, (server['resource_id'],))

    if not zones:
        return {
            'result': 'UNKNOWN',
            'reason': '방화벽 데이터가 수집되지 않았습니다. 데이터 수집 후 다시 시도하세요.',
            'server': server,
            'matched': [],
            'zones_checked': 0,
        }

    matched = []
    dst_port_str = str(dst_port)

    for zone in zones:
        sources_list = (zone['sources'] or '').split()
        ports_list   = (zone['ports']   or '').split()
        rich_text    = zone['rich_rules'] or ''

        # Zone 레벨 소스 + 포트 체크
        src_ok  = any(_ip_in_source(src_ip, s) for s in sources_list) if sources_list else False
        port_ok = any(
            p.split('/')[0] == dst_port_str
            for p in ports_list
        ) if ports_list else False

        if src_ok and port_ok:
            matched.append({
                'type':    'zone',
                'zone':    zone['zone_name'],
                'sources': zone['sources'],
                'ports':   zone['ports'],
            })

        # Rich rules 체크 (accept 만)
        for rule in rich_text.split('\n'):
            rule = rule.strip()
            if not rule or 'accept' not in rule:
                continue
            m_src  = re.search(r'source address="([^"]+)"', rule)
            m_port = re.search(r'port port="([^"]+)"', rule)
            if m_src and m_port:
                if (_ip_in_source(src_ip, m_src.group(1))
                        and m_port.group(1) == dst_port_str):
                    matched.append({
                        'type': 'rich_rule',
                        'zone': zone['zone_name'],
                        'rule': rule,
                    })

    return {
        'result':        'ALLOWED' if matched else 'BLOCKED',
        'server':        server,
        'matched':       matched,
        'zones_checked': len(zones),
    }
