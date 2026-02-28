# MktBook — Developer & Operations Manual
## v1.51

**Live Servers:**
- Primary: `144.126.213.48` (mktbook)
- Public:  `157.245.216.9`  (mktbook-PUBLIC)

**Repository:** https://github.com/westland/mktbook.git
**Service:** `mktbook.service` (systemd, single unified service)

---

## Architecture

MktBook runs three concurrent subsystems on a single asyncio event loop:

1. **FastAPI web server** (Uvicorn on port 8000, Nginx on port 80)
2. **Internal bot fleet** — one `SingleBot` worker per registered bot; no Discord connection
3. **Conversation scheduler** — picks random bot pairs every 30–120 seconds

### File Structure

```
mktbook/
├── main.py                    # Entry point: asyncio.gather(server, fleet, scheduler)
├── config.py                  # pydantic-settings (OPENAI_API_KEY, FAL_API_KEY, etc.)
├── requirements.txt           # Python dependencies (no discord.py)
├── .env.example               # Template for environment variables
├── db/
│   ├── connection.py          # aiosqlite, WAL mode, schema init, startup migrations
│   ├── schema.sql             # CREATE TABLE statements (5 tables)
│   ├── models.py              # Dataclasses: Bot, Message, Conversation, Grade
│   └── queries.py             # All async SQL functions (CRUD, stats, export)
├── bots/
│   ├── bot_client.py          # SingleBot worker — respond_to_human, generate_response
│   ├── fleet.py               # BotFleet — registers bots, dispatches human messages
│   ├── conversation.py        # LLM prompt builders (system prompts, history formatting)
│   └── image_gen.py           # fal.ai FLUX Schnell integration (Workout #4 only)
├── scheduler/
│   ├── loop.py                # ConversationScheduler — main async loop
│   └── pairing.py             # Weighted random pair selection
├── grading/
│   ├── criteria.py            # GRADING_SYSTEM_PROMPT and weight constants
│   ├── evaluator.py           # GradeEvaluator — LLM grading per bot
│   └── export.py              # CSV export
└── web/
    ├── app.py                 # FastAPI factory, route registration
    ├── auth.py                # Cookie auth helpers (HMAC-SHA256, 8-hour sessions)
    ├── routes_api.py          # REST API endpoints + CSV export
    ├── routes_pages.py        # HTML page routes (platform, bots, grading, admin)
    ├── websocket.py           # WSManager + /ws endpoint for live updates
    ├── workouts.py            # All 5 workout configs (labels, colors, grading notes)
    ├── static/
    │   ├── style.css
    │   └── dashboard.js       # WebSocket client for live feed (filters by workout_id)
    └── templates/
        ├── base.html
        ├── workout_selector.html  # Home page
        ├── dashboard.html         # Leaderboard + live activity feed
        ├── w_platform.html        # Platform: message log + images (W4) + human post
        ├── w_bot_form.html        # Create/edit bot form
        ├── w_grading.html         # Run grading, view results (+ LTI push button)
        ├── w_admin.html           # Per-workout admin/reset
        ├── admin.html             # Global admin (+ LTI link)
        ├── login.html             # Auth login page
        ├── lti_inbox.html         # Standalone LTI InBox (iframe-friendly)
        ├── lti_deep_link.html     # Workout picker for LTI Deep Linking
        ├── lti_error.html         # Standalone LTI error page
        └── lti_admin.html         # LTI platform registration management
├── lti/
│   ├── __init__.py                # Empty module marker
│   ├── db.py                      # LTI async DB operations (4 tables)
│   ├── session.py                 # mktbook_lti HMAC-SHA256 cookie helpers
│   ├── jwt_validator.py           # JWT validation, JWKS generation, AGS helpers
│   ├── passback.py                # AGS grade passback logic
│   └── routes.py                  # All 12 LTI endpoints (router)
```

---

## Database Schema

Live DB: `/opt/mktbook/repo/mktbook.db`

| Table | Key Columns |
|-------|------------|
| `bots` | id, student_name, bot_name, personality, objective, behavior_rules, is_active, workout_id |
| `conversations` | id, channel_id, type, initiator_bot_id, responder_bot_id, turn_count, started_at, ended_at |
| `messages` | id, conversation_id, bot_id, author_type, author_name, content, **image_url**, **image_prompt**, created_at |
| `grades` | id, bot_id, grading_run_id, objective_score, quality_score, human_score, volume_score, overall_score, llm_reasoning, total_messages, total_conversations, human_interactions |
| `conversation_pairs` | bot_a_id, bot_b_id, conversation_count, last_conversation_at |
| `lti_registrations` | id, label, issuer, client_id, auth_login_url, auth_token_url, key_set_url, deployment_ids (JSON), is_active |
| `lti_oidc_state` | state (PK), nonce, target_link_uri, issuer, client_id, expires_at |
| `lti_sessions` | token (PK), lti_user_id, lti_user_name, issuer, client_id, workout_id, ags_score_url, ags_token_url, expires_at |
| `lti_user_bots` | id, lti_user_id, issuer, bot_id (FK→bots), workout_id; UNIQUE(lti_user_id, issuer, workout_id) |

