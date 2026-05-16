import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings


class DiscordReporter:
    API_BASE = "https://discord.com/api/v10"

    def __init__(self):
        self.token = settings.discord_bot_token
        self.channel_id = settings.discord_general_channel_id
        self._client: httpx.AsyncClient | None = None

        if self.token and self.channel_id:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bot {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
            logger.info("Discord reporter initialized")
        else:
            logger.info("Discord reporter disabled — missing token or channel ID")

    def _ensure_client(self) -> bool:
        return self._client is not None

    async def _send_to_channel(
        self,
        content: str | None = None,
        embed: dict[str, Any] | None = None,
    ) -> bool:
        if not self._ensure_client() or not self.channel_id:
            return False

        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed]

        try:
            resp = await self._client.post(
                f"{self.API_BASE}/channels/{self.channel_id}/messages",
                json=payload,
            )
            if resp.status_code == 200:
                return True
            elif resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                await asyncio.sleep(retry_after)
                return await self._send_to_channel(content, embed)
            else:
                logger.warning(f"Discord report failed: {resp.status_code} {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Discord report error: {e}")
            return False

    async def send_daily_report(self, data: dict[str, Any]) -> bool:
        equity = data.get("equity", 0.0)
        day_pnl = data.get("day_pnl", 0.0)
        day_pnl_pct = data.get("day_pnl_pct", 0.0)
        open_positions = data.get("open_positions", 0)
        positions = data.get("positions", [])
        gems_found = data.get("gems_found", 0)
        mode = data.get("mode", "paper")

        is_profit = day_pnl >= 0
        color = 0x22C55E if is_profit else 0xEF4444
        pnl_sign = "+" if is_profit else ""
        emoji = "📈" if is_profit else "📉"

        fields = [
            {"name": "Portfolio Value", "value": f"${equity:,.2f}", "inline": True},
            {"name": "Day P&L", "value": f"{pnl_sign}${day_pnl:,.2f} ({pnl_sign}{day_pnl_pct:.2f}%)", "inline": True},
            {"name": "Open Positions", "value": str(open_positions), "inline": True},
            {"name": "Gems Found Today", "value": str(gems_found), "inline": True},
        ]

        if positions:
            pos_lines = []
            for pos in positions[:5]:
                pnl = pos.get("pnl", 0)
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                pos_lines.append(
                    f"{pnl_emoji} **{pos['symbol']}**: {pos['qty']} shares | "
                    f"P&L: {pnl_emoji}${pnl:,.2f} ({(pos.get('unrealized_plpc', 0) * 100):.1f}%)"
                )
            fields.append({"name": "Positions", "value": "\n".join(pos_lines), "inline": False})

        strategy_insights = data.get("strategy_insights", [])
        if strategy_insights:
            fields.append({
                "name": "Strategy Insights",
                "value": "\n".join(f"• {s}" for s in strategy_insights[:3]),
                "inline": False,
            })

        embed = {
            "title": f"{emoji} Daily Report — {datetime.now(timezone.utc).strftime('%A, %B %d')}",
            "color": color,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": f"Stradegy | {mode.upper()} Mode | End of Day Summary"},
        }

        success = await self._send_to_channel(embed=embed)
        if success:
            logger.info("Daily report posted to Discord #general")
        return success

    async def send_monthly_report(self, data: dict[str, Any]) -> bool:
        month_name = datetime.now(timezone.utc).strftime("%B %Y")
        total_return = data.get("total_return", 0.0)
        sharpe = data.get("sharpe", 0.0)
        max_dd = data.get("max_drawdown", 0.0)
        win_rate = data.get("win_rate", 0.0)
        total_trades = data.get("total_trades", 0)
        best_performer = data.get("best_performer", "N/A")
        worst_performer = data.get("worst_performer", "N/A")
        adjustments = data.get("adjustments", [])

        is_profit = total_return >= 0
        color = 0x22C55E if is_profit else 0xEF4444
        sign = "+" if is_profit else ""

        fields = [
            {"name": "Monthly Return", "value": f"{sign}{total_return:.2f}%", "inline": True},
            {"name": "Sharpe Ratio", "value": f"{sharpe:.2f}", "inline": True},
            {"name": "Max Drawdown", "value": f"{max_dd:.1%}", "inline": True},
            {"name": "Win Rate", "value": f"{win_rate:.1%}", "inline": True},
            {"name": "Total Trades", "value": str(total_trades), "inline": True},
            {"name": "Best Trade", "value": best_performer, "inline": True},
            {"name": "Worst Trade", "value": worst_performer, "inline": True},
        ]

        if adjustments:
            fields.append({
                "name": "Strategy Adjustments",
                "value": "\n".join(f"• {a}" for a in adjustments[:5]),
                "inline": False,
            })

        embed = {
            "title": f"📊 Monthly Review — {month_name}",
            "description": (
                "**Performance Summary**\n"
                f"This month the portfolio returned **{sign}{total_return:.2f}%** with a Sharpe of {sharpe:.2f}.\n"
                f"Risk was well-managed with a max drawdown of {max_dd:.1%}."
            ),
            "color": color,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Stradegy | Monthly Strategy Review"},
        }

        success = await self._send_to_channel(embed=embed)
        if success:
            logger.info("Monthly report posted to Discord #general")
        return success

    async def send_quarterly_report(self, data: dict[str, Any]) -> bool:
        quarter = (datetime.now(timezone.utc).month - 1) // 3 + 1
        year = datetime.now(timezone.utc).year
        total_return = data.get("total_return", 0.0)
        annualized_return = data.get("annualized_return", 0.0)
        sharpe = data.get("sharpe", 0.0)
        max_dd = data.get("max_drawdown", 0.0)
        win_rate = data.get("win_rate", 0.0)
        strategy_changes = data.get("strategy_changes", [])
        midterm_goals = data.get("midterm_goals", [])

        is_profit = total_return >= 0
        color = 0x3B82F6
        sign = "+" if is_profit else ""

        fields = [
            {"name": "Quarterly Return", "value": f"{sign}{total_return:.2f}%", "inline": True},
            {"name": "Annualized", "value": f"{sign}{annualized_return:.2f}%", "inline": True},
            {"name": "Sharpe Ratio", "value": f"{sharpe:.2f}", "inline": True},
            {"name": "Max Drawdown", "value": f"{max_dd:.1%}", "inline": True},
            {"name": "Win Rate", "value": f"{win_rate:.1%}", "inline": True},
        ]

        if strategy_changes:
            fields.append({
                "name": "Strategy Changes",
                "value": "\n".join(f"• {s}" for s in strategy_changes[:5]),
                "inline": False,
            })

        if midterm_goals:
            fields.append({
                "name": "Mid-Term Goals",
                "value": "\n".join(f"• {g}" for g in midterm_goals[:5]),
                "inline": False,
            })

        embed = {
            "title": f"🎯 Q{quarter} {year} — Quarterly Strategy Review",
            "description": (
                "**Long-term Strategy Adjustment**\n"
                f"Q{quarter} returned **{sign}{total_return:.2f}%**. Based on this performance, "
                "the following adjustments are recommended to optimize the strategy for the next quarter."
            ),
            "color": color,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Stradegy | Quarterly Strategy Review & Adjustment"},
        }

        success = await self._send_to_channel(embed=embed)
        if success:
            logger.info("Quarterly report posted to Discord #general")
        return success

    async def send_moonshot_alert(self, gem_data: dict[str, Any]) -> bool:
        if not self._ensure_client():
            return False

        ticker = gem_data.get("ticker", "")
        score = gem_data.get("score", 0)
        classification = gem_data.get("classification", "")
        catalyst = gem_data.get("catalyst", "")
        urgency = gem_data.get("urgency", "high")

        color = 0x8B5CF6 if urgency == "critical" else 0xEAB308
        emoji = "🚀" if urgency == "critical" else "⭐"

        embed = {
            "title": f"{emoji} MOONSHOT ALERT — ${ticker}",
            "description": (
                f"**URGENT:** {catalyst}\n\n"
                f"This is a high-conviction opportunity requiring immediate attention.\n"
                f"Score: **{score}/100** | Classification: **{classification}**"
            ),
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Stradegy | Moonshot Alert — Act Within 4 Hours"},
        }

        success = await self._send_to_channel(embed=embed)
        if success:
            logger.info(f"Moonshot alert posted to #general for {ticker}")
        return success

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
