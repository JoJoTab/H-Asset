-- OS 방화벽 모니터링 서버 목록
CREATE TABLE IF NOT EXISTS hli_asset_network_firewall_server (
    resource_id      INT          NOT NULL  COMMENT '폴스타 리소스 ID',
    name             VARCHAR(100) NOT NULL  COMMENT '서버명 (hostname)',
    ip_address       VARCHAR(50)  DEFAULT NULL COMMENT 'IP 주소',
    monitor_group_id INT          DEFAULT NULL COMMENT '모니터 그룹 ID',
    fw_monitor_id    INT          DEFAULT NULL COMMENT 'OS방화벽 서브모니터 ID',
    availability     VARCHAR(20)  DEFAULT NULL COMMENT '가용성 (UP / DOWN)',
    error_msg        TEXT         DEFAULT NULL COMMENT '오류 내용',
    last_collected   DATETIME     DEFAULT NULL COMMENT '마지막 수집일시',
    PRIMARY KEY (resource_id),
    INDEX idx_ip (ip_address),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OS방화벽 모니터링 서버';
