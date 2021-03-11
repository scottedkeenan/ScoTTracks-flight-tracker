--rollback sql

--ALTER TABLE sites RENAME TO airfields;
--DROP TABLE airfields


-- Rollout SQL

ALTER TABLE airfields RENAME TO sites;
