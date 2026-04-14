-- ============================================================
-- asset_info : 자산정보 테이블 (total_asset 대체)
-- info_domain / info_group / info_isoper / info_oper 제거 후
-- 모든 코드 값을 VARCHAR ENUM 으로 직접 저장
-- ============================================================

DROP TABLE IF EXISTS `asset_info`;
CREATE TABLE `asset_info` (
  `pnum`         INT          NOT NULL AUTO_INCREMENT COMMENT '자산번호 (PK)',

  -- ── 식별 ──────────────────────────────────────────────────
  `hostname`     VARCHAR(100)  DEFAULT NULL COMMENT '호스트명',
  `servername`   VARCHAR(200)  DEFAULT NULL COMMENT '서비스명',

  -- ── 분류 ──────────────────────────────────────────────────
  `grp`          VARCHAR(50)   DEFAULT NULL
      COMMENT '그룹: 서버>x86 / 서버>Unix / 서버>Public Cloud / 서버>기타
               / 스토리지>스토리지 장비 / 스토리지>SAN 스위치 / 스토리지>기타 스토리지
               / 백업장비>백업장비 / 백업장비>PTL / 백업장비>기타 백업장비',
  `oper`         VARCHAR(20)   DEFAULT NULL COMMENT '구분: DEV / PROD / QA / DR',
  `center`       VARCHAR(50)   DEFAULT NULL COMMENT '위치: IDC / 63DR',
  `network_zone` VARCHAR(20)   DEFAULT NULL COMMENT '망: 내부 / 외부',
  `asset_type`   VARCHAR(10)   DEFAULT NULL COMMENT '물리/논리',
  `purpose`      VARCHAR(500)  DEFAULT NULL COMMENT '용도 (콤마 구분): WEB,WAS,DB,VDI,콘솔,FS,SW',

  -- ── 물리 위치 ─────────────────────────────────────────────
  `loc1`         VARCHAR(100)  DEFAULT NULL COMMENT '물리서버 상면위치',
  `loc2`         INT           DEFAULT NULL COMMENT '물리서버 상단번호',
  `usize`        INT           DEFAULT 1    COMMENT '상면크기(U)',

  -- ── 하드웨어 ──────────────────────────────────────────────
  `maker`        VARCHAR(100)  DEFAULT NULL COMMENT '제조사',
  `model`        VARCHAR(100)  DEFAULT NULL COMMENT '모델명',
  `serial`       VARCHAR(100)  DEFAULT NULL COMMENT '시리얼번호',

  -- ── OS ────────────────────────────────────────────────────
  `os`           VARCHAR(50)   DEFAULT NULL COMMENT 'OS: LINUX / WINDOWS / AIX / HPUX / 기타',
  `osver`        VARCHAR(100)  DEFAULT NULL COMMENT 'OS 버전',

  -- ── 사양 ──────────────────────────────────────────────────
  `cpucore`      INT           DEFAULT NULL COMMENT 'CPU Core 수',
  `cpusocket`    INT           DEFAULT NULL COMMENT 'CPU 소켓 수',
  `memory`       FLOAT         DEFAULT NULL COMMENT 'MEM (GB)',

  -- ── 일자 ──────────────────────────────────────────────────
  `datein`       DATE          DEFAULT NULL COMMENT '도입일자',
  `dateout`      DATE          DEFAULT NULL COMMENT '폐기일자',
  `hw_eos`       DATE          DEFAULT NULL COMMENT 'HW EOS 일자',
  `hw_eosl`      DATE          DEFAULT NULL COMMENT 'HW EOSL 일자',

  -- ── 운영 ──────────────────────────────────────────────────
  `status`       VARCHAR(20)   DEFAULT '사용'
      COMMENT '자산상태: 사용 / 유휴 / 폐기',
  `importance`   VARCHAR(10)   DEFAULT '일반'
      COMMENT '중요도: 일반 / 핵심',

  -- ── 전원 ──────────────────────────────────────────────────
  `power`        VARCHAR(30)   DEFAULT NULL
      COMMENT '전원이중화: 이중화(AB) / 단일(A) / 단일(B) / 단일(S)',
  `watt`         FLOAT         DEFAULT NULL COMMENT '소비전력량 (W)',
  `ampere`       FLOAT         DEFAULT NULL COMMENT '사용전류 (A)',

  -- ── 담당자 ────────────────────────────────────────────────
  `charge`       VARCHAR(100)  DEFAULT NULL COMMENT '담당자(정)',
  `charge2`      VARCHAR(100)  DEFAULT NULL COMMENT '담당자(부)',
  `charge3`      VARCHAR(100)  DEFAULT NULL COMMENT '서비스담당자',

  -- ── 기타 ──────────────────────────────────────────────────
  `memo`         TEXT          DEFAULT NULL COMMENT '메모',
  `dateupdate`   DATETIME      DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '업데이트일자',
  `dateinsert`   DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '생성일자',

  PRIMARY KEY (`pnum`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='자산정보 테이블';


-- ============================================================
-- 데이터 이전: total_asset → asset_info
-- (스키마 변경 후 1회 실행)
-- ============================================================
/*
INSERT INTO asset_info (
  pnum, hostname, servername,
  grp,
  oper,
  center, asset_type, loc1, loc2, usize,
  maker, model, serial,
  os, osver,
  cpucore, cpusocket, memory,
  datein, dateout,
  status,
  power,
  charge, charge2, charge3,
  memo, dateupdate, dateinsert
)
SELECT
  ta.pnum,
  ta.hostname,
  ta.servername,
  -- grp: domain_state + group_state 조합
  CONCAT(COALESCE(id.state,''), '>', COALESCE(ig.state,'')) AS grp,
  -- oper
  io_oper.state  AS oper,
  ta.center,
  CASE ta.isvm WHEN 0 THEN '물리' ELSE '논리' END AS asset_type,
  ta.loc1, ta.loc2, COALESCE(ta.usize,1),
  ta.maker, ta.model, ta.serial,
  io_os.state AS os,
  ta.osver,
  ta.cpucore, ta.cpusocket, ta.memory,
  ta.datein, ta.dateout,
  io_isoper.state AS status,
  io_power.state  AS power,
  ta.charge, ta.charge2, ta.charge3,
  ta.memo, ta.dateupdate, ta.dateinsert
FROM total_asset ta
LEFT JOIN info_domain  id        ON ta.domain = id.domain
LEFT JOIN info_group   ig        ON ta.`group` = ig.`group` AND ta.domain = ig.domain
LEFT JOIN info_oper    io_oper   ON ta.oper    = io_oper.oper
LEFT JOIN info_isoper  io_isoper ON ta.isoper  = io_isoper.isoper
LEFT JOIN info_os      io_os     ON ta.os      = io_os.os
LEFT JOIN info_power   io_power  ON ta.power   = io_power.power;
*/
