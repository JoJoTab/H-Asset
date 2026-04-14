from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, flash
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
from utils.db import execute_query, get_db_connection
import os
import tempfile

storage_bp = Blueprint('storage', __name__)


@storage_bp.route('/storage', methods=['GET', 'POST'])
def storage():
    """스토리지 관리 페이지"""
    connection = get_db_connection()
    data1 = {}
    data2 = []
    end_date = None
    start_date = None
    error_message = None
    graph_html_tl = None
    graph_html_use = None

    try:
        with connection.cursor() as cursor:
            # 전체 데이터 조회
            sql = "SELECT DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP FROM total_storage"
            cursor.execute(sql)
            result = cursor.fetchall()

            # 가장 최근 날짜 가져오기
            sql_recent_date = "SELECT MAX(DATEIN) AS end_date FROM total_storage"
            sql_yesterday_date = "SELECT DATE_SUB(MAX(DATEIN), INTERVAL 1 DAY) AS start_date FROM total_storage"
            cursor.execute(sql_recent_date)
            end_date_result = cursor.fetchone()
            end_date = end_date_result['end_date'] if end_date_result else None
            cursor.execute(sql_yesterday_date)
            start_date_result = cursor.fetchone()
            start_date = start_date_result['start_date'] if start_date_result else None

            if request.method == 'POST':
                start_date = request.form.get('start_date')
                end_date = request.form.get('end_date')

            # 데이터 조회
            if start_date and end_date:
                sql_data = """
                           SELECT STORAGE, PID, DATEIN, AV_CAP, TP_CAP, TL_CAP
                           FROM total_storage
                           WHERE DATEIN BETWEEN %s AND %s \
                           """
                cursor.execute(sql_data, (start_date, end_date))
                date_range_data = cursor.fetchall()

                # 스토리지별로 날짜별 데이터를 저장할 딕셔너리 초기화
                data_for_plot = {}

                for row in date_range_data:
                    date = row['DATEIN']
                    storage = row['STORAGE']

                    # 할당률 및 사용률 계산
                    tl_rate = row['TL_CAP'] * 100 / row['TP_CAP'] if row['TP_CAP'] > 0 else 0
                    use_rate = (row['TP_CAP'] - row['AV_CAP']) * 100 / row['TL_CAP'] if row['TL_CAP'] > 0 else 0

                    # 날짜별로 스토리지 데이터를 누적
                    if storage not in data_for_plot:
                        data_for_plot[storage] = {}

                    if date not in data_for_plot[storage]:
                        data_for_plot[storage][date] = {
                            'tl_rates': [],
                            'use_rates': []
                        }

                    data_for_plot[storage][date]['tl_rates'].append(tl_rate)
                    data_for_plot[storage][date]['use_rates'].append(use_rate)

                # 최종 데이터 구조화
                final_data_for_plot = {'dates': [], 'storages': [], 'tl_rates': [], 'use_rates': []}
                for storage, date_data in data_for_plot.items():
                    for date, rates in date_data.items():
                        avg_tl_rate = sum(rates['tl_rates']) / len(rates['tl_rates']) if rates['tl_rates'] else 0
                        avg_use_rate = sum(rates['use_rates']) / len(rates['use_rates']) if rates['use_rates'] else 0

                        final_data_for_plot['dates'].append(date)
                        final_data_for_plot['storages'].append(storage)
                        final_data_for_plot['tl_rates'].append(avg_tl_rate)
                        final_data_for_plot['use_rates'].append(avg_use_rate)

                # DataFrame 생성
                df = pd.DataFrame(final_data_for_plot)

                if not df.empty:
                    # 할당률 꺾은선 그래프 생성
                    fig_tl = px.line(df, x='dates', y='tl_rates', color='storages',
                                     labels={'tl_rates': '할당률 (%)', 'dates': '날짜'})

                    # 사용률 꺾은선 그래프 생성
                    fig_use = px.line(df, x='dates', y='use_rates', color='storages',
                                      labels={'use_rates': '사용률 (%)', 'dates': '날짜'})

                    # 그래프 HTML 코드로 변환
                    graph_html_tl = fig_tl.to_html(full_html=False)
                    graph_html_use = fig_use.to_html(full_html=False)

                if not date_range_data:
                    # 시작 날짜와 종료 날짜의 데이터 유무 검사
                    sql_check_data = "SELECT DATEIN FROM total_storage WHERE DATEIN IN (%s, %s)"
                    cursor.execute(sql_check_data, (start_date, end_date))
                    existing_dates = {row['DATEIN'] for row in cursor.fetchall()}

                    if str(end_date) not in [str(date) for date in existing_dates]:
                        error_message = '종료 날짜에 데이터가 없습니다.'
                else:
                    # 데이터 비교 로직
                    filtered_data = [row for row in date_range_data if
                                     row['DATEIN'].strftime('%Y-%m-%d') == str(end_date)]
                    for recent in filtered_data:
                        storage = recent['STORAGE']
                        pid = recent['PID']
                        if storage not in data1:
                            data1[storage] = {}

                        data1[storage][pid] = {
                            'AV_CAP': recent['AV_CAP'] / 1024 / 1024,  # TB로 변환
                            'TP_CAP': recent['TP_CAP'] / 1024 / 1024,
                            'TL_CAP': recent['TL_CAP'] / 1024 / 1024,
                            'AV_CAP_diff': None,  # 초기화
                            'TP_CAP_diff': None,
                            'TL_CAP_diff': None,
                            'TL_RATE': recent['TL_CAP'] * 100 / recent['TP_CAP'] if recent['TP_CAP'] > 0 else 0,
                            'USE_RATE': (recent['TP_CAP'] - recent['AV_CAP']) * 100 / recent['TL_CAP'] if recent[
                                                                                                              'TL_CAP'] > 0 else 0
                        }
                    filtered_data = [row for row in date_range_data if
                                     row['DATEIN'].strftime('%Y-%m-%d') == str(start_date)]
                    for yesterday in filtered_data:
                        storage = yesterday['STORAGE']
                        pid = yesterday['PID']
                        if storage in data1 and pid in data1[storage]:
                            # 차이 계산
                            diff = round(data1[storage][pid]['AV_CAP'] - (yesterday['AV_CAP'] / 1024 / 1024), 2)
                            data1[storage][pid]['AV_CAP_diff'] = f"({diff:+})"  # 차이를 포맷팅
                            diff = round(data1[storage][pid]['TP_CAP'] - (yesterday['TP_CAP'] / 1024 / 1024), 2)
                            data1[storage][pid]['TP_CAP_diff'] = f"({diff:+})"  # 차이를 포맷팅
                            diff = round(data1[storage][pid]['TL_CAP'] - (yesterday['TL_CAP'] / 1024 / 1024), 2)
                            data1[storage][pid]['TL_CAP_diff'] = f"({diff:+})"  # 차이를 포맷팅

            # MB를 TB로 변환하여 결과에 추가
            for row in date_range_data:
                row['AV_CAP'] = round(row['AV_CAP'] / 1024 / 1024, 2)  # TB 단위로 변환
                row['TP_CAP'] = round(row['TP_CAP'] / 1024 / 1024, 2)
                row['TL_CAP'] = round(row['TL_CAP'] / 1024 / 1024, 2)
                data2.append(row)

            # 스토리지 현황 개요 데이터 가져오기
            storage_overview = get_storage_overview(cursor)

            # 스토리지 목록 가져오기
            storage_list = get_storage_list(cursor)

    finally:
        connection.close()

    return render_template('storage.html',
                           data1=data1,
                           data2=data2,
                           latest_date=end_date,
                           start_date=start_date,
                           end_date=end_date,
                           error_message=error_message,
                           graph_html_tl=graph_html_tl,
                           graph_html_use=graph_html_use,
                           storage_overview=storage_overview,
                           incidents=[],
                           allocations=[],
                           storage_list=storage_list)


