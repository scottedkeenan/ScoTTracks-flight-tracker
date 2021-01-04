
-- Rollback SQL

--ALTER TABLE daily_flights
--DROP COLUMN takeoff_airfield,
--DROP COLUMN landing_airfield

-- Rollout SQL

ALTER TABLE daily_flights
ADD COLUMN takeoff_airfield varchar(255) DEFAULT NULL,
ADD COLUMN landing_airfield varchar(255) DEFAULT NULL