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
-- Table structure for table `total_asset`
--

DROP TABLE IF EXISTS `total_asset`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `total_asset` (
  `pnum` int NOT NULL AUTO_INCREMENT,
  `itamnum` varchar(45) DEFAULT NULL,
  `servername` longtext,
  `ip` varchar(100) DEFAULT NULL,
  `hostname` varchar(100) DEFAULT NULL,
  `center` varchar(45) DEFAULT NULL,
  `loc1` varchar(45) DEFAULT NULL,
  `loc2` int DEFAULT NULL,
  `group` int DEFAULT NULL,
  `vcenter` int DEFAULT NULL,
  `datein` date DEFAULT NULL,
  `dateout` date DEFAULT NULL,
  `charge` varchar(45) DEFAULT NULL,
  `charge2` varchar(45) DEFAULT NULL,
  `isoper` int DEFAULT NULL,
  `oper` int DEFAULT NULL,
  `power` int DEFAULT NULL,
  `pdu` varchar(45) DEFAULT NULL,
  `os` int DEFAULT NULL,
  `osver` varchar(60) DEFAULT NULL,
  `maker` varchar(45) DEFAULT NULL,
  `model` varchar(45) DEFAULT NULL,
  `serial` varchar(45) DEFAULT NULL,
  `domain` int DEFAULT '1',
  `charge3` varchar(45) DEFAULT NULL,
  `usize` int DEFAULT '1',
  `vmpnum` int DEFAULT NULL,
  `dateinsert` datetime DEFAULT CURRENT_TIMESTAMP,
  `cpucore` int DEFAULT NULL,
  `memory` int DEFAULT NULL,
  `dateupdate` datetime DEFAULT NULL,
  `isfix` int DEFAULT '1',
  `eos` date DEFAULT NULL,
  `eosl` date DEFAULT NULL,
  PRIMARY KEY (`pnum`)
) ENGINE=InnoDB AUTO_INCREMENT=3337 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
