-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: hli_asset
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `info_software_type`
--

DROP TABLE IF EXISTS `info_software_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `info_software_type` (
  `type_idx` int NOT NULL AUTO_INCREMENT COMMENT '소프트웨어 종류 인덱스',
  `type_name` varchar(50) NOT NULL COMMENT '소프트웨어 종류명',
  `type_description` text COMMENT '소프트웨어 종류 설명',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (`type_idx`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='소프트웨어 종류 정보';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `info_software_type`
--

LOCK TABLES `info_software_type` WRITE;
/*!40000 ALTER TABLE `info_software_type` DISABLE KEYS */;
INSERT INTO `info_software_type` VALUES (1,'펌웨어','하드웨어 제어를 위한 펌웨어','2025-07-30 22:40:12','2025-07-30 22:40:12'),(2,'OS','운영체제','2025-07-30 22:40:12','2025-07-30 22:40:12'),(3,'DBMS','데이터베이스 관리 시스템','2025-07-30 22:40:12','2025-07-30 22:40:12'),(4,'미들웨어','미들웨어 소프트웨어','2025-07-30 22:40:12','2025-07-30 22:40:12'),(5,'AP','애플리케이션 소프트웨어','2025-07-30 22:40:12','2025-07-30 22:40:12'),(6,'보안','보안 관련 소프트웨어','2025-07-30 22:40:12','2025-07-30 22:40:12'),(7,'기타','기타 소프트웨어','2025-07-30 22:40:12','2025-07-30 22:40:12');
/*!40000 ALTER TABLE `info_software_type` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-07 15:34:46
