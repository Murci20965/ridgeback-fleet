-- Run once as the database owner, after the first pipeline run has created the tables.
-- The API connects with this role, so even a bug can't change data.
-- Replace CHANGE_ME with a generated password, and don't commit it.
CREATE ROLE ridgeback_api LOGIN PASSWORD 'CHANGE_ME';
GRANT USAGE ON SCHEMA public TO ridgeback_api;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ridgeback_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ridgeback_api;
