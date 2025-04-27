from flask import Blueprint, render_template, redirect, url_for, request, send_file, flash, abort, jsonify
import os
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
import aiofiles
from utils.cache import cache
import shutil
from werkzeug.utils import secure_filename

file_bp = Blueprint('file', __name__)


class FileForm(FlaskForm):
    """파일 업로드 폼"""
    files = FileField(validators=[FileRequired('업로드할 파일을 넣어주세요')])


def is_safe_path(base_path, requested_path):
    """경로가 안전한지 확인 (base_path 상위로 이동 불가)"""
    # 절대 경로로 변환
    base_path = os.path.abspath(base_path)
    requested_path = os.path.abspath(requested_path)

    # 요청된 경로가 기본 경로 내에 있는지 확인
    return requested_path.startswith(base_path)


@file_bp.route('/fileindex', methods=['GET', 'POST'])
def fileindex():
    """파일 관리 페이지"""
    form = FileForm()  # 파일 유효성 폼 클래스 인스턴스 생성

    # 기본 경로 설정 (uploads 폴더)
    base_path = os.path.abspath('./uploads')

    # uploads 폴더가 없으면 생성
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)

    # 요청된 경로 가져오기
    current_path = request.args.get('path', base_path)

    # 경로 안전성 검사
    if not is_safe_path(base_path, current_path):
        flash('접근할 수 없는 경로입니다.', 'danger')
        return redirect(url_for('file.fileindex', path=base_path))

    # 경로가 존재하지 않으면 기본 경로로 리다이렉트
    if not os.path.exists(current_path):
        flash('요청한 경로가 존재하지 않습니다.', 'warning')
        return redirect(url_for('file.fileindex', path=base_path))

    # 상위 디렉토리 경로 계산
    parent_path = os.path.dirname(current_path)

    # 상위 경로가 base_path 밖으로 나가지 않도록 확인
    if not is_safe_path(base_path, parent_path):
        parent_path = base_path

    # 파일 업로드 처리
    if form.validate_on_submit():
        f = form.files.data
        filename = secure_filename(f.filename)  # 파일명 보안 처리
        file_path = os.path.join(current_path, filename)

        # 파일 저장
        try:
            f.save(file_path)
            flash(f'파일 "{filename}"이 성공적으로 업로드되었습니다.', 'success')
        except Exception as e:
            flash(f'파일 업로드 중 오류가 발생했습니다: {str(e)}', 'danger')

        return redirect(url_for('file.fileindex', path=current_path))

    # 새 폴더 생성
    if request.method == 'POST' and 'create_folder' in request.form:
        folder_name = request.form['folder_name']

        # 폴더명 유효성 검사
        if not folder_name or '/' in folder_name or '\\' in folder_name:
            flash('유효하지 않은 폴더 이름입니다.', 'danger')
        else:
            folder_path = os.path.join(current_path, folder_name)

            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    flash(f'폴더 "{folder_name}"가 생성되었습니다.', 'success')
                except Exception as e:
                    flash(f'폴더 생성 중 오류가 발생했습니다: {str(e)}', 'danger')
            else:
                flash(f'폴더 "{folder_name}"가 이미 존재합니다.', 'warning')

        return redirect(url_for('file.fileindex', path=current_path))

    # 폴더 삭제 처리
    if request.method == 'POST' and 'delete_folder' in request.form:
        folder_name = request.form['folder_name']
        folder_path = os.path.join(current_path, folder_name)

        if os.path.isdir(folder_path):
            try:
                if os.listdir(folder_path):  # 폴더가 비어있지 않은 경우
                    if request.form.get('force_delete') == 'true':
                        shutil.rmtree(folder_path)  # 강제 삭제
                        flash(f'폴더 "{folder_name}"와 그 내용이 삭제되었습니다.', 'success')
                    else:
                        flash(f'폴더 "{folder_name}"가 비어있지 않습니다. 강제 삭제하려면 확인해주세요.', 'warning')
                        return render_template('fileindex.html', form=form,
                                               pwd=current_path, parent_path=parent_path,
                                               infos=get_directory_contents(current_path),
                                               confirm_delete=folder_name,
                                               base_path=base_path,
                                               relative_path=os.path.relpath(current_path, base_path))
                else:
                    os.rmdir(folder_path)  # 빈 폴더 삭제
                    flash(f'폴더 "{folder_name}"가 삭제되었습니다.', 'success')
            except Exception as e:
                flash(f'폴더 삭제 중 오류가 발생했습니다: {str(e)}', 'danger')
        else:
            flash(f'폴더 "{folder_name}"가 존재하지 않습니다.', 'error')

        return redirect(url_for('file.fileindex', path=current_path))

    # 파일 및 폴더 정보 가져오기
    infos = get_directory_contents(current_path)

    return render_template('fileindex.html', form=form,
                           pwd=current_path, parent_path=parent_path,
                           infos=infos, base_path=base_path,
                           relative_path=os.path.relpath(current_path, base_path))


