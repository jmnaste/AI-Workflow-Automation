# Prompt Log (minimal Q/A)

Entries are appended in reverse chronological order.

**Format**: `YYYY-MM-DD HH:MM — Topic`

**Instructions for Copilot**: 
- User will request prompt log update by saying: **"I want to commit and update prompt log"**
- **Log only significant prompts** (architectural decisions, feature requests, workflow changes)
- Skip trivial requests (clarifications, small fixes, acknowledgments)
- When requested, add entry with:
  - Timestamp in YYYY-MM-DD HH:MM format
  - Full prompt text (no ellipsis)
  - **Synthetic answer** (1-2 sentences max, focus on what was done)
- Then proceed with commit workflow (check last commit, propose semantic message)

---

## 2025-10-31 — Hostinger deployment help
- Prompt:
```
Now help me have this configuration up-and-running on the vps on hostinger (See <attachments> above for file contents. You may not need to search or read the file again.)
```
- Answer (minimal): Use deploy/docker-compose.yml with .env (TRAEFIK_NETWORK); run docker compose from deploy/; verify API /api/health returns ok.

## 2025-10-31 — Minimal VPS stack request
- Prompt:
```
We need to have a minimal setup on the vps so to
1. Keep n8n 100% functional without step back in current setup (workflows, credentials, ...)
2. Have a minimal fastapi api that implements a minimal health check
3. Have a minimal ui that solely requests api for health check

Please have a file where you log prompt I post and a really minimal answer of yours. This shall be done for each and every post I make.
```
- Answer (minimal): Keep n8n unchanged; add FastAPI /api/health; no UI component.

## 2025-10-31 — Logging policy update
- Prompt:
```
In the prompt_log.md I want the entire prompt, no ellipsis
```
- Answer (minimal): Will log full prompts going forward; updated previous entry.

---

## 2025-11-09 14:30 — Prompt logging and commit workflow
- Prompt:
```
From now on I want that the prompt_log.md file be filled with pertinent prompts. The prompt should carry date and time aaaa-mm-dd hh.mm. What do I do for copilot not forget to maintain this? Also, can I during conversation ask for commit, I say I want to commit, copilot knows when was last commit and propose a synthetic phrase for commit description. 

Please make sure the file 3.Engineering_method_vibe.md is fully and correctly describing this way of working, there is I think already a section but make sure it is complete with regard with the current request of mine.
```
- Answer (minimal): Updated prompt_log.md with instructions for Copilot; added "Commit Workflow with Copilot" section to 3.Engineering_method_vibe.md; documented prompt logging process. User can now say "I want to commit" and Copilot will propose semantic commit message based on git diff since last commit (2025-11-09 11:26 "refine ui style").

---

## 2025-11-09 14:45 — Refined prompt logging workflow
- Prompt:
```
In the meantime I have decided that I will ask for prompt_log update along with I want to commit request. I should ask something like: I want to commit and update prompt log?

Remember to log only significant prompts, not all is required and although you save the prompt completly the AI answer need to be synthetic (short).
```
- Answer: Combined commit and prompt log update into single workflow trigger: "I want to commit and update prompt log". Updated both files to specify logging only significant prompts (architecture, features, workflows) with synthetic 1-2 sentence answers.

---

## 2025-11-09 15:00 — OTP-based passwordless authentication UI
- Prompt:
```
Yes we start with simple jwt auth. Also, user identifies itself with email and then we ask his phone number and indicate if he wants otp over email or sms. The login don't ask for password, only send otp and validate answer. We have a free account with twilio for sms otp sending.

Please create a followup file for this and make items checkable. Then proceed with phase 1
```
- Answer: Created `docs/Implementation/auth_implementation.md` with complete checklist for OTP auth. Implemented Phase 1 (UI): multi-step SignIn form (email → phone/preference → OTP), auth API client with mock responses, auth state management with session persistence, protected routes with auto-redirect, AppLayout integration. Build verified successfully. Ready for Phase 2 (BFF backend with Twilio/email/JWT).

---

## 2025-11-09 19:00 — Auth Service implementation and BFF simplification complete
- Prompt:
```
I want to commit and update prompt log
```
- Answer: Completed full architecture refactoring. Auth Service (Python/FastAPI) now owns: OTP authentication (bcrypt hashing, rate limiting, expiration), user management (PostgreSQL CRUD), JWT generation (7-day expiry), SMS delivery (Twilio), Email delivery (SMTP with branded HTML template). BFF simplified to thin proxy only - no business logic, no database access, JWT cookie management only. Created 7 service modules in auth/app/services/ (database, users, otp, jwt, sms, email), 4 FastAPI endpoints, PostgreSQL schema (auth.users, auth.otp_storage, auth.rate_limit). Deleted 5 BFF service files, removed 6 dependencies. Updated documentation: auth/README.md, webui/README.md, auth/AUTH_CONFIGURATION.md (350+ lines), auth_implementation.md, Platform_architecture.md, BFF_CONFIGURATION.md. All environment variables properly separated by service ownership. Ready for deployment and testing.
