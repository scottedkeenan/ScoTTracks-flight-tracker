-- phpMyAdmin SQL Dump
-- version 4.9.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Mar 20, 2021 at 04:57 PM
-- Server version: 10.3.27-MariaDB-cll-lve
-- PHP Version: 7.3.26

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `scottedk_ogn_logs`
--
CREATE DATABASE IF NOT EXISTS `scottedk_ogn_logs` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `scottedk_ogn_logs`;

-- --------------------------------------------------------

--
-- Table structure for table `received_beacons`
--

CREATE TABLE `received_beacons` (
  `id` int(11) NOT NULL,
  `address` varchar(255) DEFAULT NULL,
  `address_type` int(11) DEFAULT NULL,
  `aircraft_type` int(11) DEFAULT NULL,
  `altitude` float DEFAULT NULL,
  `aprs_type` varchar(255) DEFAULT NULL,
  `beacon_type` varchar(255) DEFAULT NULL,
  `climb_rate` float DEFAULT NULL,
  `comment` varchar(255) DEFAULT NULL,
  `dstcall` varchar(255) DEFAULT NULL,
  `error_count` int(11) DEFAULT NULL,
  `flightlevel` int(11) DEFAULT NULL,
  `frequency_offset` int(11) DEFAULT NULL,
  `gps_quality` varchar(255) DEFAULT NULL,
  `ground_speed` float DEFAULT NULL,
  `hardware_version` varchar(255) DEFAULT NULL,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `proximity` varchar(255) DEFAULT NULL,
  `raw_message` varchar(255) DEFAULT NULL,
  `real_address` varchar(255) DEFAULT NULL,
  `receiver_name` varchar(255) DEFAULT NULL,
  `reference_timestamp` timestamp NULL DEFAULT NULL,
  `relay` varchar(255) DEFAULT NULL,
  `signal_power` varchar(255) DEFAULT NULL,
  `signal_quality` varchar(255) DEFAULT NULL,
  `software_version` varchar(255) DEFAULT NULL,
  `stealth` varchar(255) DEFAULT NULL,
  `symbolcode` varchar(255) DEFAULT NULL,
  `symboltable` varchar(255) DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT NULL,
  `track` varchar(255) DEFAULT NULL,
  `turn_rate` varchar(255) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `received_beacons`
--
ALTER TABLE `received_beacons`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `received_beacons`
--
ALTER TABLE `received_beacons`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
