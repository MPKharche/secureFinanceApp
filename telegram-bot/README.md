# Securo Telegram bot (`myPersonalFinanceAgent`)

Binds every Securo MCP function tool (plus a guarded REST fallback) to the Telegram bot **myPersonalFinanceAgent**.

- MCP: `http://127.0.0.1:8765/mcp` (29 tools)
- REST fallback: `securo_http` for `/api/*` (password / 2FA / create-admin blocked)
- India defaults: INR, Asia/Kolkata, DD/MM/YYYY
- Allowlist: Telegram user `613463569`

Secrets: `/root/.credentials/securo-telegram.env` and `/root/.credentials/money.planetfinance.cloud.env`.

```bash
systemctl start securo-telegram.service
/root/apps/secureFinanceApp/telegram-bot/.venv/bin/python -m unittest test_unit.py
```
