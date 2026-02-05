# Production Deployment Guide

Complete guide for deploying the Agent Swarm Knowledge System in production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Migrations](#database-migrations)
4. [Configuration](#configuration)
5. [Deployment Options](#deployment-options)
6. [Monitoring Setup](#monitoring-setup)
7. [Backup Strategy](#backup-strategy)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- Python 3.9+
- PostgreSQL 14+ (via Supabase)
- Git
- Docker (optional, for containerized deployment)

### Required Accounts

- [Supabase](https://supabase.com) account
- [OpenAI](https://openai.com) API account (or [Anthropic](https://anthropic.com))
- (Optional) [PubMed](https://www.ncbi.nlm.nih.gov/home/develop/api/) API key

### System Requirements

- RAM: 512MB minimum, 1GB recommended
- CPU: 1 core minimum
- Disk: 1GB for logs and temporary files

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd supabase
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

Required environment variables:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# LLM API (at least one required)
OPENAI_API_KEY=sk-your-openai-key
# Or
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Optional
PUBMED_API_KEY=your-pubmed-key
ENVIRONMENT=production
```

---

## Database Migrations

### Run All Migrations

Execute migrations in order:

```bash
# Set database URL
export DATABASE_URL="postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres"

# Run migrations
psql $DATABASE_URL -f migrations/001_add_ai_coach.sql
psql $DATABASE_URL -f migrations/003_add_knowledge_system.sql
psql $DATABASE_URL -f migrations/005_add_embeddings_function.sql
psql $DATABASE_URL -f migrations/007_add_semantic_search.sql
```

### Verify Migration

```sql
-- Check vector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check semantic search functions
SELECT proname FROM pg_proc WHERE proname LIKE 'match_%';

-- Check tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' 
AND tablename IN ('research_papers', 'knowledge_claims', 'knowledge_base');
```

---

## Configuration

### Development

```python
from config import DevelopmentConfig

config = DevelopmentConfig()
```

### Production

```python
from config import ProductionConfig

config = ProductionConfig()
```

### Custom Configuration

```python
from config import Settings

config = Settings(
    supabase_url="https://...",
    supabase_service_key="...",
    openai_api_key="sk-...",
    log_level="INFO"
)

# Validate
config.validate_api_keys()
```

---

## Deployment Options

### Option 1: Systemd Service (Recommended for Linux)

#### Create Service File

```bash
sudo nano /etc/systemd/system/agent-swarm.service
```

#### Service Configuration

```ini
[Unit]
Description=Agent Swarm Knowledge System
After=network.target

[Service]
Type=simple
User=agent-swarm
Group=agent-swarm
WorkingDirectory=/opt/agent-swarm
Environment=PYTHONPATH=/opt/agent-swarm
EnvironmentFile=/opt/agent-swarm/.env
ExecStart=/opt/agent-swarm/venv/bin/python -m scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=agent-swarm

[Install]
WantedBy=multi-user.target
```

#### Setup and Start

```bash
# Create user
sudo useradd -r -s /bin/false agent-swarm

# Set permissions
sudo mkdir -p /opt/agent-swarm
sudo cp -r . /opt/agent-swarm/
sudo chown -R agent-swarm:agent-swarm /opt/agent-swarm

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable agent-swarm
sudo systemctl start agent-swarm

# Check status
sudo systemctl status agent-swarm

# View logs
sudo journalctl -u agent-swarm -f
```

### Option 2: Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run as non-root user
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from monitoring.health_check import HealthChecker; print('OK')" || exit 1

CMD ["python", "-m", "scheduler"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  agent-swarm:
    build: .
    env_file: .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: Cloud Run (Google Cloud)

```bash
# Build and deploy
gcloud run deploy agent-swarm \
  --source . \
  --set-env-vars="$(cat .env | xargs)" \
  --memory=1Gi \
  --cpu=1 \
  --concurrency=1 \
  --max-instances=1 \
  --min-instances=1 \
  --region=us-central1
```

### Option 4: AWS ECS/Fargate

See AWS documentation for ECS task definition and service configuration.

### Option 5: Railway (Recommended for Quick Deploy)

Railway offers simple deployment with automatic builds from GitHub.

#### Step 1: Create Project

1. Go to [railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your repository
4. Set **Root Directory** to `supabase`

#### Step 2: Configure Environment Variables

In Railway Dashboard → Settings → Variables, add:

**Required:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
OPENAI_API_KEY=sk-your-openai-key
ENVIRONMENT=production
```

**Recommended:**
```
LOG_LEVEL=INFO
PERPLEXITY_API_KEY=pplx-your-key (optional)
PERPLEXITY_ENABLED=true
SCRAPER_ENABLED=false
```

**Agent Intervals (optional):**
```
RESEARCH_INTERVAL=86400      # 1 day
EXTRACTION_INTERVAL=1800     # 30 min
VALIDATION_INTERVAL=900      # 15 min
KB_INTERVAL=600              # 10 min
CONFLICT_INTERVAL=3600       # 1 hour
PROMPT_ENGINEERING_INTERVAL=86400
```

#### Step 3: Verify Deployment Settings

The project includes pre-configured files:
- `railway.json` - Railway configuration
- `Dockerfile` - Container definition
- `Procfile` - Start command

Default settings in `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "python scheduler.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5,
    "numReplicas": 1
  }
}
```

#### Step 4: Deploy and Monitor

After deployment, check logs for:
```
INFO - Scheduler starting...
INFO - Loaded 18 trusted authors, 15 trusted journals
INFO - Research Agent starting search...
```

#### Step 5: Verify in Supabase

```sql
-- Check research queue
SELECT COUNT(*) FROM research_queue
WHERE created_at > NOW() - INTERVAL '1 day';

-- Check processed articles
SELECT status, COUNT(*) FROM research_queue
GROUP BY status;

-- Check new knowledge
SELECT COUNT(*) FROM scientific_knowledge
WHERE created_at > NOW() - INTERVAL '1 day';
```

#### Railway Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check Dockerfile and requirements.txt |
| No logs | Verify Root Directory = `supabase` |
| DB connection error | Check SUPABASE_URL and SERVICE_KEY |
| API errors | Verify OPENAI_API_KEY |
| Agent not starting | Check ENVIRONMENT=production |

---

## Monitoring Setup

### Health Checks

```python
from monitoring.health_check import HealthChecker
from services.supabase_client import SupabaseClient
from config import get_settings

settings = get_settings()
client = SupabaseClient(settings.supabase_url, settings.supabase_service_key)
checker = HealthChecker(client)

# Run checks
health = await checker.check_all()
print(health.to_dict())
```

### Metrics Collection

```python
from monitoring.agent_metrics import get_metrics_collector

collector = get_metrics_collector()

# Register agents
collector.register_agent('research')
collector.register_agent('extraction')

# Record metrics
collector.record_success('research')
collector.record_failure('extraction', 'API error')

# Get stats
stats = collector.get_stats()
```

### Logging Configuration

Logs are written to stdout/stderr. Configure log aggregation based on your platform:

**Datadog:**
```bash
# Install datadog-agent and configure log collection
```

**CloudWatch (AWS):**
```bash
# Use awslogs driver with Docker
```

**Grafana Stack:**
```bash
# Use Loki for log aggregation
```

---

## Backup Strategy

### Database Backups

Supabase provides automatic backups. For additional safety:

```bash
# Manual backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup (add to crontab)
0 2 * * * pg_dump $DATABASE_URL > /backups/agent_swarm_$(date +\%Y\%m\%d).sql
```

### Configuration Backup

```bash
# Backup .env
cp .env .env.backup.$(date +%Y%m%d)

# Store securely (example with AWS S3)
aws s3 cp .env.backup.20240115 s3://your-backup-bucket/agent-swarm/
```

### Knowledge Base Export

```python
# Export knowledge base
from services.supabase_client import SupabaseClient
import json

client = SupabaseClient(url, key)
claims = await client.get_all_claims()

with open('knowledge_backup.json', 'w') as f:
    json.dump(claims, f, indent=2)
```

---

## Troubleshooting

### Common Issues

#### Agents Not Starting

**Symptoms:** Service starts but no agent activity

**Check:**
```bash
# Verify configuration
python -c "from config import get_settings; s = get_settings(); s.validate_api_keys()"

# Check Supabase connection
python -c "from services.supabase_client import SupabaseClient; ..."

# View logs
sudo journalctl -u agent-swarm -f
```

**Solutions:**
- Verify `.env` file exists and is readable
- Check Supabase URL and service key
- Ensure at least one LLM API key is configured

#### Rate Limiting Errors

**Symptoms:** Frequent 429 errors in logs

**Solutions:**
- Reduce rate limits in configuration
- Add API keys (especially PubMed)
- Check API quotas and upgrade if needed

```python
# Lower rate limits
from config import Settings

config = Settings(
    pubmed_rate_limit=2.0,  # Reduce from 3.0
    crossref_rate_limit=5.0,  # Reduce from 10.0
)
```

#### Circuit Breaker Open

**Symptoms:** "Circuit breaker is open" errors

**Solutions:**
- Check external API status
- Wait for reset timeout (60s default)
- Review logs for error details
- Restart service if needed

#### Database Connection Errors

**Symptoms:** "Connection refused" or timeout errors

**Check:**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check network connectivity
nc -zv db.[project].supabase.co 5432
```

**Solutions:**
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Check IP allowlist in Supabase dashboard
- Verify migrations are applied

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m scheduler
```

### Health Check

```bash
# Run health check
python -c "
import asyncio
from config import get_settings
from services.supabase_client import SupabaseClient
from monitoring.health_check import HealthChecker

async def check():
    settings = get_settings()
    client = SupabaseClient(settings.supabase_url, settings.supabase_service_key)
    checker = HealthChecker(client)
    health = await checker.check_all()
    print(health.to_dict())

asyncio.run(check())
"
```

### Performance Tuning

#### Adjust Agent Intervals

```python
# For lower resource usage
from config import ProductionConfig

config = ProductionConfig()
config.research_interval = 172800  # 2 days
config.extraction_interval = 3600  # 1 hour
```

#### Batch Size Tuning

```python
# Reduce memory usage
config.research_batch_size = 10
config.extraction_batch_size = 3
```

---

## Security Considerations

1. **API Keys:** Never commit API keys to version control
2. **Service Keys:** Use Supabase service role key only on server
3. **Network:** Restrict database access to application servers
4. **Logs:** Sanitize logs to avoid leaking sensitive data
5. **Updates:** Keep dependencies updated

---

## Support

For issues and questions:

1. Check logs: `journalctl -u agent-swarm -f`
2. Run health check (see above)
3. Review this troubleshooting guide
4. Open an issue in the repository
