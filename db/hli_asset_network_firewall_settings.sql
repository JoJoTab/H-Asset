-- 방화벽 데이터 수집 설정 (단일 행)
CREATE TABLE IF NOT EXISTS hli_asset_network_firewall_settings (
    id                          INT          NOT NULL DEFAULT 1,
    polaris_base_url            VARCHAR(255) NOT NULL DEFAULT 'https://hsms.hanwhalife.com/rest',
    fw_monitor_type             VARCHAR(500) NOT NULL DEFAULT 'com.nkia.cygnus.plugins.server.domain.ScriptCustomMonitor-924fe3c4-9129-4916-8230-c9026ed09def',
    rate_limit_count            INT          NOT NULL DEFAULT 1  COMMENT 'N초당 N개 중 N개',
    rate_limit_seconds          INT          NOT NULL DEFAULT 1  COMMENT 'N초당 N개 중 N초',
    auto_collect_enabled        TINYINT(1)   NOT NULL DEFAULT 0,
    auto_collect_interval_hours INT          NOT NULL DEFAULT 6,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='방화벽 수집 설정';

INSERT IGNORE INTO hli_asset_network_firewall_settings (id) VALUES (1);
