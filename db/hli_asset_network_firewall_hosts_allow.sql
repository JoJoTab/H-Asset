-- /etc/hosts.allow 내용 저장
-- 외래키 미사용: 서버 테이블과 독립적으로 동작
CREATE TABLE IF NOT EXISTS hli_asset_network_firewall_hosts_allow (
    id           INT      NOT NULL AUTO_INCREMENT,
    resource_id  INT      NOT NULL  COMMENT 'firewall_server.resource_id 참조 (논리적)',
    hosts_allow  TEXT     DEFAULT NULL COMMENT '/etc/hosts.allow 파일 내용',
    collected_at DATETIME DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_resource_id (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OS방화벽 hosts.allow 설정';
