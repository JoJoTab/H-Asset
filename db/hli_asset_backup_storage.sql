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
-- Table structure for table `backup_storage`
--

DROP TABLE IF EXISTS `backup_storage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `backup_storage` (
  `id` int NOT NULL AUTO_INCREMENT,
  `storage_name` varchar(100) NOT NULL,
  `total_capacity_tb` float NOT NULL DEFAULT '0',
  `location` varchar(200) DEFAULT NULL,
  `storage_type` varchar(50) DEFAULT 'Disk',
  `storage_source` varchar(100) DEFAULT '직접입력',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_storage_name` (`storage_name`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `backup_storage`
--

LOCK TABLES `backup_storage` WRITE;
/*!40000 ALTER TABLE `backup_storage` DISABLE KEYS */;
INSERT INTO `backup_storage` VALUES (4,'NBU APPLIANCE #1 (5250)',129.5,'IDC','Disk','직접입력','2025-10-13 09:56:55','2025-10-13 10:04:57'),(5,'NBU APPLIANCE #2 (5250)',129.5,'IDC','Disk','직접입력','2025-10-13 09:57:42','2025-10-13 10:04:57'),(6,'NBU APPLIANCE #3 (5250)',184,'IDC','Disk','직접입력','2025-10-13 09:58:18','2025-10-13 09:58:18'),(7,'NBU APPLIANCE #4 (5250)',121.9,'IDC','Disk','직접입력','2025-10-13 09:58:39','2025-10-13 10:04:57'),(8,'NBU APPLIANCE #5 (5250)',313.6,'IDC','Disk','직접입력','2025-10-13 09:59:02','2025-10-13 10:04:57'),(9,'NBU APPLIANCE #IFRS (5240)',136.4,'IDC','Disk','직접입력','2025-10-13 09:59:29','2025-10-13 10:04:57'),(10,'NBU APPLIANCE 대용량 (5260)',675,'IDC','Disk','직접입력','2025-10-13 10:00:05','2025-10-13 10:00:05'),(11,'ZConverter #1',70,'IDC','Disk','직접입력','2025-10-13 10:00:26','2025-10-13 10:00:26'),(12,'ZConverter #2',109,'IDC','Disk','직접입력','2025-10-13 10:00:46','2025-10-13 10:00:46'),(13,'ZConverter #3',181,'IDC','Disk','직접입력','2025-10-13 10:01:04','2025-10-13 10:01:04');
/*!40000 ALTER TABLE `backup_storage` ENABLE KEYS */;
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