@storage_bp.route('/storage/load_data', methods=['POST'])
def load_data():
    """AJAX로 스토리지 데이터 로드"""
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 데이터 조회
                sql_data = """
                           SELECT STORAGE, PID, DATEIN, AV_CAP, TP_CAP, TL_CAP
                           FROM total_storage
                           WHERE DATEIN BETWEEN %s AND %s \
                           """
                cursor.execute(sql_data, (start_date, end_date))
                date_range_data = cursor.fetchall()

                if not date_range_data:
                    return jsonify({'success': False, 'message': '선택한 기간에 데이터가 없습니다.'})

                # 그래프 데이터 생성
                data_for_plot = {}
                for row in date_range_data:
                    date = row['DATEIN']
                    storage = row['STORAGE']
                    tl_rate = row['TL_CAP'] * 100 / row['TP_CAP'] if row['TP_CAP'] > 0 else 0
                    use_rate = (row['TP_CAP'] - row['AV_CAP']) * 100 / row['TL_CAP'] if row['TL_CAP'] > 0 else 0

                    if storage not in data_for_plot:
                        data_for_plot[storage] = {}
                    if date not in data_for_plot[storage]:
                        data_for_plot[storage][date] = {'tl_rates': [], 'use_rates': []}

                    data_for_plot[storage][date]['tl_rates'].append(tl_rate)
                    data_for_plot[storage][date]['use_rates'].append(use_rate)

                # 그래프 생성
                final_data_for_plot = {'dates': [], 'storages': [], 'tl_rates': [], 'use_rates': []}
                for storage, date_data in data_for_plot.items():
                    for date, rates in date_data.items():
                        avg_tl_rate = sum(rates['tl_rates']) / len(rates['tl_rates']) if rates['tl_rates'] else 0
                        avg_use_rate = sum(rates['use_rates']) / len(rates['use_rates']) if rates['use_rates'] else 0
                        final_data_for_plot['dates'].append(date)
                        final_data_for_plot['storages'].append(storage)
                        final_data_for_plot['tl_rates'].append(avg_tl_rate)
                        final_data_for_plot['use_rates'].append(avg_use_rate)

                df = pd.DataFrame(final_data_for_plot)
                graph_html_tl = None
                graph_html_use = None

                if not df.empty:
                    fig_tl = px.line(df, x='dates', y='tl_rates', color='storages',
                                     labels={'tl_rates': '할당률 (%)', 'dates': '날짜'})
                    fig_use = px.line(df, x='dates', y='use_rates', color='storages',
                                      labels={'use_rates': '사용률 (%)', 'dates': '날짜'})
                    graph_html_tl = fig_tl.to_html(full_html=False)
                    graph_html_use = fig_use.to_html(full_html=False)

                # 테이블 데이터 준비
                table_data = []
                for row in date_range_data:
                    table_data.append({
                        'DATEIN': row['DATEIN'].strftime('%Y-%m-%d'),
                        'STORAGE': row['STORAGE'],
                        'PID': row['PID'],
                        'AV_CAP': round(row['AV_CAP'] / 1024 / 1024, 2),
                        'TP_CAP': round(row['TP_CAP'] / 1024 / 1024, 2),
                        'TL_CAP': round(row['TL_CAP'] / 1024 / 1024, 2)
                    })

                # 현재 데이터 HTML 생성
                current_data_html = generate_current_data_html(date_range_data, end_date, start_date)

                return jsonify({
                    'success': True,
                    'graph_html_tl': graph_html_tl,
                    'graph_html_use': graph_html_use,
                    'table_data': table_data,
                    'current_data_html': current_data_html,
                    'latest_date': end_date
                })

        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def generate_current_data_html(date_range_data, end_date, start_date):
    """현재 데이터 HTML 생성"""
    data1 = {}

    # 최신 날짜 데이터 처리
    filtered_data = [row for row in date_range_data if row['DATEIN'].strftime('%Y-%m-%d') == str(end_date)]
    for recent in filtered_data:
        storage = recent['STORAGE']
        pid = recent['PID']
        if storage not in data1:
            data1[storage] = {}

        data1[storage][pid] = {
            'AV_CAP': recent['AV_CAP'] / 1024 / 1024,
            'TP_CAP': recent['TP_CAP'] / 1024 / 1024,
            'TL_CAP': recent['TL_CAP'] / 1024 / 1024,
            'AV_CAP_diff': None,
            'TP_CAP_diff': None,
            'TL_CAP_diff': None,
            'TL_RATE': recent['TL_CAP'] * 100 / recent['TP_CAP'] if recent['TP_CAP'] > 0 else 0,
            'USE_RATE': (recent['TP_CAP'] - recent['AV_CAP']) * 100 / recent['TL_CAP'] if recent['TL_CAP'] > 0 else 0
        }

    # 이전 날짜와 비교
    filtered_data = [row for row in date_range_data if row['DATEIN'].strftime('%Y-%m-%d') == str(start_date)]
    for yesterday in filtered_data:
        storage = yesterday['STORAGE']
        pid = yesterday['PID']
        if storage in data1 and pid in data1[storage]:
            diff = round(data1[storage][pid]['AV_CAP'] - (yesterday['AV_CAP'] / 1024 / 1024), 2)
            data1[storage][pid]['AV_CAP_diff'] = f"({diff:+})"
            diff = round(data1[storage][pid]['TP_CAP'] - (yesterday['TP_CAP'] / 1024 / 1024), 2)
            data1[storage][pid]['TP_CAP_diff'] = f"({diff:+})"
            diff = round(data1[storage][pid]['TL_CAP'] - (yesterday['TL_CAP'] / 1024 / 1024), 2)
            data1[storage][pid]['TL_CAP_diff'] = f"({diff:+})"

    # HTML 생성
    html = ""
    for storage, pids in data1.items():
        html += f"<h5>{storage}</h5>"
        html += '<div class="table-container">'
        html += '<table class="table table-striped table-bordered">'
        html += '<thead><tr><th>PID</th><th>가용량(TB)</th><th>총용량(TB)</th><th>할당량(TB)</th><th>할당률(%)</th><th>사용률(%)</th></tr></thead>'
        html += '<tbody>'
        for pid, data in pids.items():
            html += f'<tr><td>{pid}</td>'
            html += f'<td>{round(data["AV_CAP"], 2)} {"<span class=text-muted>%s</span>" % data["AV_CAP_diff"] if data["AV_CAP_diff"] else ""}</td>'
            html += f'<td>{round(data["AV_CAP"], 2)} {"<span class=text-muted>%s</span>" % data["TP_CAP_diff"] if data["TP_CAP_diff"] else ""}</td>'
            html += f'<td>{round(data["AV_CAP"], 2)} {"<span class=text-muted>%s</span>" % data["TL_CAP_diff"] if data["TL_CAP_diff"] else ""}</td>'
            html += f'<td>{round(data["TL_RATE"], 2)}%</td>'
            html += f'<td>{round(data["USE_RATE"], 2)}%</td></tr>'
        html += '</tbody></table></div>'

    return html


