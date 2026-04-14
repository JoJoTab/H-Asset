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
-- Table structure for table `vmware_exceptions`
--

DROP TABLE IF EXISTS `vmware_exceptions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vmware_exceptions` (
  `exception_id` int NOT NULL AUTO_INCREMENT COMMENT '예외 ID',
  `vm_name` varchar(255) NOT NULL COMMENT 'VM 이름',
  `ip` varchar(50) NOT NULL COMMENT 'IP 주소',
  `reason` varchar(500) DEFAULT NULL COMMENT '예외 사유',
  `created_at` datetime DEFAULT NULL COMMENT '예외 등록 날짜',
  `created_by` varchar(100) DEFAULT NULL COMMENT '등록자',
  PRIMARY KEY (`exception_id`),
  UNIQUE KEY `unique_vm_ip` (`vm_name`,`ip`),
  KEY `idx_vm_name` (`vm_name`),
  KEY `idx_ip` (`ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='VMware 변경 이력 예외 목록';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vmware_exceptions`
--

LOCK TABLES `vmware_exceptions` WRITE;
/*!40000 ALTER TABLE `vmware_exceptions` DISABLE KEYS */;
/*!40000 ALTER TABLE `vmware_exceptions` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-07 15:34:45
