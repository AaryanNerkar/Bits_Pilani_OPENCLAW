"""
executor.py

This file executes the allowed action.
For now, we simulate execution.
Later, you can replace this with Alpaca paper trading API.
"""

from typing import Dict, Any


def execute(action: Dict[str, Any]) -> str:
    """
    Simulate trade execution.

    Later, this function can be changed to call:
    - Alpaca paper trading API
    - TradeStation SIM
    - Another broker API
    """

    return (
        f"Executed {action['action']} for {action.get('symbol', 'N/A')} "
        f"worth ${action.get('amount', 0)}"
    )