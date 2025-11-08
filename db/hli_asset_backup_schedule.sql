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
-- Table structure for table `backup_schedule`
--

DROP TABLE IF EXISTS `backup_schedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `backup_schedule` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unique_id` varchar(50) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL,
  `business_name` varchar(200) DEFAULT NULL,
  `hostname` varchar(100) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `introduction_year` int DEFAULT NULL,
  `vendor` varchar(100) DEFAULT NULL,
  `model_name` varchar(200) DEFAULT NULL,
  `os` varchar(100) DEFAULT NULL,
  `os_version` varchar(200) DEFAULT NULL,
  `installation_location` varchar(200) DEFAULT NULL,
  `redundancy_config` varchar(10) DEFAULT NULL,
  `backup_method` varchar(100) DEFAULT NULL,
  `retention_period` varchar(50) DEFAULT NULL,
  `offsite_cycle` varchar(100) DEFAULT NULL,
  `offsite_location` varchar(200) DEFAULT NULL,
  `offsite_equipment` varchar(100) DEFAULT NULL,
  `offsite_retention` varchar(50) DEFAULT NULL,
  `backup_target` text,
  `storage_media` varchar(200) DEFAULT NULL,
  `backup_policy` varchar(200) DEFAULT NULL,
  `backup_schedule` varchar(200) DEFAULT NULL,
  `dbms` varchar(100) DEFAULT NULL,
  `target_filesystem` text,
  `memo` text,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_id` (`unique_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1293 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-15 18:20:24
