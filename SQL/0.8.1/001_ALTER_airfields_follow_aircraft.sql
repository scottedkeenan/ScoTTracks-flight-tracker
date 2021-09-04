-- Rollback SQL

--ALTER TABLE airfields
--DROP COLUMN follow_aircraft;

-- Rollout SQL

ALTER TABLE airfields
ADD COLUMN follow_aircraft BOOLEAN DEFAULT FALSE;

-- DRL and EGXY
UPDATE airfields
SET follow_aircraft = TRUE
WHERE airfields.name in ('DARLTON', 'SYERSTON')