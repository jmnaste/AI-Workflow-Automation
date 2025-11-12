-- Seed admin user: jmnaste@yahoo.ca
-- Idempotent: uses ON CONFLICT DO NOTHING

BEGIN;

-- Insert admin user if not already exists
-- Use WHERE NOT EXISTS since the unique constraint is on lower(email), not email directly
INSERT INTO auth.users (id, email, phone, role, is_active, otp_preference, created_at, updated_at, verified_at)
SELECT 
    gen_random_uuid(),
    'jmnaste@yahoo.ca',
    '+15142193815',  -- Phone in E.164 format
    'admin',
    true,
    'sms',
    now(),
    now(),
    now()  -- Mark as verified immediately
WHERE NOT EXISTS (
    SELECT 1 FROM auth.users WHERE lower(email) = lower('jmnaste@yahoo.ca')
);

-- Update schema registry
WITH desired AS (
    SELECT
        COALESCE(
            current_setting('SERVICE_SEMVER', true),
            (SELECT semver FROM auth.schema_registry WHERE service='auth' LIMIT 1),
            '0.1.2'
        ) AS semver,
        to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint AS ts_key
)
INSERT INTO auth.schema_registry(service, semver, ts_key)
SELECT 'auth', semver, ts_key FROM desired
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, applied_at)
SELECT service, semver, ts_key, applied_at
FROM auth.schema_registry
WHERE service = 'auth'
ON CONFLICT DO NOTHING;

-- Record this migration
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 5, '0005_seed_admin_user.sql', md5('0005_seed_admin_user.sql'), 'seed admin user jmnaste@yahoo.ca')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