def get_storage_overview(cursor):
    """스토리지 현황 개요 데이터 조회"""
    sql = """
          SELECT si.id, \
                 si.storage_code, \
                 si.storage_name, \
                 si.status, \
                 si.location, \
                 si.memo, \
                 CONCAT(si.storage_code, '(', si.storage_name, ')') as display_name, \
                 COALESCE(SUM(ts.TP_CAP), 0) / 1024 / 1024          as total_capacity, \
                 COALESCE(SUM(ts.TL_CAP), 0) / 1024 / 1024          as allocated_capacity, \
                 COALESCE(SUM(ts.AV_CAP), 0) / 1024 / 1024          as available_capacity, \
                 CASE \
                     WHEN SUM(ts.TP_CAP) > 0 THEN (SUM(ts.TL_CAP) * 100.0 / SUM(ts.TP_CAP)) \
                     ELSE 0 \
                     END                                            as allocation_rate, \
                 CASE \
                     WHEN SUM(ts.TL_CAP) > 0 THEN ((SUM(ts.TP_CAP) - SUM(ts.AV_CAP)) * 100.0 / SUM(ts.TL_CAP)) \
                     ELSE 0 \
                     END                                            as usage_rate
          FROM storage_info si
                   LEFT JOIN total_storage ts ON si.storage_code = ts.STORAGE
              AND ts.DATEIN = (SELECT MAX(DATEIN) FROM total_storage WHERE STORAGE = si.storage_code)
          WHERE si.status IN ('사용', '유휴') AND (si.storage_name NOT LIKE '%보험코어%' AND si.storage_name NOT LIKE '%NAS%')
          GROUP BY si.id, si.storage_code, si.storage_name, si.status, si.location, si.memo
          ORDER BY si.storage_code DESC\
          """

    cursor.execute(sql)
    results = cursor.fetchall()

    for result in results:
        allocation_rate = result['allocation_rate']
        if allocation_rate < 50:
            result['capacity_level'] = 'low'
        elif allocation_rate < 70:
            result['capacity_level'] = 'medium'
        elif allocation_rate < 90:
            result['capacity_level'] = 'high'
        else:
            result['capacity_level'] = 'critical'

    return results


