-- OS 방화벽 Zone 설정 (firewalld zone 별 허용 규칙)
-- 외래키 미사용: 서버 테이블과 독립적으로 동작
CREATE TABLE IF NOT EXISTS hli_asset_network_firewall_zone (
    id           INT          NOT NULL AUTO_INCREMENT,
    resource_id  INT          NOT NULL  COMMENT 'firewall_server.resource_id 참조 (논리적)',
    zone_name    VARCHAR(100) DEFAULT NULL COMMENT 'Zone 이름 (예: 01_SMS)',
    sources      TEXT         DEFAULT NULL COMMENT '허용 출발지 IP/CIDR 목록 (공백 구분)',
    ports        TEXT         DEFAULT NULL COMMENT '허용 포트 목록 (예: 80/tcp 443/tcp)',
    services     TEXT         DEFAULT NULL COMMENT '허용 서비스 이름 목록',
    interfaces   TEXT         DEFAULT NULL COMMENT '인터페이스 목록',
    rich_rules   TEXT         DEFAULT NULL COMMENT 'Rich Rules (개행 구분)',
    raw_value    TEXT         DEFAULT NULL COMMENT '폴스타 수집 원본값',
    collected_at DATETIME     DEFAULT NULL COMMENT '수집일시',
    PRIMARY KEY (id),
    INDEX idx_resource_id (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OS방화벽 Zone 설정';
