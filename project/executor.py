# executor.py

"""
This file executes allowed actions through Alpaca paper trading.

What it does:
- Reads API keys from environment variables
- Connects to Alpaca paper trading
- Sends a market order only if the action is allowed by ArmorClaw

Before running:
- Set ALPACA_API_KEY
- Set ALPACA_API_SECRET
- Install: pip install alpaca-py python-dotenv
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


# Load variables from `project/.env` (preferred) or CWD `.env`.
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
load_dotenv()

# Never hardcode secrets in code
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET")


def _get_client() -> TradingClient:
    """
    Create an Alpaca TradingClient in paper-trading mode.
    Paper trading is a free sandbox environment.
    """
    if not ALPACA_API_KEY or not ALPACA_API_SECRET:
        raise ValueError("Missing ALPACA_API_KEY or ALPACA_API_SECRET in environment variables.")

    return TradingClient(
        api_key=ALPACA_API_KEY,
        secret_key=ALPACA_API_SECRET,
        paper=True
    )


def execute(action: Dict[str, Any]) -> str:
    """
    Execute an allowed trade.

    Expected action format:
    {
        "action": "buy",
        "symbol": "AAPL",
        "amount": 480,
        "side": "buy",
        "product": "stock",
        "reason": "..."
    }

    Here, 'amount' is treated as notional USD value.
    That means $480 will be sent as a paper trade notional amount.
    """
    symbol = action.get("symbol")
    amount = action.get("amount", 0)
    side = action.get("side", "buy").lower()

    if not symbol:
        return "Execution failed: missing symbol."

    if amount <= 0:
        return "Execution failed: invalid amount."

    client = _get_client()

    order = MarketOrderRequest(
        symbol=symbol,
        notional=amount,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )

    submitted_order = client.submit_order(order_data=order)

    return (
        f"Paper trade submitted successfully: "
        f"{side.upper()} {symbol} for ${amount}. "
        f"Order ID: {submitted_order.id}"
    )