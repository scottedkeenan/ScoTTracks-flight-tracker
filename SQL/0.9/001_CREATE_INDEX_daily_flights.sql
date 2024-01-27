-- Rollback
-- reload backup

-- Rectify value set too high

UPDATE daily_flights SET takeoff_airfield = null
WHERE takeoff_airfield = 9999999
AND id = 155384;

-- Set non int values to null
UPDATE daily_flights
SET takeoff_airfield = null
WHERE NOT (
        daily_flights.takeoff_airfield REGEXP '^[0-9]+$'
    );

-- Convert the daily_flights takeoff_airfield and landing_airfield to smallint
ALTER TABLE daily_flights
    MODIFY COLUMN takeoff_airfield smallint UNSIGNED;
ALTER TABLE daily_flights
    MODIFY COLUMN landing_airfield smallint UNSIGNED;

-- Add the indexes

CREATE INDEX idx_takeoff_airfield ON daily_flights (takeoff_airfield);
CREATE INDEX idx_takeoff_timestamp ON daily_flights (takeoff_timestamp);
