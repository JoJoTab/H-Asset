-- ============================================================
-- asset_relation : 자산관계 테이블
-- 자산 간 상위/하위/DR/이중화 관계를 저장
-- parent_pnum → child_pnum 방향으로 관계 정의
--   예) 물리서버(parent) -- VM(child) : relation_type='VM'
--       IDC서버(parent)  -- DR서버(child) : relation_type='DR'
-- ============================================================

DROP TABLE IF EXISTS `asset_relation`;
CREATE TABLE `asset_relation` (
  `id`            INT         NOT NULL AUTO_INCREMENT COMMENT 'PK',
  `parent_pnum`   INT         NOT NULL COMMENT '상위 자산번호 (asset_info.pnum FK)',
  `child_pnum`    INT         NOT NULL COMMENT '하위 자산번호 (asset_info.pnum FK)',
  `relation_type` VARCHAR(50) NOT NULL
      COMMENT '관계 유형: VM / DR / 이중화(A-A) / 이중화(A-S) / 기타',
  `description`   VARCHAR(200) DEFAULT NULL COMMENT '관계 설명',

  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_relation` (`parent_pnum`, `child_pnum`, `relation_type`),
  KEY `idx_relation_parent` (`parent_pnum`),
  KEY `idx_relation_child`  (`child_pnum`),
  CONSTRAINT `fk_relation_parent`
      FOREIGN KEY (`parent_pnum`) REFERENCES `asset_info` (`pnum`)
      ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_relation_child`
      FOREIGN KEY (`child_pnum`) REFERENCES `asset_info` (`pnum`)
      ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='자산관계 테이블 (상위/하위/DR/이중화)';


-- ============================================================
-- 데이터 이전: total_asset.vcenter (상위 서버 pnum) → asset_relation
-- vcenter 컬럼이 상위 물리서버의 pnum 을 가리키는 경우
-- ============================================================
/*
INSERT INTO asset_relation (parent_pnum, child_pnum, relation_type)
SELECT vcenter, pnum, 'VM'
FROM total_asset
WHERE vcenter IS NOT NULL AND isvm = 1;
*/
