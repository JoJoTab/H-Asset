-- ============================================================
-- asset_ip : 자산 IP 테이블
-- 자산 1개에 복수 IP 를 저장 (asset_info 와 1:N 관계)
-- ============================================================

DROP TABLE IF EXISTS `asset_ip`;
CREATE TABLE `asset_ip` (
  `id`          INT          NOT NULL AUTO_INCREMENT COMMENT 'PK',
  `asset_pnum`  INT          NOT NULL COMMENT '자산번호 (asset_info.pnum FK)',
  `ip`          VARCHAR(50)  NOT NULL COMMENT 'IP 주소',
  `ip_type`     VARCHAR(20)  DEFAULT '내부'
      COMMENT 'IP 유형: 내부 / 외부 / 관리 / 기타',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '비고',

  PRIMARY KEY (`id`),
  KEY `idx_asset_pnum` (`asset_pnum`),
  CONSTRAINT `fk_asset_ip_pnum`
      FOREIGN KEY (`asset_pnum`) REFERENCES `asset_info` (`pnum`)
      ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='자산 IP 테이블';


-- ============================================================
-- 데이터 이전: total_asset.ip (단일) → asset_ip (복수 지원)
-- IP 가 콤마로 구분된 경우는 별도 처리 필요
-- ============================================================
/*
INSERT INTO asset_ip (asset_pnum, ip, ip_type)
SELECT pnum, TRIM(ip), '내부'
FROM total_asset
WHERE ip IS NOT NULL AND ip != '';
*/
