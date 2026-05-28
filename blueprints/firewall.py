from flask import Blueprint, render_template, request, jsonify
import threading

from utils.firewall_collector import (
    get_fw_settings, save_fw_settings,
    collect_all_firewall_data, get_collection_status,
    restart_scheduler,
    get_all_fw_servers, search_fw_servers,
    get_fw_server_detail, check_firewall_access,
)

firewall_bp = Blueprint('firewall', __name__)


@firewall_bp.route('/')
def index():
    return render_template('firewall/index.html')


# ── 설정 ──────────────────────────────────────────────────
@firewall_bp.route('/settings', methods=['GET'])
def get_settings():
    return jsonify(get_fw_settings())


@firewall_bp.route('/settings', methods=['POST'])
def update_settings():
    data = request.get_json() or {}
    try:
        save_fw_settings(data)
        restart_scheduler()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── 수집 ──────────────────────────────────────────────────
@firewall_bp.route('/collect', methods=['POST'])
def trigger_collect():
    status = get_collection_status()
    if status['running']:
        return jsonify({'success': False, 'error': '이미 수집 중입니다.'})
    t = threading.Thread(target=collect_all_firewall_data, daemon=True, name='fw-collect')
    t.start()
    return jsonify({'success': True, 'message': '수집을 시작합니다.'})


@firewall_bp.route('/collect_status')
def collect_status():
    return jsonify(get_collection_status())


# ── 서버 조회 ──────────────────────────────────────────────
@firewall_bp.route('/servers')
def list_servers():
    return jsonify(get_all_fw_servers())


@firewall_bp.route('/search_servers')
def search_servers_api():
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return jsonify([])
    return jsonify(search_fw_servers(keyword))


@firewall_bp.route('/server/<int:resource_id>')
def server_detail(resource_id):
    detail = get_fw_server_detail(resource_id)
    if not detail:
        return jsonify({'error': '서버를 찾을 수 없습니다.'}), 404
    return jsonify(detail)


# ── 방화벽 통과 확인 ──────────────────────────────────────
@firewall_bp.route('/check', methods=['POST'])
def check_access():
    data = request.get_json() or {}
    src_ip   = data.get('src_ip',   '').strip()
    dst_ip   = data.get('dst_ip',   '').strip()
    dst_port = data.get('dst_port', '').strip()
    protocol = data.get('protocol', 'tcp').lower()

    if not src_ip or not dst_ip or not dst_port:
        return jsonify({'error': '출발지 IP, 목적지 IP, 포트를 모두 입력하세요.'}), 400

    try:
        result = check_firewall_access(src_ip, dst_ip, dst_port, protocol)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
