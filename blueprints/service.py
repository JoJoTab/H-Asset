from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, send_file, current_app
from utils.db import get_db_connection, execute_query
from flask_ckeditor import upload_success, upload_fail
import pymysql
import os
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

service_bp = Blueprint('service', __name__, url_prefix='/service')


@service_bp.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT app_idx, app_servicecode, app_name, app_group, app_domain, app_appcode
            FROM info_service
            ORDER BY app_servicecode
        """)
        services = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching services: {e}")
        services = []
    finally:
        cursor.close()
        conn.close()

    return render_template('service/index.html', services=services)


@service_bp.route('/add', methods=['GET', 'POST'])
def add_service():
    if request.method == 'POST':
        app_servicecode = request.form.get('app_servicecode')
        app_name = request.form.get('app_name')
        app_group = request.form.get('app_group')
        app_domain = request.form.get('app_domain')
        app_appcode = request.form.get('app_appcode')
        app_comment = request.form.get('app_comment', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO info_service (app_servicecode, app_name, app_group, app_domain, app_appcode, app_comment)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (app_servicecode, app_name, app_group, app_domain, app_appcode, app_comment))

            # 새로 생성된 서비스의 app_idx 가져오기
            app_idx = cursor.lastrowid

            # 서비스 파일 디렉토리 생성
            service_dir = os.path.join(current_app.root_path, 'autodata', 'service', f"{app_servicecode}-{app_idx}")
            os.makedirs(service_dir, exist_ok=True)

            conn.commit()
            flash('서비스가 성공적으로 추가되었습니다.', 'success')
            return redirect(url_for('service.index'))
        except Exception as e:
            conn.rollback()
            flash(f'서비스 추가 중 오류가 발생했습니다: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('service/add.html')


@service_bp.route('/edit/<int:app_idx>', methods=['GET', 'POST'])
def edit_service(app_idx):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        app_servicecode = request.form.get('app_servicecode')
        app_name = request.form.get('app_name')
        app_group = request.form.get('app_group')
        app_domain = request.form.get('app_domain')
        app_appcode = request.form.get('app_appcode')
        app_comment = request.form.get('app_comment', '')

        try:
            # 기존 서비스 코드 가져오기
            cursor.execute("SELECT app_servicecode FROM info_service WHERE app_idx = %s", (app_idx,))
            old_service = cursor.fetchone()
            old_servicecode = old_service['app_servicecode'] if old_service else None

            # 서비스 정보 업데이트
            cursor.execute("""
                UPDATE info_service
                SET app_servicecode = %s, app_name = %s, app_group = %s, app_domain = %s, app_appcode = %s, app_comment = %s
                WHERE app_idx = %s
            """, (app_servicecode, app_name, app_group, app_domain, app_appcode, app_comment, app_idx))

            # 서비스 코드가 변경된 경우 디렉토리 이름 변경
            if old_servicecode and old_servicecode != app_servicecode:
                old_dir = os.path.join(current_app.root_path, 'autodata', 'service', f"{old_servicecode}-{app_idx}")
                new_dir = os.path.join(current_app.root_path, 'autodata', 'service', f"{app_servicecode}-{app_idx}")

                if os.path.exists(old_dir):
                    os.makedirs(os.path.dirname(new_dir), exist_ok=True)
                    shutil.move(old_dir, new_dir)

            conn.commit()
            flash('서비스가 성공적으로 수정되었습니다.', 'success')
            return redirect(url_for('service.index'))
        except Exception as e:
            conn.rollback()
            flash(f'서비스 수정 중 오류가 발생했습니다: {e}', 'danger')

    try:
        # 서비스 정보 가져오기
        cursor.execute("""
            SELECT app_idx, app_servicecode, app_name, app_group, app_domain, app_appcode, app_comment
            FROM info_service
            WHERE app_idx = %s
        """, (app_idx,))
        service = cursor.fetchone()

        if not service:
            flash('해당 서비스를 찾을 수 없습니다.', 'danger')
            return redirect(url_for('service.index'))

        # 연계된 자산 목록 가져오기
        cursor.execute("""
            SELECT a.pnum, a.servername, a.hostname, a.ip
            FROM total_asset a
            JOIN total_service ts ON a.pnum = ts.service_pnum
            WHERE ts.service_appidx = %s
        """, (app_idx,))
        linked_assets = cursor.fetchall()

        # 서비스 파일 목록 가져오기
        service_files = []
        service_dir = os.path.join(current_app.root_path, 'autodata', 'service',
                                   f"{service['app_servicecode']}-{app_idx}")

        if os.path.exists(service_dir):
            for filename in os.listdir(service_dir):
                file_path = os.path.join(service_dir, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_str = format_file_size(file_size)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                    service_files.append({
                        'filename': filename,
                        'size': file_size_str,
                        'upload_date': file_mtime.strftime('%Y-%m-%d %H:%M:%S')
                    })

    except Exception as e:
        flash(f'서비스 정보를 가져오는 중 오류가 발생했습니다: {e}', 'danger')
        return redirect(url_for('service.index'))
    finally:
        cursor.close()
        conn.close()

    return render_template('service/edit.html', service=service, linked_assets=linked_assets,
                           service_files=service_files)


@service_bp.route('/delete/<int:app_idx>', methods=['POST'])
def delete_service(app_idx):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        # 서비스 코드 가져오기
        cursor.execute("SELECT app_servicecode FROM info_service WHERE app_idx = %s", (app_idx,))
        service = cursor.fetchone()

        if service:
            # 서비스 디렉토리 삭제
            service_dir = os.path.join(current_app.root_path, 'autodata', 'service',
                                       f"{service['app_servicecode']}-{app_idx}")
            if os.path.exists(service_dir):
                shutil.rmtree(service_dir)

        # 먼저 연계 정보 삭제
        cursor.execute("DELETE FROM total_service WHERE service_appidx = %s", (app_idx,))

        # 서비스 정보 삭제
        cursor.execute("DELETE FROM info_service WHERE app_idx = %s", (app_idx,))

        conn.commit()
        flash('서비스가 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'서비스 삭제 중 오류가 발생했습니다: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('service.index'))


@service_bp.route('/linked_services/<int:pnum>')
def get_linked_services(pnum):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT s.app_idx, s.app_servicecode, s.app_name, s.app_group, s.app_domain, s.app_appcode
            FROM info_service s
            JOIN total_service ts ON s.app_idx = ts.service_appidx
            WHERE ts.service_pnum = %s
        """, (pnum,))
        services = cursor.fetchall()
        return jsonify(services)
    except Exception as e:
        print(f"Error fetching linked services: {e}")
        return jsonify([])
    finally:
        cursor.close()
        conn.close()


