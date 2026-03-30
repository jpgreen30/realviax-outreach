# Realviax Outreach API

FastAPI backend for listing scraping, video generation, and agent outreach.

## Project Structure

```
realviax-outreach/
├── app/
│   ├── api/             # Route modules
│   ├── core/            # Config, security
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic (scraper, video, email, sms)
│   ├── utils/           # Helpers
│   └── main.py          # FastAPI app
├── output/              # Generated videos
├── assets/              # Logo, music
├── tests/
├── requirements.txt
├── .env
└── README.md
```

## Quick Start

1. Install deps: `pip install -r requirements.txt`
2. Install ffmpeg: `sudo apt-get install -y ffmpeg`
3. Copy `.env.example` to `.env` and fill keys
4. Init DB: `python -m app.core.init_db`
5. Run: `uvicorn app.main:app --reload`

## Env Vars

- `DATABASE_URL` (default: sqlite:///leads.db)
- `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `VIDEO_OUTPUT_DIR`, `LOGO_PATH`, `MUSIC_DIR`

## API

- `POST /api/scrape` (url, platform) → lead
- `GET /api/leads` → list
- `POST /api/generate/{id}` → start video
- `POST /api/send-email/{id}` → send teaser
- `GET /api/metrics` → stats
- `GET /videos/{filename}` → static videos
