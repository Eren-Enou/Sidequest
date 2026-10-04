-- sidequest-dialect: postgresql
-- Existing goals remain current; lifecycle and saved sessions are unchanged.
ALTER TABLE goals ADD COLUMN readiness VARCHAR(7) NOT NULL DEFAULT 'current'
    CONSTRAINT ck_goal_readiness CHECK (readiness IN ('current', 'later'));
