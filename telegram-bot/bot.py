#!/usr/bin/env python3
"""Telegram bot: bind Securo MCP function tools + REST fallback to myPersonalFinanceAgent."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import httpx
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from client import SYSTEM_PROMPT, SecuroClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("securo-telegram")

ENV_FILES = [
    Path("/root/.credentials/securo-telegram.env"),
    Path("/root/.credentials/money.planetfinance.cloud.env"),
]


def load_env() -> dict[str, str]:
    # Credential files win over ambient process env (Hermes/cc-vibe URLs).
    out: dict[str, str] = {k: v for k, v in os.environ.items() if v}
    for path in ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip('"').strip("'")
            if val:
                out[key] = val
    return out


def allowed_ids(raw: str) -> set[str]:
    return {p.strip() for p in (raw or "").split(",") if p.strip()}


class AgentLoop:
    def __init__(self, env: dict[str, str], securo: SecuroClient):
        self.securo = securo
        self.model = env.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
        self.api_key = env["OPENROUTER_API_KEY"]
        self.base = (
            env.get("OPENROUTER_BASE_URL")
            or env.get("OPENROUTER_API_BASE")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.max_turns = int(env.get("LLM_MAX_TURNS", "8"))

    def complete(self, messages: list[dict]) -> dict:
        tools = self.securo.openai_tools()
        with httpx.Client(timeout=90.0) as client:
            r = client.post(
                f"{self.base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://money.planetfinance.cloud",
                    "X-Title": "myPersonalFinanceAgent",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.2,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]

    def run(self, user_text: str) -> str:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
        for _ in range(self.max_turns):
            msg = self.complete(messages)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return (msg.get("content") or "").strip() or "(empty reply)"
            messages.append(msg)
            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name") or ""
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}
                try:
                    result = self.securo.dispatch_tool(name, args if isinstance(args, dict) else {})
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id") or name,
                        "name": name,
                        "content": json.dumps(result, default=str)[:24000],
                    }
                )
        return "I hit the tool-call limit. Ask me to continue with a narrower question."


def split_telegram(text: str, limit: int = 3900) -> list[str]:
    text = text.strip() or "(no content)"
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


def is_allowed(update: Update, allow: set[str]) -> bool:
    if not allow:
        return False
    user = update.effective_user
    chat = update.effective_chat
    uid = str(user.id) if user else ""
    cid = str(chat.id) if chat else ""
    return uid in allow or cid in allow


HELP = (
    "myPersonalFinanceAgent — Securo on https://money.planetfinance.cloud\n\n"
    "Talk in plain English (or Hinglish). I can list accounts, log expenses, "
    "check budgets, goals, bills, payees, and the rest of the money API.\n\n"
    "India defaults: INR, IST, DD/MM/YYYY.\n"
    "Writes are previewed first; say yes to apply."
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update, context.application.bot_data["allow"]):
        return
    await update.message.reply_text(HELP)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if not is_allowed(update, context.application.bot_data["allow"]):
        await update.message.reply_text("Not authorized.")
        return
    agent: AgentLoop = context.application.bot_data["agent"]
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        reply = agent.run(update.message.text)
    except Exception:
        log.exception("agent loop failed")
        reply = "Something went wrong talking to Securo. Try again in a moment."
    for chunk in split_telegram(reply):
        await update.message.reply_text(chunk)


def main() -> int:
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_FINANCE_BOT_TOKEN")
    if not token:
        log.error("TELEGRAM_BOT_TOKEN missing in /root/.credentials/securo-telegram.env")
        return 1
    allow = allowed_ids(env.get("TELEGRAM_ALLOWED_CHAT_IDS", "613463569"))
    securo = SecuroClient(
        mcp_url=env.get("SECURO_MCP_URL", "http://127.0.0.1:8765/mcp"),
        mcp_token=env["SECURO_MCP_TOKEN"],
        api_base=env.get("SECURO_API_BASE", "https://money.planetfinance.cloud"),
        api_email=env.get("EMAIL") or env.get("SECURO_EMAIL", ""),
        api_password=env.get("PASSWORD") or env.get("SECURO_PASSWORD", ""),
        workspace_id=env.get("SECURO_WORKSPACE_ID", ""),
    )
    # Fail fast if MCP is down
    tools = securo.list_mcp_tools()
    log.info("MCP tools loaded: %s", len(tools))
    agent = AgentLoop(env, securo)
    app = Application.builder().token(token).build()
    app.bot_data["allow"] = allow
    app.bot_data["agent"] = agent
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("polling Telegram as myPersonalFinanceAgent")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
