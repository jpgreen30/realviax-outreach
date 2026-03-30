# Realviax Outreach Automation

Automated system for generating listing videos and outreaching to real estate agents with upsell offers.

## Features

- **Multi-platform scraping**: Zillow, Redfin, Realtor.com
- **Auto video generation**: 30s teaser + 60s full versions
- **Personalized outreach**: Email (Brevo) + SMS (Twilio)
- **Full tracking**: Opens, clicks, conversions, revenue
- **Dashboard**: Web UI for monitoring and manual control
- **Optimized for revenue**: $250 upsell per converted lead

## Quick Start

### 1. Install dependencies

```bash
cd realviax-outreach
pip install -r requirements.txt

# Install ffmpeg (required)
sudo apt-get install -y ffmpeg

# Ensure Chrome for optional Selenium scraping
# Optional: playwright install chromium
```

### 2. Configure credentials

Create `.env` file in the project root:

```bash
# Brevo (Sendinblue) for email
export BREVO_API_KEY="your-key"
export BREVO_SENDER_EMAIL="your@email.com"
export BREVO_SENDER_NAME="Realviax"

# Twilio for SMS
export TWILIO_ACCOUNT_SID="your-sid"
export TWILIO_AUTH_TOKEN="your-token"
export TWILIO_FROM_NUMBER="+1234567890"

# Database (default: SQLite)
export DATABASE_URL="sqlite:///database/leads.db"
```

Or create `config/credentials.json` with the same keys.

### 3. Prepare assets

- Place your logo at `assets/logo.png` (transparent PNG recommended, ~200px height)
- Add luxury background music to `assets/music/` (MP3, ~30-60 seconds)

### 4. Initialize database

```bash
python3 -c "from database.models import init_db; init_db()"
```

### 5. Run the system

**Single listing:**
```bash
python3 main.py --url "https://www.zillow.com/homedetails/..." --platform zillow
```

**Batch processing:**
```bash
# File `urls.txt` with one listing URL per line
python3 main.py --batch urls.txt --platform zillow --max-concurrent 5
```

**Start dashboard:**
```bash
python3 main.py --dashboard
# Visit http://localhost:8000
```

## Architecture

```
realviax-outreach/
├── scraper/          # Multi-platform listing scrapers
├── video/            # Video generator (ffmpeg + PIL)
├── outreach/         # Email (Brevo) + SMS (Twilio) + tracking
├── database/         # SQLAlchemy models (leads, videos, logs)
├── dashboard/        # FastAPI web dashboard
├── config/           # Settings and configuration
├── main.py           # Orchestrator CLI
└── requirements.txt  # Python dependencies
```

## Workflow

1. **Scrape** listing data (photos, price, agent contact)
2. **Generate** 30s teaser video automatically
3. **Send** personalized email with video to agent
4. **Track** opens/clicks via Brevo webhooks (setup required)
5. **Convert** leads who reply to $250 full video
6. **Track** revenue and metrics in dashboard

## Email Templates

- **Teaser email**: 30s video, $250 upsell
- **Full video delivery**: After payment, send 60s video + source files

Templates are rendered inline in `outreach/emailer.py`. Customize as needed.

## Campaign Optimization

### A/B Testing
- Test different subject lines
- Test video thumbnails
- Test pricing offers ($200 vs $250)

### List Building
- Target specific cities/zip codes
- Filter by price range
- Focus on high-end listings ($500k+)

### Deliverability
- Warm up sending domain with Brevo
- Use dedicated IP if sending > 1000/day
- Monitor bounce rates (<2% target)

## Revenue Model

- **Teaser**: free (lead generation)
- **Full 60s video**: $250
- Upsell rate target: 2-5%
- Cost per lead: scraping + email < $1

Example SCENARIO:
- Send 100 emails → 50 opens → 10 replies → 3 conversions
- Revenue: 3 × $250 = $750
- Net profit: $750 - $100 (costs) = $650

## Scale Considerations

- Use proxy rotation for scraping (add in `anti_detection.py`)
- Rate limiting: 2-5 seconds between scrapes
- Parallel processing: adjust `--max-concurrent`
- Database: migrate to PostgreSQL for scale
- Video rendering: queue with Celery/Redis

## Troubleshooting

**ModuleNotFoundError: No module named moviepy**
```bash
pip install moviepy==1.0.3
```

**ffmpeg not found**
```bash
sudo apt-get install ffmpeg
```

**Scraping blocked**
- Add more realistic delays
- Use residential proxies
- Rotate user agents
- Consider using browser automation (Selenium) as fallback

**Emails not sending**
- Verify Brevo API key
- Check sender domain is verified in Brevo
- Monitor Brevo dashboard for bounces

## Roadmap

- [ ] Video CDN hosting (S3 + CloudFront)
- [ ] Automated invoice generation (Stripe)
- [ ] SMS follow-up automation
- [ ] A/B test framework
- [ ] Multi-agent support
- [ ] CRM integration (HubSpot/ActiveCampaign)

## License

Proprietary - Realviax

---

**Questions?** Contact support@realviax.com