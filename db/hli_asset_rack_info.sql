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
-- Table structure for table `rack_info`
--

DROP TABLE IF EXISTS `rack_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rack_info` (
  `rnum` int NOT NULL AUTO_INCREMENT,
  `rackname` varchar(45) DEFAULT NULL,
  `rackenable` int DEFAULT NULL,
  `loc` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`rnum`)
) ENGINE=InnoDB AUTO_INCREMENT=172 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rack_info`
--

LOCK TABLES `rack_info` WRITE;
/*!40000 ALTER TABLE `rack_info` DISABLE KEYS */;
INSERT INTO `rack_info` VALUES (105,'Hitach HCI',1,'5F-20-R03'),(106,'그룹웨어 #2',1,'5F-15-R05'),(107,'그룹웨어 #1',1,'5F-15-R04'),(108,'DELL변액헷지#3',1,'5F-15-R03'),(109,'IBM S924',1,'5F-15-R02'),(110,'주전산슈퍼돔#2',1,'5F-12-R07'),(111,'(보안)망연계',1,'5F-12-R02'),(112,'주전산슈퍼돔#1',1,'5F-12-R06'),(113,'SWIFT,이미지',1,'5F-31-R04'),(114,'통합기#3(12호기)',1,'5F-31-R05'),(115,'통합기#4(13호기)',1,'5F-31-R06'),(116,'DELL변액헷지#2',1,'5F-15-R11'),(117,'DELL변액헷지#1',1,'5F-15-R12'),(118,'정보계VSP5500',1,'5F-12-R01'),(119,'G1500#2',1,'5F-12-R03'),(120,'주전산슈퍼돔OS',1,'5F-12-R04'),(121,'G1500#1',1,'5F-12-R05'),(122,'주전산G1000',1,'5F-12-R09'),(123,'디지털대면NAS',1,'5F-12-R11'),(124,'통합SAN x6-4',1,'5F-12-R12'),(125,'보안 문서중앙화',1,'5F-12-R14'),(126,'VDI NAS',1,'5F-12-R15'),(127,'그룹웨어 #VMI',1,'5F-15-R06'),(128,'F1500',1,'5F-15-R09'),(129,'IFRS17,TSQL#1',1,'5F-15-R13'),(130,'IFRS17,TSQL#2',1,'5F-15-R14'),(131,'F800',1,'5F-15-R15'),(132,'이미지스토리지',1,'5F-20-R02'),(133,'정보계SAN',1,'5F-20-R04'),(134,'정보계 스토리지',1,'5F-20-R05'),(135,'IFRS EXA(X7-2)',1,'5F-20-R06'),(136,'정보계#1(P870)',1,'5F-20-R07'),(137,'변액헷지#4',1,'5F-20-R09'),(138,'한금서 업무VDI',1,'5F-20-R10'),(139,'VDI 스토리지',1,'5F-20-R11'),(140,'중요단말VDI',1,'5F-20-R12'),(141,'한금서 업무VDI',1,'5F-20-R13'),(142,'한금서 업무VDI',1,'5F-20-R14'),(143,'VDI망연계',1,'5F-20-R15'),(144,'중요단말VDI HCI',1,'5F-23-R03'),(145,'투자관리시스템',1,'5F-23-R04'),(146,'VOC(P740)',2,'5F-23-R05'),(147,'정보계#2(P870)',1,'5F-23-R07'),(148,'통합SAN(48000)',1,'5F-23-R10'),(149,'ISILION',1,'5F-23-R12'),(150,'투자관리시스템',1,'5F-23-R13'),(151,'인터넷VDI HCI',1,'5F-23-R14'),(152,'IBM 보험코어용',1,'5F-23-R15'),(153,'주전산 VSP5600',1,'5F-28-R01'),(154,'인터넷VDI NVME',1,'5F-28-R03'),(155,'(구)주전산,ALFA',1,'5F-28-R04'),(156,'보안통합',1,'5F-28-R05'),(157,'통합기#2',1,'5F-28-R06'),(158,'통합SQL#1',1,'5F-28-R07'),(159,'IFRS17 PTL',1,'5F-28-R09'),(160,'PTL백업',1,'5F-28-R11'),(161,'PTL백업',1,'5F-28-R12'),(162,'통합로그위변조',1,'5F-28-R13'),(163,'통합로그/빅데이터',1,'5F-28-R14'),(164,'빅데이터 EXA',1,'5F-28-R15'),(165,'사용자체감성능',1,'5F-31-R03'),(166,'소매금융BPM',1,'5F-31-R07'),(167,'변액헷지#5',1,'5F-31-R09'),(168,'TM녹취',1,'5F-31-R12'),(169,'TM녹취/TAB',1,'5F-31-R13'),(170,'통합기,상시검증',1,'5F-31-R14'),(171,'VTL백업',1,'5F-31-R15');
/*!40000 ALTER TABLE `rack_info` ENABLE KEYS */;
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
