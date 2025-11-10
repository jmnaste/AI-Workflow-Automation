-- Restructure auth.users for email-primary authentication
-- Changes:
--   - Make email NOT NULL (primary identifier)
--   - Make phone nullable (optional, stored in E.164 format)
--   - Add otp_preference column (sms or email)
--   - Keep role, is_active, verified_at from 0001
-- Idempotent and safe to re-run

BEGIN;

-- 1) Add otp_preference column
ALTER TABLE auth.users
    ADD COLUMN IF NOT EXISTS otp_preference text NULL CHECK (otp_preference IN ('sms', 'email'));

-- 2) Make email NOT NULL (requires existing data to have emails)
--    NOTE: This will fail if any users lack email. In fresh DB, this is safe.
DO $$
BEGIN
    -- Check if any users exist without email
    IF EXISTS (SELECT 1 FROM auth.users WHERE email IS NULL LIMIT 1) THEN
        RAISE EXCEPTION 'Cannot make email NOT NULL: some users have NULL email';
    END IF;
    
    -- Make email NOT NULL
    ALTER TABLE auth.users ALTER COLUMN email SET NOT NULL;
END $$;

-- 3) Make phone_e164 (or phone) nullable (change from NOT NULL to NULL)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_schema = 'auth' AND table_name = 'users' AND column_name = 'phone_e164') THEN
        ALTER TABLE auth.users ALTER COLUMN phone_e164 DROP NOT NULL;
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'auth' AND table_name = 'users' AND column_name = 'phone') THEN
        ALTER TABLE auth.users ALTER COLUMN phone DROP NOT NULL;
    END IF;
END $$;

-- 4) Rename phone_e164 to phone for simpler naming (if column exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_schema = 'auth' AND table_name = 'users' AND column_name = 'phone_e164') THEN
        ALTER TABLE auth.users RENAME COLUMN phone_e164 TO phone;
    END IF;
END $$;

-- 5) Drop old unique constraint on phone (since it's now nullable and not primary identifier)
ALTER TABLE auth.users DROP CONSTRAINT IF EXISTS users_phone_e164_key;
ALTER TABLE auth.users DROP CONSTRAINT IF EXISTS users_phone_key;

-- 6) Create non-unique index on phone for lookups (nullable fields can have duplicates)
CREATE INDEX IF NOT EXISTS idx_users_phone ON auth.users(phone) WHERE phone IS NOT NULL;

-- 7) Update users_email_unique index to be the main constraint (already exists from 0002)
--    Ensure it exists and covers the uniqueness requirement
DROP INDEX IF EXISTS auth.users_email_unique;
CREATE UNIQUE INDEX users_email_unique
    ON auth.users (lower(email));

-- 8) Versioning footer
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

-- 9) Record this migration
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 4, '0004_restructure_for_email_primary.sql', md5('0004_restructure_for_email_primary.sql'), 
        'restructure: email NOT NULL primary, phone nullable, add otp_preference')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
