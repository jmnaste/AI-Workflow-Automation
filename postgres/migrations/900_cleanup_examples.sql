-- 900_cleanup_examples.sql
-- Example maintenance statements. Schedule externally (cron/job) as needed.

-- Delete OTP challenges older than 2 hours
DELETE FROM otp_challenges WHERE sent_at < now() - interval '2 hours';

-- Mark any past-due OTP challenges as expired (idempotent)
UPDATE otp_challenges
SET status = 'expired'
WHERE status = 'sent' AND expires_at < now();

-- Delete sessions expired more than 7 days ago
DELETE FROM sessions WHERE expires_at < now() - interval '7 days';