def get_directory_contents(path):
    """디렉토리 내용 가져오기"""
    infos = []

    try:
        filelist = os.listdir(path)

        # 폴더를 먼저, 파일을 나중에 정렬
        folders = []
        files = []

        for name in filelist:
            fileinfo = {}
            full_path = os.path.join(path, name)
            ctime = os.path.getctime(full_path)
            mtime = os.path.getmtime(full_path)

            if os.path.isdir(full_path):  # 디렉토리인지 확인
                fileinfo["name"] = name
                fileinfo["create"] = datetime.fromtimestamp(ctime)
                fileinfo["modify"] = datetime.fromtimestamp(mtime)
                fileinfo["size"] = "폴더"
                fileinfo["isfile"] = False
                folders.append(fileinfo)
            else:
                size = os.path.getsize(full_path)
                fileinfo["name"] = name
                fileinfo["create"] = datetime.fromtimestamp(ctime)
                fileinfo["modify"] = datetime.fromtimestamp(mtime)
                fileinfo["isfile"] = True

                # 파일 확장자 추출
                _, ext = os.path.splitext(name)
                fileinfo["extension"] = ext.lower()[1:] if ext else ""

                # 파일 크기 포맷팅
                if size < 1024:
                    fileinfo["size"] = f"{size} B"
                elif size < 1024 * 1024:
                    fileinfo["size"] = f"{size / 1024:.2f} KB"
                elif size < 1024 * 1024 * 1024:
                    fileinfo["size"] = f"{size / (1024 * 1024):.2f} MB"
                else:
                    fileinfo["size"] = f"{size / (1024 * 1024 * 1024):.2f} GB"

                files.append(fileinfo)

        # 폴더와 파일을 각각 이름순으로 정렬 후 합치기
        folders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        infos = folders + files

    except Exception as e:
        flash(f'디렉토리 내용을 읽는 중 오류가 발생했습니다: {str(e)}', 'danger')

    return infos


@file_bp.route('/download/<path:filename>')
def download_file(filename):
    """파일 다운로드"""
    base_path = os.path.abspath('./uploads')
    file_path = os.path.join(base_path, filename)

    # 경로 안전성 검사
    if not is_safe_path(base_path, file_path):
        abort(403)  # 접근 금지

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        flash('파일이 존재하지 않습니다.', 'error')
        return redirect(url_for('file.fileindex'))

    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))


@file_bp.route('/delete/<path:filename>')
def delete_file(filename):
    """파일 삭제"""
    base_path = os.path.abspath('./uploads')
    file_path = os.path.join(base_path, filename)

    # 경로 안전성 검사
    if not is_safe_path(base_path, file_path):
        abort(403)  # 접근 금지

    # 파일 존재 여부 확인
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        flash('파일이 존재하지 않습니다.', 'error')
        return redirect(url_for('file.fileindex'))

    # 파일 삭제
    try:
        os.remove(file_path)
        flash(f'파일 "{os.path.basename(file_path)}"가 삭제되었습니다.', 'success')
    except Exception as e:
        flash(f'파일 삭제 중 오류가 발생했습니다: {str(e)}', 'danger')

    # 삭제 후 원래 디렉토리로 리다이렉트
    directory = os.path.dirname(file_path)
    return redirect(url_for('file.fileindex', path=directory))


@file_bp.route('/preview/<path:filename>')
def preview_file(filename):
    """파일 미리보기"""
    base_path = os.path.abspath('./uploads')
    file_path = os.path.join(base_path, filename)

    # 경로 안전성 검사
    if not is_safe_path(base_path, file_path):
        abort(403)  # 접근 금지

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        flash('파일이 존재하지 않습니다.', 'error')
        return redirect(url_for('file.fileindex'))

    # 파일 확장자 확인
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # 미리보기 가능한 파일 타입
    previewable_types = {
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'text/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv'
    }

    if ext in previewable_types:
        return send_file(file_path, mimetype=previewable_types[ext])
    else:
        # 미리보기 불가능한 파일은 다운로드
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
