-- ============================================================
-- asset_link : 자산연계 테이블
-- 다른 시스템에서 관리하는 자산 번호를 key-value 형태로 저장
-- system_type 을 추가하면 새 시스템 연계를 DDL 변경 없이 확장 가능
-- ============================================================

DROP TABLE IF EXISTS `asset_link`;
CREATE TABLE `asset_link` (
  `id`          INT          NOT NULL AUTO_INCREMENT COMMENT 'PK',
  `asset_pnum`  INT          NOT NULL COMMENT '자산번호 (asset_info.pnum FK)',
  `system_type` VARCHAR(50)  NOT NULL
      COMMENT '연계 시스템 유형: ITSM / ITMS / HiON / 기타',
  `system_id`   VARCHAR(200) NOT NULL COMMENT '해당 시스템의 자산 ID',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '비고',

  PRIMARY KEY (`id`),
  KEY `idx_asset_link_pnum` (`asset_pnum`),
  KEY `idx_asset_link_type` (`system_type`),
  CONSTRAINT `fk_asset_link_pnum`
      FOREIGN KEY (`asset_pnum`) REFERENCES `asset_info` (`pnum`)
      ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='자산연계 테이블 (외부 시스템 자산번호)';


-- ============================================================
-- 데이터 이전: total_asset.itamnum → asset_link (system_type='ITSM')
-- ============================================================
/*
INSERT INTO asset_link (asset_pnum, system_type, system_id)
SELECT pnum, 'ITSM', itamnum
FROM total_asset
WHERE itamnum IS NOT NULL AND itamnum != '';
*/
