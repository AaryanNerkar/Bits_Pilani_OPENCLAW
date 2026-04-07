# agent.py

import re
from typing import Dict, Any, Optional


DEFAULT_SYMBOL = "AAPL"
DEFAULT_AMOUNT = 300


def extract_symbol(text: str) -> str:
    """
    Try to detect a stock symbol from the user input.
    If none is found, return a default symbol.
    """
    symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA"]

    for symbol in symbols:
        if symbol.lower() in text:
            return symbol

    return DEFAULT_SYMBOL


def extract_amount(text: str) -> int:
    """
    Try to extract a number from the input.
    Example:
        'buy aapl for 450' -> 450
    If no number is found, return a default amount.
    """
    match = re.search(r"\b(\d+)\b", text)
    if match:
        return int(match.group(1))

    return DEFAULT_AMOUNT


def detect_action(text: str) -> str:
    """
    Detect the main intent from the user command.
    """
    if any(word in text for word in ["buy", "purchase", "invest"]):
        return "buy"

    if any(word in text for word in ["sell", "exit", "close"]):
        return "sell"

    if any(word in text for word in ["send data", "export", "share", "api", "webhook"]):
        return "external_api_call"

    return "unknown"


def agent_loop(user_input: str) -> Dict[str, Any]:
    """
    Convert raw user text into a structured decision object.

    This is the agent's job:
    1. understand the request
    2. decide the action
    3. send a structured output to ArmorClaw
    """
    text = user_input.lower().strip()

    action = detect_action(text)

    # Dummy research data for now.
    # Later you can replace this with:
    # - market data
    # - price trends
    # - news
    # - risk analysis
    market_snapshot = {
        "price": 150,
        "trend": "neutral",
        "volatility": "medium"
    }

    # Build a structured decision.
    decision = {
        "action": action,
        "symbol": None,
        "amount": 0,
        "side": None,
        "product": None,
        "reason": None,
        "market_snapshot": market_snapshot
    }

    if action == "buy":
        symbol = extract_symbol(text)
        amount = extract_amount(text)

        decision.update({
            "symbol": symbol,
            "amount": amount,
            "side": "buy",
            "product": "stock",
            "reason": f"User requested to buy {symbol}"
        })

    elif action == "sell":
        symbol = extract_symbol(text)
        amount = extract_amount(text)

        decision.update({
            "symbol": symbol,
            "amount": amount,
            "side": "sell",
            "product": "stock",
            "reason": f"User requested to sell {symbol}"
        })

    elif action == "external_api_call":
        decision.update({
            "reason": "User requested data sharing or external API action"
        })

    else:
        decision.update({
            "reason": "Could not understand the user request"
        })

    return decision