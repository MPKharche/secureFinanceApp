"""Securo MCP (function tools) + REST fallback for the Telegram bot."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

BLOCKED_REST_PREFIXES = (
    "/api/auth/2fa",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/auth/request-verify",
    "/api/setup/create-admin",
)
BLOCKED_BODY_KEYS = {"password", "hashed_password", "totp_secret", "new_password"}

REST_TOOL = {
    "type": "function",
    "function": {
        "name": "securo_http",
        "description": (
            "Call any Securo HTTP API under /api/ when an MCP tool is not enough "
            "(assets create/update, connections, import, goals write, admin settings, "
            "workspaces, categories write, etc.). Prefer named MCP tools for reads "
            "and propose_* tools for money mutations. Amounts must be decimal strings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST", "PATCH", "PUT", "DELETE"]},
                "path": {
                    "type": "string",
                    "description": "Path starting with /api/, e.g. /api/accounts",
                },
                "query": {"type": "object", "additionalProperties": True},
                "body": {"type": "object", "additionalProperties": True},
            },
            "required": ["method", "path"],
            "additionalProperties": False,
        },
    },
}


def mcp_tools_to_openai(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for tool in mcp_tools:
        name = tool.get("name")
        if not name:
            continue
        params = tool.get("inputSchema") or tool.get("parameters") or {"type": "object", "properties": {}}
        desc = tool.get("description") or name
        extra = tool.get("_securo") or {}
        if extra.get("is_proposal"):
            desc = (
                desc
                + " This is a proposal tool: first call with apply=false (preview). "
                "Only set apply=true after the user confirms in Telegram."
            )
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc[:1024],
                    "parameters": params,
                },
            }
        )
    out.append(REST_TOOL)
    return out


def assert_rest_allowed(method: str, path: str, body: dict | None) -> None:
    method = (method or "").upper()
    if method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
        raise ValueError(f"method not allowed: {method}")
    if not path.startswith("/api/"):
        raise ValueError("path must start with /api/")
    if ".." in path:
        raise ValueError("invalid path")
    lowered = path.lower()
    for prefix in BLOCKED_REST_PREFIXES:
        if lowered.startswith(prefix):
            raise ValueError(f"blocked path: {prefix}")
    if body:
        for key in body:
            if str(key).lower() in BLOCKED_BODY_KEYS:
                raise ValueError(f"blocked body field: {key}")


class SecuroClient:
    def __init__(
        self,
        *,
        mcp_url: str,
        mcp_token: str,
        api_base: str,
        api_email: str,
        api_password: str,
        workspace_id: str,
        timeout: float = 30.0,
    ):
        self.mcp_url = mcp_url
        self.mcp_token = mcp_token
        self.api_base = api_base.rstrip("/")
        self.api_email = api_email
        self.api_password = api_password
        self.workspace_id = workspace_id
        self.timeout = timeout
        self._api_token: str | None = None
        self._mcp_tools: list[dict[str, Any]] | None = None

    def _mcp_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.mcp_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def mcp_rpc(self, method: str, params: dict | None = None, req_id: int = 1) -> Any:
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(self.mcp_url, headers=self._mcp_headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

    def list_mcp_tools(self) -> list[dict[str, Any]]:
        if self._mcp_tools is None:
            result = self.mcp_rpc("tools/list")
            self._mcp_tools = result.get("tools") or []
        return self._mcp_tools

    def openai_tools(self) -> list[dict[str, Any]]:
        return mcp_tools_to_openai(self.list_mcp_tools())

    def call_mcp(self, name: str, arguments: dict[str, Any]) -> Any:
        result = self.mcp_rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if isinstance(result, dict) and "structuredContent" in result:
            return result["structuredContent"]
        return result

    def _login(self) -> str:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.api_base}/api/auth/login",
                data={"username": self.api_email, "password": self.api_password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            r.raise_for_status()
            token = r.json().get("access_token")
        if not token:
            raise RuntimeError("login did not return access_token")
        self._api_token = token
        return token

    def _api_headers(self) -> dict[str, str]:
        token = self._api_token or self._login()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-Workspace-Id": self.workspace_id,
        }
        return headers

    def call_rest(self, method: str, path: str, query: dict | None = None, body: dict | None = None) -> Any:
        assert_rest_allowed(method, path, body)
        url = urljoin(self.api_base + "/", path.lstrip("/"))
        headers = self._api_headers()
        json_body = body if method.upper() != "GET" else None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.request(method.upper(), url, params=query or None, json=json_body, headers=headers)
            if r.status_code == 401:
                self._api_token = None
                headers = self._api_headers()
                if json_body is not None:
                    headers["Content-Type"] = "application/json"
                r = client.request(method.upper(), url, params=query or None, json=json_body, headers=headers)
        try:
            parsed = r.json()
        except Exception:
            parsed = {"text": r.text[:4000]}
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "error": parsed}
        return {"ok": True, "status": r.status_code, "data": parsed}

    def dispatch_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "securo_http":
            return self.call_rest(
                arguments.get("method", "GET"),
                arguments.get("path", ""),
                arguments.get("query"),
                arguments.get("body"),
            )
        return self.call_mcp(name, arguments)


SYSTEM_PROMPT = """You are myPersonalFinanceAgent, the Telegram interface to Securo (https://money.planetfinance.cloud) for MP Kharche in India.

Rules:
- Always use tools for live balances, transactions, budgets, accounts, goals, assets. Never invent numbers.
- Default currency INR, timezone Asia/Kolkata, dates DD/MM/YYYY, Indian grouping (₹1,23,456.78).
- Tax jurisdiction is India (GSTIN/PAN). UI language English.
- Prefer MCP tools (list_*, get_*, aggregate, search_all, propose_*). Use securo_http only when no MCP tool covers the request.
- For propose_* tools: first call with apply=false, show the preview, ask the user to confirm. Only then call again with apply=true.
- Money values from tools are authoritative; quote them as returned. Do not recompute with floating point.
- Keep replies short for Telegram. Use INR and IST. If a write is preview-only, say so clearly.
- You may only act on this user's Personal workspace. Refuse requests that would change passwords, 2FA, or create another admin.
"""
