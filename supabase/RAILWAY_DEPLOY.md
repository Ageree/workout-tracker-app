# Railway Deployment Guide

Quick guide to deploy Agent Swarm on Railway.

## Prerequisites

- Railway account ([railway.app](https://railway.app))
- GitHub repo with this code
- Supabase project with migrations applied
- OpenAI API key

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Select your repository
4. Click **Add variables** before deploying

## Step 2: Set Environment Variables

In Railway Dashboard → **Variables**, add:

### Required Variables

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | `https://measgjlyzxnootmkhktj.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Your service_role key from Supabase Dashboard |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `ENVIRONMENT` | `production` |

### Recommended Variables

| Variable | Value |
|----------|-------|
| `LOG_LEVEL` | `INFO` |
| `PERPLEXITY_API_KEY` | Your Perplexity key (optional) |
| `PERPLEXITY_ENABLED` | `true` |
| `SCRAPER_ENABLED` | `false` |

### Agent Intervals (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `RESEARCH_INTERVAL` | `86400` | 1 day (seconds) |
| `EXTRACTION_INTERVAL` | `1800` | 30 minutes |
| `VALIDATION_INTERVAL` | `900` | 15 minutes |
| `KB_INTERVAL` | `600` | 10 minutes |
| `CONFLICT_INTERVAL` | `3600` | 1 hour |
| `PROMPT_ENGINEERING_INTERVAL` | `86400` | 1 day |

## Step 3: Configure Service

In Railway Dashboard → **Settings**:

| Setting | Value |
|---------|-------|
| **Root Directory** | `supabase` |
| **Start Command** | `python scheduler.py` (auto from railway.json) |
| **Builder** | Dockerfile |

## Step 4: Deploy

Click **Deploy** button. Railway will:
1. Build the Docker image from `Dockerfile`
2. Start the scheduler
3. Run all agents on their configured intervals

## Step 5: Verify Deployment

### Check Logs

In Railway Dashboard → **Logs**, you should see:

```
INFO - Scheduler starting...
INFO - Starting agent research with interval 86400s
INFO - Starting agent extraction with interval 1800s
INFO - Starting agent validation with interval 900s
...
```

### Check Supabase

Run these queries in Supabase SQL Editor:

```sql
-- New entries in research queue
SELECT COUNT(*) FROM research_queue
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Processing status
SELECT status, COUNT(*)
FROM research_queue
GROUP BY status;

-- New knowledge
SELECT COUNT(*) FROM scientific_knowledge
WHERE created_at > NOW() - INTERVAL '1 day';
```

## Architecture

```
Railway Service
├── scheduler.py (main entry point)
│   ├── Research Agent     → PubMed, CrossRef, RSS
│   ├── Extraction Agent   → OpenAI GPT-4
│   ├── Validation Agent   → Evidence scoring
│   ├── KB Agent          → Embeddings, deduplication
│   ├── Conflict Agent    → Conflict detection
│   └── Prompt Engineering → Dynamic prompts
│
└── External APIs
    ├── Supabase (PostgreSQL + pgvector)
    ├── OpenAI (GPT-4, embeddings)
    ├── PubMed API
    ├── CrossRef API
    └── Perplexity API (optional)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Build fails** | Check `requirements.txt` for missing packages |
| **No logs appearing** | Verify Root Directory = `supabase` |
| **"SUPABASE_URL required"** | Add environment variables |
| **DB connection error** | Check SUPABASE_URL and SERVICE_KEY |
| **API rate limit** | Reduce batch sizes or intervals |
| **Memory issues** | Upgrade Railway plan or reduce batch sizes |

### Debug Mode

Set `LOG_LEVEL=DEBUG` for verbose logging.

### Manual Test

```bash
# SSH into Railway container
railway run python -c "
from config import get_settings
s = get_settings()
print('Supabase URL:', s.supabase_url)
print('OpenAI configured:', bool(s.openai_api_key))
"
```

## Files Reference

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.11-slim container |
| `railway.json` | Railway service config |
| `Procfile` | Start command |
| `scheduler.py` | Main entry point |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for local dev |

## Monitoring (Optional)

For Telegram alerts, add:
```
TELEGRAM_BOT_TOKEN=<your bot token>
TELEGRAM_CHAT_ID=<your chat id>
```

For Slack alerts:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Cost Estimate

Railway free tier: 500 hours/month
- Agent Swarm runs 24/7 = ~720 hours/month
- Upgrade to Developer plan ($5/month) for continuous operation

---

Ready to deploy? Go to [railway.app](https://railway.app) and follow the steps above!