@service_bp.route('/link_asset', methods=['POST'])
def link_asset():
    app_idx = request.form.get('app_idx')
    pnum = request.form.get('pnum')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 이미 연계되어 있는지 확인
        cursor.execute("""
            SELECT COUNT(*) FROM total_service
            WHERE service_appidx = %s AND service_pnum = %s
        """, (app_idx, pnum))
        if cursor.fetchone()[0] > 0:
            return jsonify({'success': False, 'message': '이미 연계된 자산입니다.'})

        # 연계 정보 추가
        cursor.execute("""
            INSERT INTO total_service (service_appidx, service_pnum)
            VALUES (%s, %s)
        """, (app_idx, pnum))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


@service_bp.route('/unlink_asset', methods=['POST'])
def unlink_asset():
    app_idx = request.form.get('app_idx')
    pnum = request.form.get('pnum')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM total_service
            WHERE service_appidx = %s AND service_pnum = %s
        """, (app_idx, pnum))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


@service_bp.route('/search_assets')
def search_assets():
    term = request.args.get('term', '')

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT pnum, servername, hostname, ip
            FROM total_asset
            WHERE servername LIKE %s OR hostname LIKE %s OR ip LIKE %s
            LIMIT 50
        """, (f'%{term}%', f'%{term}%', f'%{term}%'))
        assets = cursor.fetchall()
        return jsonify(assets)
    except Exception as e:
        print(f"Error searching assets: {e}")
        return jsonify([])
    finally:
        cursor.close()
        conn.close()

