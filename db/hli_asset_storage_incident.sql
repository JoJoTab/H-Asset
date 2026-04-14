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
-- Table structure for table `storage_incident`
--

DROP TABLE IF EXISTS `storage_incident`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `storage_incident` (
  `id` int NOT NULL AUTO_INCREMENT,
  `storage_id` int NOT NULL,
  `incident_date` date NOT NULL,
  `completion_date` date DEFAULT NULL,
  `issue_description` text NOT NULL,
  `resolution_details` text,
  `status` enum('진행중','완료','보류') DEFAULT '진행중',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_by` varchar(100) DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `storage_id` (`storage_id`),
  CONSTRAINT `storage_incident_ibfk_1` FOREIGN KEY (`storage_id`) REFERENCES `storage_info` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `storage_incident`
--

LOCK TABLES `storage_incident` WRITE;
/*!40000 ALTER TABLE `storage_incident` DISABLE KEYS */;
INSERT INTO `storage_incident` VALUES (2,3,'2025-08-07','2025-08-07','Drive error (location : 08/09)','08/07 디스크 교체 완료','완료','2025-08-07 02:09:31','2025-08-08 00:04:48',NULL,NULL),(3,5,'2025-09-01','2025-09-01','DR 복제 중지','9/1 처리 완료','완료','2025-09-04 00:40:41','2025-09-04 00:40:41',NULL,NULL),(4,3,'2025-09-04','2025-09-05','Drive error (location : 08/0C)','9/5 디스트 교체 완료','완료','2025-09-05 00:53:04','2025-09-08 04:00:56',NULL,NULL),(5,8,'2025-10-19','2025-10-22','Drive error (location : HDD00-01)','10/22 18시 디스크 교체 완료','완료','2025-10-20 04:02:26','2025-10-23 04:31:23',NULL,NULL),(6,17,'2025-10-23','2025-10-27','Drive error (DB#/RDEV#=13/07)','10/27 디스크 교체 완료','완료','2025-10-24 05:30:44','2025-10-28 00:18:30',NULL,NULL),(7,19,'2025-10-31','2025-11-03','HNAS5200 용량 부족 문제 발생','HNAS5200 용량 증설 완료','완료','2025-11-03 23:27:52','2025-11-05 00:54:10',NULL,NULL),(8,3,'2025-11-18',NULL,'Drvie error (location: 05/12)','차민석 부장님 방문 예정','완료','2025-11-19 00:08:26','2025-12-17 00:22:41',NULL,NULL),(9,17,'2025-12-14',NULL,'Environmental microcontroller warning','12/15 18시 파트 교체 예정 (김석민 과장님 협의)','진행중','2025-12-15 05:19:27','2025-12-15 05:19:27',NULL,NULL),(10,2,'2026-02-22',NULL,'Drive media error (location : 06/02)','','진행중','2026-02-23 04:49:22','2026-02-23 04:49:22',NULL,NULL);
/*!40000 ALTER TABLE `storage_incident` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-07 15:34:43
