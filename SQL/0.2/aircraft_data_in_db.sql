
-- Rollback SQL

--ALTER TABLE daily_flights
--DROP COLUMN tracking_launch_height,
--DROP COLUMN tracking_launch_start_time

-- Rollout SQL

ALTER TABLE daily_flights
ADD COLUMN tracking_launch_height float,
ADD COLUMN tracking_launch_start_time timestamp NULL DEFAULT NULL