@service_bp.route('/upload_file/<int:app_idx>', methods=['POST'])
def upload_file(app_idx):
    if 'file' not in request.files:
        flash('파일이 없습니다.', 'danger')
        return redirect(url_for('service.edit_service', app_idx=app_idx))

    file = request.files['file']

    if file.filename == '':
        flash('선택된 파일이 없습니다.', 'danger')
        return redirect(url_for('service.edit_service', app_idx=app_idx))

    try:
        # 서비스 코드 가져오기
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT app_servicecode FROM info_service WHERE app_idx = %s", (app_idx,))
        service = cursor.fetchone()
        cursor.close()
        conn.close()

        if not service:
            flash('서비스를 찾을 수 없습니다.', 'danger')
            return redirect(url_for('service.index'))

        # 서비스 디렉토리 경로 확인 및 생성
        base_dir = os.path.join(current_app.root_path, 'autodata', 'service')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        service_dir = os.path.join(base_dir, f"{service['app_servicecode']}-{app_idx}")
        if not os.path.exists(service_dir):
            os.makedirs(service_dir, exist_ok=True)

        # 파일 이름 보안 처리
        filename = secure_filename(file.filename)
        file_path = os.path.join(service_dir, filename)

        # 파일 저장
        file.save(file_path)

        flash('파일이 성공적으로 업로드되었습니다.', 'success')

    except Exception as e:
        flash(f'파일 업로드 중 오류가 발생했습니다: {e}', 'danger')

    return redirect(url_for('service.edit_service', app_idx=app_idx))


@service_bp.route('/download_file/<int:app_idx>/<path:filename>')
def download_file(app_idx, filename):
    try:
        # 서비스 코드 가져오기
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT app_servicecode FROM info_service WHERE app_idx = %s", (app_idx,))
        service = cursor.fetchone()
        cursor.close()
        conn.close()

        if not service:
            flash('서비스를 찾을 수 없습니다.', 'danger')
            return redirect(url_for('service.index'))

        # 파일 경로
        service_dir = os.path.join(current_app.root_path, 'autodata', 'service',
                                   f"{service['app_servicecode']}-{app_idx}")
        file_path = os.path.join(service_dir, filename)

        if not os.path.exists(file_path):
            flash('파일을 찾을 수 없습니다.', 'danger')
            return redirect(url_for('service.edit_service', app_idx=app_idx))

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        flash(f'파일 다운로드 중 오류가 발생했습니다: {e}', 'danger')
        return redirect(url_for('service.edit_service', app_idx=app_idx))


@service_bp.route('/delete_file/<int:app_idx>', methods=['POST'])
def delete_file(app_idx):
    filename = request.form.get('filename')

    if not filename:
        return jsonify({'success': False, 'message': '파일 이름이 제공되지 않았습니다.'})

    try:
        # 서비스 코드 가져오기
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT app_servicecode FROM info_service WHERE app_idx = %s", (app_idx,))
        service = cursor.fetchone()
        cursor.close()
        conn.close()

        if not service:
            return jsonify({'success': False, 'message': '서비스를 찾을 수 없습니다.'})

        # 파일 경로
        service_dir = os.path.join(current_app.root_path, 'autodata', 'service',
                                   f"{service['app_servicecode']}-{app_idx}")
        file_path = os.path.join(service_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'})

        # 파일 삭제
        os.remove(file_path)

        return jsonify({'success': True, 'message': '파일이 성공적으로 삭제되었습니다.'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# 유틸리티 함수
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def format_file_size(size_bytes):
    """파일 크기를 읽기 쉬운 형식으로 변환"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
