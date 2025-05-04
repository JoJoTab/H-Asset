from flask import url_for
from utils.db import execute_query


def get_asset_hierarchy(pnum=None, domain=None, group=None):
    """
    자산의 계층 구조를 가져오는 함수

    Args:
        pnum: 자산 번호 (특정 자산의 계층 구조를 가져올 때 사용)
        domain: 도메인 ID (특정 도메인의 계층 구조를 가져올 때 사용)
        group: 그룹 ID (특정 그룹의 계층 구조를 가져올 때 사용)

    Returns:
        계층 구조 리스트 (각 항목은 name, url, active 속성을 가짐)
    """
    hierarchy = []

    # 1계층: Infra
    hierarchy.append({
        'name': 'Infra',
        'url': url_for('asset.index_detail'),
        'active': domain is None and group is None and pnum is None
    })

    # 특정 자산이 지정된 경우 해당 자산의 정보 가져오기
    asset_info = None
    if pnum is not None:
        sql = """
            SELECT ta.*, id.state AS domain_state, ig.state AS group_state
            FROM total_asset ta
            LEFT JOIN info_domain id ON ta.domain = id.domain
            LEFT JOIN info_group ig ON ta.`group` = ig.`group` AND ta.domain = ig.domain
            WHERE ta.pnum = %s
        """
        asset_info = execute_query(sql, (pnum,), fetch_all=False)
        if asset_info:
            domain = asset_info['domain']
            group = asset_info['group']

    # 2계층: 도메인
    if domain is not None:
        domain_sql = "SELECT * FROM info_domain WHERE domain = %s"
        domain_info = execute_query(domain_sql, (domain,), fetch_all=False)
        if domain_info:
            hierarchy.append({
                'name': domain_info['state'],
                'url': url_for('asset.index_detail', domain=domain),
                'active': group is None and pnum is None
            })

    # 3계층: 그룹
    if domain is not None and group is not None:
        group_sql = "SELECT * FROM info_group WHERE domain = %s AND `group` = %s"
        group_info = execute_query(group_sql, (domain, group), fetch_all=False)
        if group_info:
            hierarchy.append({
                'name': group_info['state'],
                'url': url_for('asset.index_detail', domain=domain, group=group),
                'active': pnum is None
            })

    # 4계층: 호스트명 (특정 자산인 경우)
    if pnum is not None and asset_info:
        hierarchy.append({
            'name': asset_info['hostname'] or asset_info['servername'],
            'url': url_for('asset.edit_asset', pnum=pnum),
            'active': True
        })

    return hierarchy
