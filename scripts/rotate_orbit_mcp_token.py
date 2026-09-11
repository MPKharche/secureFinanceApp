#!/usr/bin/env python3
"""Rotate Finance Orbit's MCP JWT with overlap so Telegram keeps working.

1. Mint a new revocable token inside securo-backend (persisted).
2. Write it into Orbit's env files (never prints the secret).
3. Restart hermes-gateway-securo so the bot picks it up.
4. After Telegram is online, denylist the previous JWT.

Run on the VPS as root after backend+mcp-server are rebuilt.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKEND = os.environ.get("SECURO_BACKEND_CONTAINER", "securo-backend-1")
ORBIT_ENV = Path("/root/apps/hermes-agent/data/profiles/securo/.env")
CRED_ENV = Path("/root/.credentials/securo-telegram.env")
GATEWAY_LOG = Path("/root/apps/hermes-agent/data/profiles/securo/logs/gateway.log")
SERVICE = "hermes-gateway-securo.service"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def _upsert_env(path: Path, key: str, value: str) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    out: list[str] = []
    found = False
    for raw in lines:
        if raw.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(raw)
    if not found:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip() + "\n")
    path.chmod(0o600)


def _read_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for raw in path.read_text().splitlines():
        if raw.startswith(f"{key}="):
            return raw.split("=", 1)[1]
    return ""


def _mint_new_token() -> str:
    script = (
        "import asyncio, pathlib\n"
        "from uuid import UUID\n"
        "from app.agents.config import get_agent_settings\n"
        "from app.agents.services.mcp_token_store import issue_external_token\n"
        "from app.core.database import async_session_maker\n"
        "USER=UUID('a5a07637-b817-43d6-a923-f5cddfbc63d0')\n"
        "WS=UUID('a9181332-25cb-4b18-a9e1-489eb71ec6c2')\n"
        "async def go():\n"
        "    s=get_agent_settings()\n"
        "    async with async_session_maker() as session:\n"
        "        token, row = await issue_external_token(session, user_id=USER, workspace_id=WS, ttl_seconds=max(s.mcp_external_ttl_days,1)*86400, label='Finance Orbit')\n"
        "    p=pathlib.Path('/tmp/orbit-mcp-new.jwt')\n"
        "    p.write_text(token)\n"
        "    p.chmod(0o600)\n"
        "    print(str(row.id))\n"
        "asyncio.run(go())\n"
    )
    result = _run(
        ["docker", "exec", "-i", BACKEND, "python", "-c", script],
        capture_output=True,
        text=True,
    )
    token_id = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    dest = Path(tempfile.mkstemp(prefix="orbit-mcp-", suffix=".jwt")[1])
    dest.chmod(0o600)
    _run(["docker", "cp", f"{BACKEND}:/tmp/orbit-mcp-new.jwt", str(dest)])
    _run(["docker", "exec", BACKEND, "rm", "-f", "/tmp/orbit-mcp-new.jwt"])
    token = dest.read_text().strip()
    dest.unlink(missing_ok=True)
    if not token.startswith("eyJ"):
        raise SystemExit("mint failed: token missing from container")
    print(f"minted token id={token_id or 'unknown'}", flush=True)
    return token


def _denylist_old(old_token: str) -> None:
    if not old_token.startswith("eyJ"):
        return
    src = Path(tempfile.mkstemp(prefix="orbit-mcp-old-", suffix=".jwt")[1])
    src.write_text(old_token)
    src.chmod(0o600)
    _run(["docker", "cp", str(src), f"{BACKEND}:/tmp/orbit-mcp-old.jwt"])
    src.unlink(missing_ok=True)
    script = (
        "import asyncio, pathlib\n"
        "from app.agents.services.mcp_token_store import denylist_raw_token\n"
        "from app.core.database import async_session_maker\n"
        "async def go():\n"
        "    token=pathlib.Path('/tmp/orbit-mcp-old.jwt').read_text().strip()\n"
        "    async with async_session_maker() as session:\n"
        "        await denylist_raw_token(session, token, reason='orbit_rotation')\n"
        "asyncio.run(go())\n"
    )
    _run(["docker", "exec", "-i", BACKEND, "python", "-c", script], capture_output=True, text=True)
    _run(["docker", "exec", BACKEND, "rm", "-f", "/tmp/orbit-mcp-old.jwt"])


def _wait_telegram(timeout: int = 45) -> None:
    start = time.time()
    marker = "✓ telegram connected"
    while time.time() - start < timeout:
        if GATEWAY_LOG.exists():
            tail = GATEWAY_LOG.read_text(errors="replace")[-4000:]
            if marker in tail and "Finance Orbit online" in tail:
                return
        time.sleep(1)
    # Don't fail the rotate if log phrasing changed; systemd active is enough.
    status = subprocess.run(["systemctl", "is-active", SERVICE], capture_output=True, text=True)
    if status.stdout.strip() != "active":
        raise SystemExit("Orbit gateway did not come back active")


def main() -> int:
    old = _read_env_value(ORBIT_ENV, "SECURO_MCP_TOKEN")
    print("minting replacement MCP token inside backend…", flush=True)
    new = _mint_new_token()
    print("writing env (Orbit + credentials)…", flush=True)
    _upsert_env(ORBIT_ENV, "SECURO_MCP_TOKEN", new)
    if CRED_ENV.exists():
        _upsert_env(CRED_ENV, "SECURO_MCP_TOKEN", new)
    print("restarting Finance Orbit…", flush=True)
    _run(["systemctl", "restart", SERVICE])
    _wait_telegram()
    print("denylisting previous MCP token…", flush=True)
    _denylist_old(old)
    print("handoff complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
