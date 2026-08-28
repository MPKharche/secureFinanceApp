# Telegram poller (retired)

The live bot is **Hermes profile `securo`**: `hermes-gateway-securo.service` → `@myPersonal_FinanceBot`.

This directory is the old Python MCP wrapper (`securo-telegram.service`). It is **disabled**. Do not start it while the Hermes gateway is polling the same BotFather token.

Rollback (emergency only):

```bash
systemctl stop hermes-gateway-securo.service
systemctl start securo-telegram.service
```
