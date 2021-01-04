
-- Rollback SQL

--ALTER TABLE daily_flights
--DROP COLUMN launch_type
--DROP COLUMN average_launch_climb_rate
--DROP COLUMN max_launch_climb_rate
--DROP COLUMN launch_complete

-- Rollout SQL

ALTER TABLE daily_flights
ADD COLUMN launch_type VARCHAR(255) DEFAULT NULL,
ADD COLUMN average_launch_climb_rate FLOAT DEFAULT 0,
ADD COLUMN max_launch_climb_rate FLOAT DEFAULT 0,
ADD COLUMN launch_complete BOOLEAN DEFAULT FALSE