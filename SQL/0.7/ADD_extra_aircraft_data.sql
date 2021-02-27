--Rollback SQL

--ALTER TABLE `daily_flights`
--DROP COLUMN `aircraft_model`,
--DROP COLUMN  `competition_number`;


ALTER TABLE `daily_flights`
ADD `aircraft_model` TINYTEXT NULL AFTER `tug_registration`,
ADD `competition_number` TINYTEXT NULL AFTER `aircraft_model`;