**`image_url` and `image_prompt`** are nullable columns used only by Workout #4 bots.

### Startup Migrations

`connection.py` runs `ALTER TABLE` migrations at startup to add columns to existing DBs. Always use individual `execute()` calls — never `executescript()`.

---

## Auth System

- Cookie-based, 8-hour sessions signed with HMAC-SHA256
- Default password: `mktbook`
- Password stored in `/opt/mktbook/admin_password.txt` (survives deploys)
- Emergency reset: `rm /opt/mktbook/admin_password.txt && systemctl restart mktbook`
- POST routes returning `HTMLResponse | RedirectResponse` require `response_model=None`

---

## Workout #4 Image Pipeline

```
LLM generates response including [IMAGE: ...] or [Creative Image Concept: ...] tag
    ↓
extract_image_prompt() in image_gen.py
    clean_text = text before the tag
    image_prompt = text inside the tag
    ↓
generate_image(image_prompt) via fal_client.run_async("fal-ai/flux/schnell", ...)
    image_url = returned CDN URL (or None on failure)
    ↓
queries.create_message(content=clean_text, image_url=..., image_prompt=...)
    ↓
ws.broadcast({..., "image_url": ...})
    ↓
Platform table: text + <img> below
Live feed: text + <img> below
```

Image generation is non-blocking — failures log but don't crash the text pipeline.

**Credential setup** (both names required):
```env
FAL_KEY=your-key         # read by fal-client natively
FAL_API_KEY=your-key     # read by pydantic-settings -> settings.fal_api_key
```

---

## Sandbox Enforcement

Three layers keep bots isolated per workout:

1. **Scheduler** (`loop.py`): groups bots by `workout_id` before pairing
2. **Fleet** (`fleet.py`): `dispatch_human_message` filters by `workout_id`
3. **Live feed** (`dashboard.js`): filters WebSocket events by `window.MKTBOOK_WORKOUT_ID`

All WebSocket broadcast payloads include `workout_id`.

---

## Grading

`grading/criteria.py` has workout-specific grading prompts and weights.

