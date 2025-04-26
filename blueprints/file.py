from flask import Blueprint, render_template, redirect, url_for, request, send_file, flash
import os
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
import aiofiles
from utils.cache import cache

file_bp = Blueprint('file', __name__)


class FileForm(FlaskForm):
    """파일 업로드 폼"""
    files = FileField(validators=[FileRequired('업로드할 파일을 넣어주세요')])


@file_bp.route('/fileindex', methods=['GET', 'POST'])
def fileindex():
    """파일 관리 페이지"""
    form = FileForm()  # 파일 유효성 폼 클래스 인스턴스 생성
    current_path = request.args.get('path', './uploads')

    # 상위 디렉토리 경로 계산
    parent_path = os.path.dirname(current_path)

    if form.validate_on_submit():  # 양식 유효성 검사 + POST인 경우
        f = form.files.data
        file_path = os.path.join(current_path, f.filename)

        # 비동기적으로 파일 저장
        with open(file_path, 'wb') as out:
            out.write(f.read())

        flash('파일이 성공적으로 업로드되었습니다.', 'success')
        return redirect(f'/fileindex?path={current_path}')

    # 새 폴더 생성
    if request.method == 'POST' and 'create_folder' in request.form:
        folder_name = request.form['folder_name']
        folder_path = os.path.join(current_path, folder_name)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            flash(f'폴더 "{folder_name}"가 생성되었습니다.', 'success')
        else:
            flash(f'폴더 "{folder_name}"가 이미 존재합니다.', 'warning')

        return redirect(f'/fileindex?path={current_path}')

    # 폴더 삭제 처리
    if request.method == 'POST' and 'delete_folder' in request.form:
        folder_name = request.form['folder_name']
        folder_path = os.path.join(current_path, folder_name)

        if os.path.isdir(folder_path):
            try:
                os.rmdir(folder_path)  # 폴더 삭제
                flash(f'폴더 "{folder_name}"가 삭제되었습니다.', 'success')
            except OSError:
                flash(f'폴더 "{folder_name}"가 비어있지 않아 삭제할 수 없습니다.', 'error')
        else:
            flash(f'폴더 "{folder_name}"가 존재하지 않습니다.', 'error')

        return redirect(f'/fileindex?path={current_path}')

    # 파일 및 폴더 정보 가져오기
    filelist = os.listdir(current_path)
    infos = []

    for name in filelist:
        fileinfo = {}
        full_path = os.path.join(current_path, name)
        ctime = os.path.getctime(full_path)
        mtime = os.path.getmtime(full_path)

        if os.path.isdir(full_path):  # 디렉토리인지 확인
            fileinfo["name"] = name
            fileinfo["create"] = datetime.fromtimestamp(ctime)
            fileinfo["modify"] = datetime.fromtimestamp(mtime)
            fileinfo["size"] = "폴더"
            fileinfo["isfile"] = False
        else:
            size = os.path.getsize(full_path)
            fileinfo["name"] = name
            fileinfo["create"] = datetime.fromtimestamp(ctime)
            fileinfo["modify"] = datetime.fromtimestamp(mtime)
            fileinfo["isfile"] = True

            if size <= 1000000:
                fileinfo["size"] = "%.2f KB" % (size / 1024)
            else:
                fileinfo["size"] = "%.2f MB" % (size / (1024.0 * 1024.0))

        infos.append(fileinfo)

    return render_template('fileindex.html', form=form,
                           pwd=current_path, parent_path=parent_path, infos=infos)


@file_bp.route('/down/<path:filename>')
def down_page(filename):
    """파일 다운로드"""
    file_path = os.path.join(os.getcwd(), 'uploads', filename)
    return send_file(file_path, as_attachment=True)


@file_bp.route('/del/<path:filename>')
def delete_page(filename):
    """파일 삭제"""
    file_path = os.path.join('uploads', filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'파일 "{filename}"가 삭제되었습니다.', 'success')
    else:
        flash(f'파일 "{filename}"가 존재하지 않습니다.', 'error')

    return redirect('/fileindex')
