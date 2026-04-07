"""
server.py

FastAPI backend that exposes the ArmorClaw enforcement engine.
The frontend sends commands here; the server runs Agent → ArmorClaw → Executor.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime

from .agent import agent_loop
from .armorclaw import ArmorClaw
from .executor import execute

app = FastAPI(title="ArmorClaw API", version="1.0.0")

FRONTEND_DIR = Path(__file__).parent / "frontend"
POLICY_FILE = Path(__file__).parent / "policies.yaml"

# Allow the frontend dev server to connect.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single ArmorClaw instance — keeps state (daily totals, counters) in memory.
armor = ArmorClaw(str(POLICY_FILE))

# In-memory action log for the dashboard.
action_log: list[dict] = []


class CommandRequest(BaseModel):
    command: str


class PolicyInfo(BaseModel):
    id: str
    rule: str


@app.post("/api/command")
def process_command(req: CommandRequest):
    """
    Receive a natural-language command, run it through
    Agent → ArmorClaw → Executor pipeline, and return the result.
    """
    user_input = req.command

    # 1. Agent parses intent.
    decision = agent_loop(user_input)

    # 2. ArmorClaw enforces policy.
    allowed, reason = armor.check(decision)

    # 3. Execute if allowed.
    execution_result = None
    if allowed:
        try:
            execution_result = execute(decision)
        except Exception as e:
            # Avoid crashing the API for configuration/runtime issues (e.g. missing env vars).
            execution_result = f"Execution failed: {e}"

    # 4. Build log entry.
    entry = {
        "id": len(action_log) + 1,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "command": user_input,
        "action": decision.get("action", "unknown"),
        "symbol": decision.get("symbol"),
        "amount": decision.get("amount", 0),
        "side": decision.get("side"),
        "product": decision.get("product"),
        "reason": reason,
        "allowed": allowed,
        "policy_status": "Verified" if allowed else "Denied",
        "execution_result": execution_result,
        "decision": decision,
    }
    action_log.append(entry)

    return entry


@app.get("/api/logs")
def get_logs():
    """Return all action logs (newest first)."""
    return list(reversed(action_log))


@app.get("/api/policies")
def get_policies():
    """Return all loaded policies."""
    policies = armor.policies.get("policies", [])
    return [{"id": p.get("id"), "rule": p.get("rule"), **p} for p in policies]


@app.get("/api/stats")
def get_stats():
    """Return live dashboard stats."""
    total = len(action_log)
    allowed_count = sum(1 for e in action_log if e["allowed"])
    blocked_count = total - allowed_count

    return {
        "total_actions": total,
        "allowed": allowed_count,
        "blocked": blocked_count,
        "daily_buy_total": armor.daily_buy_total,
        "trade_count_today": armor.trade_count_today,
        "open_positions": armor.open_positions,
        "block_rate": round(blocked_count / total * 100, 1) if total > 0 else 0,
    }


@app.post("/api/reset")
def reset_state():
    """Reset all counters and logs."""
    global action_log
    action_log.clear()
    armor.daily_buy_total = 0
    armor.trade_count_today = 0
    armor.open_positions = 0
    armor.last_buy_time = None
    return {"status": "reset"}


# ── Serve Frontend ──
@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


# Mount static files LAST so /api routes take priority.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
