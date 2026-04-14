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
-- Table structure for table `network_hardware`
--

DROP TABLE IF EXISTS `network_hardware`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `network_hardware` (
  `hardware_id` int NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `manufacturer` varchar(100) DEFAULT NULL,
  `type_a` varchar(45) DEFAULT NULL,
  `type_b` varchar(45) DEFAULT NULL,
  `type_c` varchar(45) DEFAULT NULL,
  `is_main_unit` varchar(45) DEFAULT NULL,
  `unit_size` int DEFAULT NULL,
  `slot_count` int DEFAULT NULL,
  `power_redundancy` varchar(10) DEFAULT NULL,
  `software_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`hardware_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `network_hardware`
--

LOCK TABLES `network_hardware` WRITE;
/*!40000 ALTER TABLE `network_hardware` DISABLE KEYS */;
INSERT INTO `network_hardware` VALUES (1,'AXGATE 2300M','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',2,NULL,NULL),(2,'EX4600-40F-AFO','Juniper','l2l3','switch','poeswitch','1',1,2,'1',1,NULL,NULL),(3,'AXGATE 1300S','AXGATE','security','vpn','sslvpn','1',1,0,'1',2,NULL,NULL),(4,'WeGuardia ITU 1000','Future Systems','security','vpn','sslvpn','1',1,0,'1',6,NULL,NULL),(6,'AXGATE 90','AXGATE','security','vpn','sslvpn','1',1,0,'0',2,NULL,NULL),(7,'QFX5110-48S-AFO','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(8,'AXGATE TMS 1000S','AXGATE','security','tms','tms','1',1,0,'0',2,NULL,NULL),(9,'BLUEMAX WIPS C5000','SECUI','wireless','wips','controller','1',1,0,'1',7,NULL,NULL),(10,'BLUEMAX WIPS S624','SECUI','wireless','wips','sensor','1',0,0,'0',7,NULL,NULL),(11,'C9800-L-F-K9','Cisco','wireless','ap','controller','1',1,0,'0',8,NULL,NULL),(12,'DN3-HW-APL','Cisco','security','nms','nms','1',1,0,'1',9,NULL,NULL),(13,'CW9166I','Cisco','wireless','ap','ap','1',0,0,'0',8,NULL,NULL),(14,'EX2300-24P','Juniper','l2l3','switch','poeswitch','1',1,0,'1',1,NULL,NULL),(15,'AXGATE 4000S','AXGATE','security','vpn','sslvpn','1',2,1,'1',2,NULL,NULL),(16,'AXGATE 4000S Option Module R-4','AXGATE','module','sfpp','sfpp','0',0,0,'0',NULL,NULL,NULL),(17,'AXGATE 80D','AXGATE','security','vpn','sslvpn','1',1,0,'0',2,NULL,NULL),(18,'SFPP-10G-SR-C','Juniper','module','gbic','10g','0',0,0,'0',NULL,NULL,NULL),(19,'SFP-1G-SX-C','Juniper','module','gbic','1g','0',0,0,'0',NULL,NULL,NULL),(20,'EX2300-48T','Juniper','l2l3','switch','poeswitch','1',1,0,'1',1,NULL,NULL),(21,'EX4600-EM-8F','Juniper','module','sfpp','sfpp','0',0,0,'0',NULL,NULL,NULL),(22,'1G SFP GBIC','F5','module','gbic','1g','0',0,0,'0',NULL,NULL,NULL),(23,'1G Bypass Switch','F5','module','bypass','1g','0',0,0,'0',NULL,NULL,NULL),(24,'NetScaler MPX 9120','Citrix','l4l7','lb','waf','1',1,0,'1',12,NULL,NULL),(25,'TrusGuard 10000B','Ahnlab','security','fw','fw','1',2,0,'1',13,NULL,NULL),(26,'TMS 10000B-B001','Ahnlab','security','tms','tms','1',1,0,'1',13,NULL,NULL),(27,'Vforce 1700U','NexG','security','vpn','sslvpn','1',1,2,'1',14,NULL,NULL),(28,'FT-10G1H-SR',NULL,'security','tms','tap','1',1,0,'0',NULL,NULL,NULL),(29,'NetScaler MPX 9110','Citrix','l4l7','lb','waf','1',1,0,'1',12,NULL,NULL),(30,'PAS-K1800','Piolink','l4l7','lb','lb','1',1,0,'1',15,NULL,NULL),(31,'QFX5120-48Y-AFO','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(32,'EX2300-24T','Juniper','l2l3','switch','poeswitch','1',1,0,'1',1,NULL,NULL),(33,'C30_R1','Genians','security','nac','server','1',2,0,'1',3,NULL,NULL),(34,'TMS 10000B-A001','Ahnlab','security','tms','log','1',1,0,'1',13,NULL,NULL),(35,'SFP-1G-T-C','Juniper','module','gbic','1g','0',0,0,'0',NULL,NULL,NULL),(36,'AXGATE TMS 3000','AXGATE','security','vpn','sslvpn','1',2,0,'1',2,NULL,NULL),(37,'AXGATE 300S','AXGATE','security','vpn','sslvpn','1',1,0,'0',2,NULL,NULL),(38,'S10-R2','Genians','nac','sensor','sensor','1',1,0,'1',3,NULL,NULL),(39,'S20H_R1','Genians','nac','sensor','sensor','1',1,0,'1',3,NULL,NULL),(40,'S30H_R1','Genians','nac','sensor','sensor','1',1,0,'1',3,NULL,NULL),(41,'S40H-R1','Genians','nac','sensor','sensor','1',1,0,'1',3,NULL,NULL),(42,'C50-R2','Genians','nac','server','server','1',2,0,'1',3,NULL,NULL),(43,'AXGATE 13000S','AXGATE','security','vpn','sslvpn','1',2,0,'1',2,NULL,NULL),(44,'SRX345','Juniper','security','vpn','ipsec','1',1,0,'1',1,NULL,NULL),(45,'C8300-2N2S-6T','Cisco','l2l3','router','edge','1',2,2,'1',8,NULL,NULL),(46,'EX4100-F-48T','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(47,'EX9214-RED3B-AC','Juniper','l2l3','switch','chassis','1',16,12,'1',1,NULL,NULL),(48,'EX4100-24T','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(49,'Vforce 700U','NexG','security','vpn','sslvpn','1',1,1,'1',14,NULL,NULL),(50,'WeGuardia FW 510','Future Systems','security','vpn','sslvpn','1',1,0,'0',6,NULL,NULL),(51,'WeGuardia FW 4500','Future Systems','security','vpn','sslvpn','1',1,0,'1',6,NULL,NULL),(52,'WeGuardia SMC 2.1','Future Systems','security','vpn','mgmt','1',1,0,'1',NULL,NULL,NULL),(53,'NexG NMS 1000','NexG','security','vpn','mgmt','1',1,0,'1',NULL,NULL,NULL),(54,'EX9200-40XS','Juniper','module','linecard','linecard','0',0,0,'0',1,NULL,NULL),(55,'N3K-C3548P-XL','Cisco','l2l3','switch','ethernetswitch','1',1,0,'1',18,NULL,NULL),(56,'AXGATE 2300S','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',2,NULL,NULL),(57,'EX4300-32F','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(58,'EX4300-24P','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(59,'SRX340','Juniper','security','vpn','ipsec','1',1,0,'1',1,NULL,NULL),(60,'TE 1415','Infoblox','wireless','dhcp','dhcp','1',1,0,'1',19,NULL,NULL),(61,'EX2300-48P','Juniper','l2l3','switch','poeswitch','1',1,0,'1',1,NULL,NULL),(62,'NetScaler MPX 15020','Citrix','l4l7','lb','waf','1',1,0,'1',12,NULL,NULL),(63,'ISR 4331','Cisco','l2l3','router','edge','1',1,0,'0',8,NULL,NULL),(64,'XTM 510','Future Systems','security','vpn','sslvpn','1',1,0,'0',6,NULL,NULL),(65,'EX9200-MPC','Juniper','module','linecard','linecard','0',0,0,'0',1,NULL,NULL),(66,'EX4300-24T','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(67,'AXGATE 50S','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',2,NULL,NULL),(68,'MX480','Juniper','l2l3','router','router','1',6,4,'1',1,NULL,NULL),(69,'S10-R1','Genians','nac','sensor','sensor','1',1,0,'1',3,NULL,NULL),(70,'XTM 1100B','Future Systems','security','vpn','sslvpn','1',1,0,'0',6,NULL,NULL),(71,'ISR 4321','Cisco','l2l3','router','edge','1',1,0,'0',8,NULL,NULL),(72,'PAS-K5200','Piolink','l4l7','lb','lb','1',1,0,'1',15,NULL,NULL),(73,'Alteon 6024','Radware','l2l3','switch','adc','1',2,0,'1',24,NULL,NULL),(74,'ngeniusone을위한서버','ngeniusone을위한서버','ngeniusone을위한서버',NULL,NULL,'1',2,0,'1',25,NULL,NULL),(75,'C-09800-QSJA2','NetScout','security','tms','collector','1',2,0,'1',27,NULL,NULL),(76,'C-50FCNANQH0J0','NetScout','security','tms','tap','1',1,0,'1',28,NULL,NULL),(77,'EX4400-48F','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(78,'QFX5110-48S-AFO','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(79,'QFX10008-REDUND','Juniper','l2l3','switch','chassis','1',13,8,'1',1,NULL,NULL),(80,'QFX5120-48T-AFO','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(81,'EX4400-48T','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(82,'NetScaler MPX 16030','Citrix','l4l7','lb','waf','1',1,0,'1',12,NULL,NULL),(83,'EX4300-48P','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(84,'PAS-K3200','Piolink','l4l7','lb','lb','1',1,0,'1',15,NULL,NULL),(85,'eWalker SWG V9','Susan','l4l7','lb','waf','1',1,0,'1',NULL,NULL,NULL),(86,'Vforce 500UTM','NexG','security','vpn','sslvpn','1',1,1,'1',14,NULL,NULL),(87,'secui mf2 110','SECUI','security','fw','fw','1',1,0,'1',NULL,NULL,NULL),(88,'AXGATE 1000','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',NULL,NULL,NULL),(89,'AXGATE 80','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',NULL,NULL,NULL),(90,'AXGATE 30','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',NULL,NULL,NULL),(91,'AXGATE 300','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',NULL,NULL,NULL),(92,'EX2200-24P','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(93,'EX4300-48T','Juniper','l2l3','switch','ethernetswitch','1',1,0,'1',1,NULL,NULL),(94,'TE 1425','Infoblox','wireless','dhcp','dhcp','1',1,0,'1',19,NULL,NULL),(95,'Arista 7150s',NULL,'securtity','tap','tap','1',1,0,'1',NULL,NULL,NULL),(96,'BYFRONT E5K','Aircuve','security','authn','authn','1',1,0,'1',29,NULL,NULL),(97,'AXGATE 4000','AXGATE','security','vpn','sslvpn','1',2,1,'1',2,NULL,NULL),(98,'TrusGuard 10000A','Ahnlab','security','fw','fw','1',2,0,'1',13,NULL,NULL),(99,'AXGATE 3000S','AXGATE','securtity','vpn','sslvpn','1',1,0,'1',2,NULL,NULL);
/*!40000 ALTER TABLE `network_hardware` ENABLE KEYS */;
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
