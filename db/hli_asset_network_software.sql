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
-- Table structure for table `network_software`
--

DROP TABLE IF EXISTS `network_software`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `network_software` (
  `software_id` int NOT NULL,
  `type` varchar(45) DEFAULT NULL,
  `name` varchar(100) DEFAULT NULL,
  `manufacturer` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`software_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `network_software`
--

LOCK TABLES `network_software` WRITE;
/*!40000 ALTER TABLE `network_software` DISABLE KEYS */;
INSERT INTO `network_software` VALUES (1,'firmware','JunOS','Juniper',NULL,NULL),(2,'firmware','AOS','AXGATE',NULL,NULL),(3,'firmware','GNOS','Genians',NULL,NULL),(4,'liscense','GPC5-20000','Genians',NULL,NULL),(5,'liscense','NetFUNNEL Enterprise','유니포인트',NULL,NULL),(6,'firmware','FutureSystemOS','FutureSystem',NULL,NULL),(7,'firmware','SECUI','SECUI',NULL,NULL),(8,'firmware','IOS','Cisco',NULL,NULL),(9,'firmware','CATALYST CENTER','Cisco',NULL,NULL),(10,'liscense','Secu-U U5000','Taesan',NULL,NULL),(11,'liscense','Secu-U U700','Taesan',NULL,NULL),(12,'firmware','NetScaler ADC','Citrix',NULL,NULL),(13,'firmware','Ahnlab OS','Ahnlab',NULL,NULL),(14,'firmware','VOS','NexG',NULL,NULL),(15,'firmware','PLOS','Piolink',NULL,NULL),(16,'liscense','CeMS V3.0',NULL,NULL,NULL),(17,'liscense','EX4600-AFL','Juniper',NULL,NULL),(18,'firmware','NXOS','Cisco',NULL,NULL),(19,'firmware','Infoblox','Infoblox',NULL,NULL),(20,'software','MultiView','새하컴즈',NULL,NULL),(21,'liscense','WDS-LS010/KOR','Samsung',NULL,NULL),(22,'liscense','WDS-LM100/KOR','Samsung',NULL,NULL),(23,'liscense','WDS-LM50/KOR','Samsung',NULL,NULL),(24,'firmware','alteon','Radware',NULL,NULL),(25,'software','Oracle Linux','Oracle',NULL,NULL),(26,'software','nGeniusONE','NetScout',NULL,NULL),(27,'software','InfinistreamNG','NetScout',NULL,NULL),(28,'software','PFOS','NetScout',NULL,NULL),(29,'firmware','ByfrontOS','Aircuve',NULL,NULL);
/*!40000 ALTER TABLE `network_software` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-07 15:34:44
