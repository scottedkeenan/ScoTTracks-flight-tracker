-- Rollback SQL

--DROP TABLE AIRFIELDS;


-- Rollout sql

-- MAKE SURE AIRFIELDS HAS BEEN RENAMED TO SITES!

-- ALTER TABLE airfields RENAME TO sites;

CREATE TABLE `airfields` (
`id` SMALLINT NOT NULL AUTO_INCREMENT ,
`name` TINYTEXT NOT NULL ,
`country_code` TINYTEXT NOT NULL ,
`icao` TINYTEXT NULL ,
`latitude` DOUBLE NOT NULL ,
`longitude` DOUBLE NOT NULL ,
`elevation` DOUBLE NOT NULL ,
`type` TINYTEXT NULL ,
`runways` JSON NULL ,
PRIMARY KEY (`id`));