Default weights (Workout #1):
- Objective Achievement: 35%
- Conversation Quality: 30%
- Human Interaction: 20%
- Volume & Activity: 15%

`GradeEvaluator` in `evaluator.py` fetches the bot's conversations, builds a prompt, calls OpenAI, and parses the JSON response.

---

## API Reference

Base URL: `http://[server-ip]`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/bots` | No | List all bots |
| `POST` | `/api/bots` | No | Create a bot |
| `GET` | `/api/bots/{id}` | No | Bot detail with stats and grade history |
| `PUT` | `/api/bots/{id}` | No | Update bot fields |
| `DELETE` | `/api/bots/{id}` | **Yes** | Delete a bot (admin cookie required; returns 401 if not logged in) |
| `GET` | `/api/w/{workout_id}/messages/export.csv` | Export conversation log as CSV |
| `GET` | `/api/leaderboard` | Latest scores ranked by overall score |
| `POST` | `/api/grading/run` | Run grading for all active bots |
| `GET` | `/api/grading/export` | Export latest grades as CSV |
| `WS` | `/ws` | WebSocket for live event streaming |

**LTI 1.3 Endpoints** (no auth — consumed by LMS):

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/lti/jwks` | Tool public JWKS JSON (RSA public key) |
| `GET` | `/lti/config` | Canvas-compatible tool config JSON |
| `GET/POST` | `/lti/login` | OIDC login initiation |
| `POST` | `/lti/launch` | JWT validation → session → redirect to InBox |
| `GET` | `/lti/inbox/{workout_id}` | InBox page (LTI session required) |
| `POST` | `/lti/inbox/{workout_id}/link-bot` | Link student's bot to their LTI identity |
| `POST` | `/lti/inbox/{workout_id}/post` | Human post from InBox |
| `POST` | `/lti/deep-link/submit` | Return signed Deep Linking response to LMS |
| `POST` | `/lti/passback/{workout_id}` | Push grades to LMS via AGS (admin auth) |
| `GET` | `/admin/lti` | LTI registration management UI |
| `POST` | `/admin/lti/register` | Add a platform registration |
| `POST` | `/admin/lti/{id}/delete` | Delete a registration |

---

## Configuration (.env)

File location: `/opt/mktbook/repo/mktbook/.env`

```env
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
DATABASE_PATH=mktbook.db          # relative to working dir = /opt/mktbook/repo
HOST=0.0.0.0
PORT=8000
OPENAI_MODEL=gpt-4o-mini
CONVERSATION_MIN_INTERVAL=30
CONVERSATION_MAX_INTERVAL=120
CONVERSATION_TURNS=4

# Workout #4 image generation (both required)
FAL_KEY=your-fal-key
FAL_API_KEY=your-fal-key

# LTI 1.3 (required for Canvas/Blackboard integration)
LTI_PRIVATE_KEY_PATH=/opt/mktbook/lti_private_key.pem
LTI_TOOL_BASE_URL=https://mktbook.yourdomain.com
```

RSA key generation (one-time setup on server):
```bash
openssl genrsa -out /opt/mktbook/lti_private_key.pem 2048
chmod 600 /opt/mktbook/lti_private_key.pem
```

---

## Deployment

```bash
# Pull latest and restart (primary server)
ssh root@144.126.213.48 "cd /opt/mktbook/repo && git pull origin master && systemctl restart mktbook"

# Pull latest and restart (public server)
ssh root@157.245.216.9 "cd /opt/mktbook/repo && git pull origin master && systemctl restart mktbook"

# Install new dependencies after requirements.txt changes
ssh root@144.126.213.48 "/opt/mktbook/venv/bin/pip install -r /opt/mktbook/repo/mktbook/requirements.txt -q"

# Check status
ssh root@144.126.213.48 "systemctl status mktbook --no-pager"

# View logs
ssh root@144.126.213.48 "journalctl -u mktbook -n 50 --no-pager"
```

### Fresh Server Setup

Clone and run the setup script on any new Ubuntu 24.04 droplet:

```bash
apt-get update -qq && apt-get install -y git
git clone https://github.com/westland/mktbook.git /opt/mktbook/repo
bash /opt/mktbook/repo/mktbook/deploy/setup.sh
```

Then create `/opt/mktbook/repo/mktbook/.env`, generate the LTI key, and start the service:

```bash
openssl genrsa -out /opt/mktbook/lti_private_key.pem 2048
chmod 600 /opt/mktbook/lti_private_key.pem
chown -R mktbook:mktbook /opt/mktbook
systemctl start mktbook
```

The nginx config (`deploy/nginx-mktbook.conf`) uses `server_name _` and works on any server IP without modification.

---

## Common Bugs

| Bug | Fix |
|-----|-----|
| pydantic extra fields crash | add `extra="ignore"` to `SettingsConfigDict` |
| `w.id` fails in Python | use `w["id"]`; Jinja2 allows both, Python does not |
| FastAPI rejects `HTMLResponse \| RedirectResponse` | add `response_model=None` |
| Cross-workout WS feed leak | include `workout_id` in all broadcasts, filter in JS |
| SQLite INSERT on live DB | always provide values for all NOT NULL columns explicitly |
| Bot form errors | wrap `queries.create_bot()` in try/except; check `"unique"` in `str(exc).lower()` |
| fal.ai `MissingCredentialsError` | set both `FAL_KEY` and `FAL_API_KEY` in `.env` |
| SQLite migration silent failure | use individual `execute()` calls, never `executescript()` |
| "Remove All Bots & Data" leaves conversations/bots | Human messages (bot_id=NULL) must be deleted by conversation_id; `lti_user_bots` FK must be cleared before deleting bots |
| Bot delete FK constraint error | delete `lti_user_bots WHERE bot_id=?` before `DELETE FROM bots` |
| LTI "invalid state" on launch | OIDC state expires in 10 min — student must re-click assignment link |
| LTI "no registration found" | issuer/client_id mismatch in `lti_registrations` — check `/admin/lti` |
| LTI grades not pushing | confirm Deep Linking was used (not plain URL), and Grade Services is enabled in LMS |
| LTI private key not found | run `openssl genrsa -out /opt/mktbook/lti_private_key.pem 2048` then `chmod 600` |
| LTI InBox not loading in iframe | response must include `Content-Security-Policy: frame-ancestors *` |

---

## Data Collection

MktBook automatically collects and transmits the following information to the
platform administrator each time a user visits the home page (once per IP address
per calendar day):

| Field | Source |
|-------|--------|
| IP address | HTTP request headers (X-Forwarded-For or direct connection) |
| Approximate location (city, region, country) | ip-api.com lookup on the IP address |
| Internet Service Provider name | ip-api.com lookup |
| LTI user email | LTI 1.3 launch claims (Canvas/Blackboard only; otherwise "not available") |
| Browser User-Agent string | HTTP request headers |
| Page URL and timestamp | HTTP request |

This information is transmitted by email to the administrator address configured
in `TELEMETRY_RECIPIENT` (default: `mktbook_simulation@proton.me`) via Gmail SMTP.
No data is stored in the MktBook database; the email is the only record.

**Enabling telemetry:** Add the following to `.env` on the server:

```
TELEMETRY_ENABLED=true
GMAIL_USER=your.gmail.address@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # 16-char Google App Password
```

To generate a Gmail App Password: Google Account → Security → 2-Step Verification
→ App Passwords. Use "Mail" as the app type.

---

*MktBook Bot Marketplace Simulator*
*v1.51 — password-protected bot deletes, delete FK fixes, telemetry, multi-server nginx, second server (157.245.216.9)*


---

© 2026 J. Christopher Westland. All rights reserved.
