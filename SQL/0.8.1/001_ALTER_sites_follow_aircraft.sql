-- Rollback SQL

--ALTER TABLE sites
--DROP COLUMN follow_aircraft BOOLEAN DEFAULT FALSE;

-- Rollout SQL

ALTER TABLE sites
ADD COLUMN follow_aircraft BOOLEAN DEFAULT FALSE;

-- DRL and EGXY
UPDATE sites
SET follow_aircraft = TRUE
WHERE sites.id in (22, 79)