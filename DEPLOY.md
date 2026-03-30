# Realviax Outreach - Production Deployment Guide

## ✅ Current Status
- **Server Status**: ✅ Running on port 8000
- **Dashboard**: http://localhost:8000/dashboard
- **API Health**: http://localhost:8000/health
- **Database**: SQLite at `./leads.db`
- **Test Lead**: ID 1 - San Francisco property

---

## 🚀 Deploy TODAY (Choose One)

### Option 1: ngrok (5 min - Public URL NOW)
```bash
# Install ngrok if not present
sudo snap install ngrok  # or download from ngrok.com

# Expose your local server
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Share that URL with Jean - site is LIVE!
```

### Option 2: VPS Systemd Service (Production)
```bash
# 1. Copy service file to systemd
sudo cp realviax.service /etc/systemd/system/

# 2. Reload systemd
sudo systemctl daemon-reload

# 3. Enable auto-start on boot
sudo systemctl enable realviax

# 4. Start the service
sudo systemctl start realviax

# 5. Check status
sudo systemctl status realviax

# 6. View logs
sudo journalctl -u realviax -f
```

### Option 3: Run in Background (Temporary)
```bash
cd /home/jpgreen1/.openclaw/workspace/realviax-outreach
nohup venv/bin/python3 run.py --port 8000 > output.log 2>&1 &
# Check: tail -f output.log
```

---

## 🔑 Environment Variables (Required for Full Features)

Create `.env` file in the project directory:

```bash
# Email (Brevo - free 300/day)
BREVO_API_KEY=your_brevo_api_key_here
FROM_EMAIL=noreply@yourdomain.com

# SMS (Twilio - optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890

# Server
PORT=8000
DATABASE_URL=sqlite:///leads.db
```

**Get Brevo API Key**:
1. Sign up at https://app.brevo.com
2. Settings → SMTP & API → API Keys
3. Create new key, paste into `.env`

---

## 🧪 Quick Test After Deploy

```bash
# Health check
curl https://your-domain.com/health

# Get metrics
curl https://your-domain.com/api/metrics | python3 -m json.tool

# Get leads
curl https://your-domain.com/api/leads?limit=5

# Scrape a listing (POST)
curl -X POST "https://your-domain.com/api/scrape" \
  -F "url=https://www.zillow.com/homedetails/123-Main-St-San-Francisco-CA-94110/2077718009_zpid/" \
  -F "platform=zillow"

# Generate video (POST)
curl -X POST "https://your-domain.com/api/generate/1"

# Send email (POST)
curl -X POST "https://your-domain.com/api/send-email/1"
```

---

## 📊 Dashboard Features

**Dashboard URL**: http://localhost:8000/dashboard (or your public URL)

**Features**:
- Real-time metrics (leads, emails sent, conversions, revenue)
- Manual lead entry form
- View recent leads
- Generate video (one-click)
- Send teaser email (one-click)
- Auto-refresh every 30 seconds

---

## 🐛 Troubleshooting

**Port already in use**:
```bash
sudo lsof -i :8000  # Find process
sudo kill -9 <PID>  # Kill it
```

**Dashboard not loading**:
- Check logs: `sudo journalctl -u realviax -f` (systemd) or `tail -f output.log`
- Verify files exist: `ls dashboard/templates/index.html`
- Check port: `curl http://localhost:8000/health`

**Database errors**:
- Delete DB to reset: `rm leads.db` (data will be lost)
- Server auto-creates fresh DB on startup

**Email not sending**:
- Verify `BREVO_API_KEY` is set in `.env` or systemd Environment
- Check logs for API errors
- Test with curl: `curl -s -X POST https://api.brevo.com/v3/account`

---

## 📦 What's Included

- **FastAPI** backend (port 8000)
- **SQLite** database (leads.db)
- **Dashboard** (HTML/JS/CSS)
- **Scraper** (requests + BeautifulSoup)
- **Email** (Brevo SMTP API)
- **Video Generator** (FFmpeg)
- **REST API** endpoints
- **Systemd** service file

---

## 🎯 Next Steps After Deploy

1. ✅ Deploy server (ngrok or systemd)
2. ⬜ Set up domain + SSL (nginx reverse proxy)
3. ⬜ Configure Brevo email templates
4. ⬜ Add payment integration (Stripe) for video purchases
5. ⬜ Add lead scoring/prioritization
6. ⬜ Implement real photo fetching from listings
7. ⬜ Add SMS follow-up sequences
8. ⬜ Build prospect analytics dashboard

---

## 📞 Support

**Jean**: Your system is running NOW at http://localhost:8000

**Deploy today**: Use ngrok for immediate public URL, then set up systemd for production.

Need help? Run `sudo systemctl status realviax` and share the output.
