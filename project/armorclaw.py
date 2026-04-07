"""
armorclaw.py

ArmorClaw is the enforcement/interceptor layer.
Every action from the agent must pass through this class first.

Its job:
- Read policies from YAML
- Check whether an action is allowed
- Return ALLOW or BLOCK with a reason

This is the core security idea of the project.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, List

import yaml


class ArmorClaw:
    def __init__(self, policy_file: str):
        """
        Load policies from a YAML file.
        """
        with open(policy_file, "r", encoding="utf-8") as f:
            self.policies = yaml.safe_load(f)

        # These values help enforce daily limits and cooldowns.
        self.daily_buy_total = 0
        self.trade_count_today = 0
        self.open_positions = 0
        self.last_buy_time = None

    def _policy_by_id(self, policy_id: str) -> Dict[str, Any] | None:
        """Find one policy by its ID in the YAML list."""
        for p in self.policies.get("policies", []):
            if p.get("id") == policy_id:
                return p
        return None

    def _now_ny(self) -> datetime:
        """Get current time in New York timezone for market hours checks."""
        return datetime.now(ZoneInfo("America/New_York"))

    def check(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if an action is allowed.

        Returns:
            (allowed: bool, reason: str)
        """

        # 1) Reject unknown or empty actions.
        if not action or action.get("action") == "unknown":
            return False, "Unknown or invalid action"

        # 2) Mandatory reason check.
        mandatory_reason = self._policy_by_id("mandatory_reason")
        if mandatory_reason and mandatory_reason.get("require_reason"):
            if not action.get("reason"):
                return False, "Every allowed trade must include a valid reason"

        # 3) Block external API calls / data export.
        no_external = self._policy_by_id("no_external_api_calls")
        if no_external:
            blocked_actions = no_external.get("block_actions", [])
            if action.get("action") in blocked_actions:
                return False, "Do not allow sending portfolio or trade data to external APIs"

        # 4) Only buy/sell if action side is allowed.
        no_short = self._policy_by_id("no_short_selling")
        if no_short:
            allowed_sides = no_short.get("allowed_sides", [])
            if action.get("side") and action.get("side") not in allowed_sides and action.get("action") == "sell":
                return False, "Short selling is not allowed"

        # 5) Block options/margin/leveraged products.
        no_products = self._policy_by_id("no_options_or_margin")
        if no_products:
            blocked_products = no_products.get("blocked_products", [])
            if action.get("product") in blocked_products:
                return False, "Options, margin, and leveraged products are blocked"

        # 6) Only allow approved tickers.
        allowlist = self._policy_by_id("allowlisted_tickers_only")
        if allowlist:
            allowed_tickers = allowlist.get("allowed_tickers", [])
            symbol = action.get("symbol")
            if symbol and symbol not in allowed_tickers:
                return False, "Ticker not allowed"

        # 7) Maximum order value.
        max_order = self._policy_by_id("max_order_value")
        if max_order:
            max_trade_size = max_order.get("max_trade_size_usd", 0)
            if action.get("amount", 0) > max_trade_size:
                return False, f"Trade too large. Max allowed is ${max_trade_size}"

        # 8) Maximum daily buy spend.
        max_daily = self._policy_by_id("max_daily_spend")
        if max_daily and action.get("action") == "buy":
            max_daily_buy = max_daily.get("max_daily_buy_usd", 0)
            if self.daily_buy_total + action.get("amount", 0) > max_daily_buy:
                return False, f"Daily buy limit exceeded. Max allowed is ${max_daily_buy}"

        # 9) Market hours only.
        market_hours = self._policy_by_id("market_hours_only")
        if market_hours:
            window = market_hours.get("allowed_time_window", "")
            current = self._now_ny().time()

            # Expected format: 09:30-16:00 America/New_York
            try:
                time_range = window.split(" ")[0]
                start_str, end_str = time_range.split("-")
                start_h, start_m = map(int, start_str.split(":"))
                end_h, end_m = map(int, end_str.split(":"))
                start_time = time(start_h, start_m)
                end_time = time(end_h, end_m)

                if not (start_time <= current <= end_time):
                    return False, "Trades are allowed only during market hours"
            except Exception:
                # If the time format is wrong, do not crash the app.
                return False, "Invalid market hours policy format"

        # 10) Do not allow selling within 24 hours of buying.
        cooldown = self._policy_by_id("cooldown_after_buy")
        if cooldown and action.get("action") == "sell":
            min_hold = cooldown.get("min_hold_time_hours", 24)
            if self.last_buy_time is not None:
                diff_hours = (self._now_ny() - self.last_buy_time).total_seconds() / 3600
                if diff_hours < min_hold:
                    return False, f"Cannot sell within {min_hold} hours of buying"

        # 11) Max trades per day.
        max_trades = self._policy_by_id("max_trades_per_day")
        if max_trades:
            limit = max_trades.get("max_trades_per_day", 0)
            if self.trade_count_today >= limit:
                return False, f"Maximum trades per day exceeded. Limit is {limit}"

        # 12) Maximum open positions.
        max_positions = self._policy_by_id("max_open_positions")
        if max_positions:
            limit = max_positions.get("max_open_positions", 0)
            if self.open_positions >= limit:
                return False, f"Maximum open positions exceeded. Limit is {limit}"

        # 13) Minimum cash buffer.
        cash_buffer = self._policy_by_id("minimum_cash_buffer")
        if cash_buffer:
            reserve = cash_buffer.get("min_cash_reserve_usd", 0)
            # For demo purposes, this is a static check.
            # Later you can connect it to real account balance.
            fake_cash_balance = 1000
            if fake_cash_balance - action.get("amount", 0) < reserve:
                return False, f"Must keep at least ${reserve} cash unused"

        # If the trade is allowed, update simple counters.
        if action.get("action") == "buy":
            self.daily_buy_total += action.get("amount", 0)
            self.open_positions += 1
            self.trade_count_today += 1
            self.last_buy_time = self._now_ny()

        elif action.get("action") == "sell":
            self.open_positions = max(0, self.open_positions - 1)
            self.trade_count_today += 1

        return True, "Allowed"