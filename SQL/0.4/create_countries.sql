CREATE TABLE `scottedk_ogn_logs`.`countries` ( `id` TINYINT UNSIGNED NOT NULL AUTO_INCREMENT , `country_code` TINYTEXT NOT NULL , `aprs_filter` VARCHAR(255) NOT NULL , PRIMARY KEY (`id`));

INSERT INTO `countries` (country_code, aprs_filter) VALUES
('GB', 'a/59.601095/-11.074219/49.866317/2.724609'),
('AU', 'a/-8.548576/107.567673/-44.956680/156.691405'),
('NZ', 'a/-32.227988/164.810570/-50.372677/178.933475'),
('FR', 'r/46.76740447371319/2.4332087966196627/550');