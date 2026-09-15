# MCP Proxy Server

Reliability layer between Hermes and Securo MCP for guaranteed transaction sync.

## Features

- Automatic `apply=true` injection
- Persistent retry queue (2 attempts: 15s, 30s)
- Circuit breaker pattern
- Idempotency for duplicate detection
- Write-ahead log for disaster recovery
- Checkpoint API for crash recovery
- Prometheus metrics
- Telegram alerts on failures

## Installation

```bash
# Create virtual environment
cd /root/apps/secureFinanceApp/mcp-proxy
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
docker exec securo-db-1 psql -U postgres -d securo < migrations/001_add_sync_tables.sql

# Configure environment
cp .env.example .env
vim .env  # Add your credentials

# Install systemd service
sudo cp systemd/mcp-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-proxy.service
sudo systemctl start mcp-proxy.service
```

## Configuration

Edit `.env` file with your settings. Required variables:

- `SECURO_MCP_TOKEN` - From `/root/apps/hermes-agent/data/profiles/securo/.env`
- `TELEGRAM_BOT_TOKEN` - From same file
- `TELEGRAM_ALERT_CHAT_ID` - Your Telegram chat ID (613463569)

## Deployment

See design spec: `/root/system/docs/2026-09-16-telegram-sync-reliability-design.md`

**Phase 1:** Deploy proxy (no traffic)
**Phase 2:** Switch Hermes to proxy (port 8766)
**Phase 3:** Enable checkpoints

## Monitoring

```bash
# Health check
curl http://127.0.0.1:8766/health | jq

# Prometheus metrics
curl http://127.0.0.1:8766/metrics

# System logs
sudo journalctl -u mcp-proxy.service -f

# Check sync status
bash /root/system/scripts/check-telegram-sync.sh
```

## Troubleshooting

**Proxy won't start:**
- Check `.env` file has all required variables
- Verify database is accessible
- Check logs: `sudo journalctl -u mcp-proxy.service -n 50`

**Transactions not syncing:**
- Check circuit breaker state: `curl http://127.0.0.1:8766/health | jq .circuit_breaker_state`
- Check pending queue: Query `pending_transactions` table
- Verify Hermes is pointing to port 8766

**Circuit breaker opened:**
- Check Securo backend: `docker ps | grep securo-backend`
- Restart backend if needed: `docker restart securo-backend-1`
- Circuit auto-recovers after 60 seconds

## API Endpoints

- `POST /mcp` - Proxy MCP calls
- `POST /checkpoint` - Save Hermes checkpoint
- `GET /health` - Health check with stats
- `GET /metrics` - Prometheus metrics