def get_storage_list(cursor):
    """스토리지 목록 조회"""
    sql = """
          SELECT id, \
                 storage_code, \
                 storage_name, \
                 CONCAT(storage_code, '(', storage_name, ')') as display_name
          FROM storage_info
          ORDER BY storage_code \
          """
    cursor.execute(sql)
    return cursor.fetchall()


@storage_bp.route('/storage/overview')
def get_overview():
    """스토리지 개요 데이터 API"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            overview = get_storage_overview(cursor)
            return jsonify(overview)
    finally:
        connection.close()


@storage_bp.route('/storage/incidents')
def get_incidents_api():
    """인시던트 데이터 API"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                  SELECT si_inc.id, \
                         si_inc.storage_id, \
                         si_inc.incident_date, \
                         si_inc.completion_date, \
                         si_inc.issue_description, \
                         si_inc.resolution_details, \
                         si_inc.status, \
                         CONCAT(si.storage_code, '(', si.storage_name, ')') as display_name
                  FROM storage_incident si_inc
                           JOIN storage_info si ON si_inc.storage_id = si.id \
                  """

            params = []
            if start_date and end_date:
                sql += " WHERE si_inc.incident_date BETWEEN %s AND %s"
                params = [start_date, end_date]

            sql += " ORDER BY si_inc.incident_date DESC"

            cursor.execute(sql, params)
            incidents = cursor.fetchall()

            # 날짜 형식 변환
            for incident in incidents:
                if incident['incident_date']:
                    incident['incident_date'] = incident['incident_date'].strftime('%Y-%m-%d')
                if incident['completion_date']:
                    incident['completion_date'] = incident['completion_date'].strftime('%Y-%m-%d')

            return jsonify(incidents)
    finally:
        connection.close()


@storage_bp.route('/storage/allocations')
def get_allocations_api():
    """할당/회수 데이터 API"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                  SELECT sa.id, \
                         sa.storage_id, \
                         sa.action_type, \
                         sa.action_date, \
                         sa.target_storage, \
                         sa.target_system, \
                         sa.capacity_change, \
                         sa.performed_by, \
                         sa.description, \
                         CONCAT(si.storage_code, '(', si.storage_name, ')') as display_name
                  FROM storage_allocation sa
                           JOIN storage_info si ON sa.storage_id = si.id \
                  """

            params = []
            if start_date and end_date:
                sql += " WHERE sa.action_date BETWEEN %s AND %s"
                params = [start_date, end_date]

            sql += " ORDER BY sa.action_date DESC"

            cursor.execute(sql, params)
            allocations = cursor.fetchall()

            # 날짜 형식 변환
            for allocation in allocations:
                if allocation['action_date']:
                    allocation['action_date'] = allocation['action_date'].strftime('%Y-%m-%d')

            return jsonify(allocations)
    finally:
        connection.close()


@storage_bp.route('/storage/update_storage_info', methods=['POST'])
def update_storage_info():
    """스토리지 정보 업데이트"""
    try:
        storage_id = request.form.get('id')
        storage_name = request.form.get('storage_name')
        status = request.form.get('status')
        location = request.form.get('location')
        memo = request.form.get('memo')

        sql = """
              UPDATE storage_info
              SET storage_name = %s, \
                  status       = %s, \
                  location     = %s, \
                  memo         = %s, \
                  updated_at   = NOW()
              WHERE id = %s \
              """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (storage_name, status, location, memo, storage_id))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/incident/add', methods=['POST'])
def add_incident():
    """인시던트 추가"""
    try:
        data = request.form
        sql = """
              INSERT INTO storage_incident
              (storage_id, incident_date, completion_date, issue_description, resolution_details, status)
              VALUES (%s, %s, %s, %s, %s, %s) \
              """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (
                    data.get('storage_id'),
                    data.get('incident_date'),
                    data.get('completion_date') if data.get('completion_date') else None,
                    data.get('issue_description'),
                    data.get('resolution_details'),
                    data.get('status')
                ))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/incident/<int:incident_id>')
def get_incident(incident_id):
    """인시던트 상세 조회"""
    try:
        sql = "SELECT * FROM storage_incident WHERE id = %s"
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (incident_id,))
                result = cursor.fetchone()
                if result:
                    if result['incident_date']:
                        result['incident_date'] = result['incident_date'].strftime('%Y-%m-%d')
                    if result['completion_date']:
                        result['completion_date'] = result['completion_date'].strftime('%Y-%m-%d')
                    return jsonify(result)
                else:
                    return jsonify({'error': 'Not found'}), 404
        finally:
            connection.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@storage_bp.route('/storage/incident/update', methods=['POST'])
def update_incident():
    """인시던트 수정"""
    try:
        data = request.form
        sql = """
              UPDATE storage_incident
              SET storage_id         = %s, \
                  incident_date      = %s, \
                  completion_date    = %s,
                  issue_description  = %s, \
                  resolution_details = %s, \
                  status             = %s, \
                  updated_at         = NOW()
              WHERE id = %s \
              """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (
                    data.get('storage_id'),
                    data.get('incident_date'),
                    data.get('completion_date') if data.get('completion_date') else None,
                    data.get('issue_description'),
                    data.get('resolution_details'),
                    data.get('status'),
                    data.get('id')
                ))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/incident/delete', methods=['POST'])
def delete_incident():
    """인시던트 삭제"""
    try:
        incident_id = request.form.get('id')
        sql = "DELETE FROM storage_incident WHERE id = %s"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (incident_id,))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/allocation/add', methods=['POST'])
def add_allocation():
    """할당/회수 추가"""
    try:
        data = request.form
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM storage_info LIMIT 1")
                storage_result = cursor.fetchone()
                storage_id = storage_result['id'] if storage_result else 1

                sql = """
                      INSERT INTO storage_allocation
                      (storage_id, action_type, action_date, target_storage, target_system, capacity_change, \
                       performed_by, description)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
                      """

                cursor.execute(sql, (
                    storage_id,
                    data.get('action_type'),
                    data.get('action_date'),
                    data.get('target_storage'),
                    data.get('target_system'),
                    data.get('capacity_change') if data.get('capacity_change') else None,
                    data.get('performed_by'),
                    data.get('description')
                ))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/allocation/<int:allocation_id>')
def get_allocation(allocation_id):
    """할당/회수 상세 조회"""
    try:
        sql = "SELECT * FROM storage_allocation WHERE id = %s"
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (allocation_id,))
                result = cursor.fetchone()
                if result:
                    if result['action_date']:
                        result['action_date'] = result['action_date'].strftime('%Y-%m-%d')
                    return jsonify(result)
                else:
                    return jsonify({'error': 'Not found'}), 404
        finally:
            connection.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@storage_bp.route('/storage/allocation/update', methods=['POST'])
def update_allocation():
    """할당/회수 수정"""
    try:
        data = request.form
        sql = """
              UPDATE storage_allocation
              SET action_type     = %s, \
                  action_date     = %s, \
                  target_storage  = %s, \
                  target_system   = %s,
                  capacity_change = %s, \
                  performed_by    = %s, \
                  description     = %s, \
                  updated_at      = NOW()
              WHERE id = %s \
              """

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (
                    data.get('action_type'),
                    data.get('action_date'),
                    data.get('target_storage'),
                    data.get('target_system'),
                    data.get('capacity_change') if data.get('capacity_change') else None,
                    data.get('performed_by'),
                    data.get('description'),
                    data.get('id')
                ))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/allocation/delete', methods=['POST'])
def delete_allocation():
    """할당/회수 삭제"""
    try:
        allocation_id = request.form.get('id')
        sql = "DELETE FROM storage_allocation WHERE id = %s"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (allocation_id,))
                connection.commit()
                return jsonify({'success': True})
        finally:
            connection.close()

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@storage_bp.route('/storage/export_incidents')
def export_incidents():
    """인시던트 데이터 엑셀 내보내기"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        sql = """
              SELECT CONCAT(si.storage_code, '(', si.storage_name, ')') as storage_name, \
                     si_inc.incident_date, \
                     si_inc.completion_date, \
                     si_inc.issue_description, \
                     si_inc.resolution_details, \
                     si_inc.status, \
                     si_inc.created_by
              FROM storage_incident si_inc
                       JOIN storage_info si ON si_inc.storage_id = si.id \
              """

        params = []
        if start_date and end_date:
            sql += " WHERE si_inc.incident_date BETWEEN %s AND %s"
            params = [start_date, end_date]

        sql += " ORDER BY si_inc.incident_date DESC"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                data = cursor.fetchall()
        finally:
            connection.close()

        if not data:
            flash('선택한 기간에 데이터가 없습니다.', 'error')
            return redirect(url_for('storage.storage'))

        df = pd.DataFrame(data)
        df.rename(columns={
            'storage_name': '스토리지',
            'incident_date': '발생일자',
            'completion_date': '완료일자',
            'issue_description': '이슈사항',
            'resolution_details': '처리내역',
            'status': '상태',
            'created_by': '등록자'
        }, inplace=True)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            temp_filename = tmp.name

        df.to_excel(temp_filename, index=False, sheet_name='인시던트 이력')
        export_filename = f'storage_incidents_{start_date or "all"}_to_{end_date or "all"}.xlsx'

        return send_file(
            temp_filename,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'엑셀 내보내기 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('storage.storage'))


@storage_bp.route('/storage/export_allocations')
def export_allocations():
    """할당/회수 데이터 엑셀 내보내기"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        sql = """
              SELECT sa.action_type, \
                     sa.action_date, \
                     sa.target_storage, \
                     sa.target_system, \
                     sa.capacity_change, \
                     sa.performed_by, \
                     sa.description, \
                     CONCAT(si.storage_code, '(', si.storage_name, ')') as storage_name
              FROM storage_allocation sa
                       JOIN storage_info si ON sa.storage_id = si.id \
              """

        params = []
        if start_date and end_date:
            sql += " WHERE sa.action_date BETWEEN %s AND %s"
            params = [start_date, end_date]

        sql += " ORDER BY sa.action_date DESC"

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                data = cursor.fetchall()
        finally:
            connection.close()

        if not data:
            flash('선택한 기간에 데이터가 없습니다.', 'error')
            return redirect(url_for('storage.storage'))

        df = pd.DataFrame(data)
        df.rename(columns={
            'action_type': '구분',
            'action_date': '수행일자',
            'target_storage': '대상스토리지',
            'target_system': '대상시스템',
            'capacity_change': '용량변화(TB)',
            'performed_by': '수행자',
            'description': '상세설명',
            'storage_name': '관련스토리지'
        }, inplace=True)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            temp_filename = tmp.name

        df.to_excel(temp_filename, index=False, sheet_name='할당회수 이력')
        export_filename = f'storage_allocations_{start_date or "all"}_to_{end_date or "all"}.xlsx'

        return send_file(
            temp_filename,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'엑셀 내보내기 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('storage.storage'))


@storage_bp.route('/storage/export_storage')
def export_storage():
    """스토리지 데이터 엑셀 내보내기"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        flash('시작 날짜와 종료 날짜를 모두 선택해주세요.', 'error')
        return redirect(url_for('storage.storage'))

    sql = """
          SELECT ts.DATEIN, \
                 COALESCE(CONCAT(si.storage_code, '(', si.storage_name, ')'), ts.STORAGE) as STORAGE, \
                 ts.PID, \
                 ts.AV_CAP, \
                 ts.TP_CAP, \
                 ts.TL_CAP, \
                 (ts.TL_CAP * 100 / ts.TP_CAP)                                            AS TL_RATE, \
                 ((ts.TP_CAP - ts.AV_CAP) * 100 / ts.TL_CAP)                              AS USE_RATE
          FROM total_storage ts
                   LEFT JOIN storage_info si ON ts.STORAGE = si.storage_code
          WHERE ts.DATEIN BETWEEN %s AND %s
          ORDER BY ts.DATEIN, ts.STORAGE, ts.PID \
          """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (start_date, end_date))
            data = cursor.fetchall()
    finally:
        connection.close()

    if not data:
        flash('선택한 기간에 데이터가 없습니다.', 'error')
        return redirect(url_for('storage.storage'))

    df = pd.DataFrame(data)
    df['AV_CAP'] = df['AV_CAP'] / 1024 / 1024
    df['TP_CAP'] = df['TP_CAP'] / 1024 / 1024
    df['TL_CAP'] = df['TL_CAP'] / 1024 / 1024

    df.rename(columns={
        'DATEIN': '날짜',
        'STORAGE': '스토리지',
        'PID': '풀ID',
        'AV_CAP': '가용량(TB)',
        'TP_CAP': '총용량(TB)',
        'TL_CAP': '할당량(TB)',
        'TL_RATE': '할당률(%)',
        'USE_RATE': '사용률(%)'
    }, inplace=True)

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        temp_filename = tmp.name

    df.to_excel(temp_filename, index=False, sheet_name='스토리지 용량 정보')
    export_filename = f'storage_capacity_{start_date}_to_{end_date}.xlsx'

    return send_file(
        temp_filename,
        as_attachment=True,
        download_name=export_filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@storage_bp.route('/storage_upload', methods=['POST'])
def storage_upload():
    """스토리지 데이터 업로드"""
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    content = file.read().decode('utf-8').splitlines()
    date = content[0].strip()
    storage_type = None

    for line in content[1:]:
        line = line.strip()
        if line.startswith("VSP") or line.startswith("F800") or line.startswith("DR_"):
            storage_type = line

            # 스토리지 정보 테이블에 자동 등록
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM storage_info WHERE storage_code = %s", (storage_type,))
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO storage_info (storage_code, storage_name, status) VALUES (%s, %s, %s)",
                            (storage_type, storage_type, '사용')
                        )
                        connection.commit()
            finally:
                connection.close()

        elif line.startswith("PID"):
            continue
        elif line and storage_type:
            data = line.split()
            if len(data) > 10:
                pid = data[0]
                av_cap = data[3]
                tp_cap = data[4]
                tl_cap = data[10]
                insert_data(date, storage_type, pid, av_cap, tp_cap, tl_cap)

    return redirect(url_for('storage.storage'))


def insert_data(date, storage_type, pid, av_cap, tp_cap, tl_cap):
    """스토리지 데이터 삽입"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO total_storage (DATEIN, STORAGE, PID, AV_CAP, TP_CAP, TL_CAP) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (date, storage_type, pid, av_cap, tp_cap, tl_cap))
        connection.commit()
    finally:
        connection.close()
