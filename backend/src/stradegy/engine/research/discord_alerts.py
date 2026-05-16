import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import GemSignal


class DiscordAlertManager:
    API_BASE = "https://discord.com/api/v10"

    def __init__(self):
        self.token = settings.discord_bot_token
        self.user_id = settings.discord_user_id
        self.general_channel_id = settings.discord_general_channel_id
        self._dm_channel_id: str | None = None
        self._client: httpx.AsyncClient | None = None
        self._last_alert: dict[str, datetime] = {}
        self._last_daily_report: datetime | None = None

        if self.token:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bot {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
            logger.info("Discord alert manager initialized")
        else:
            logger.info("Discord bot token not configured — alert manager disabled")

    def _ensure_client(self) -> bool:
        return self._client is not None

    async def _get_dm_channel(self) -> str | None:
        if self._dm_channel_id:
            return self._dm_channel_id
        if not self._client or not self.user_id:
            return None

        try:
            resp = await self._client.post(
                f"{self.API_BASE}/users/@me/channels",
                json={"recipient_id": self.user_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                self._dm_channel_id = str(data["id"])
                logger.info(f"Discord DM channel created: {self._dm_channel_id}")
                return self._dm_channel_id
            else:
                logger.warning(f"Failed to create DM channel: {resp.status_code} {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error creating DM channel: {e}")
            return None

    async def _send_to_channel(
        self,
        channel_id: str,
        content: str | None = None,
        embed: dict[str, Any] | None = None,
    ) -> bool:
        if not self._ensure_client():
            return False

        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed]

        try:
            resp = await self._client.post(
                f"{self.API_BASE}/channels/{channel_id}/messages",
                json=payload,
            )
            if resp.status_code == 200:
                return True
            elif resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                logger.warning(f"Discord rate limited. Retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._send_to_channel(channel_id, content, embed)
            else:
                logger.warning(f"Discord channel send failed: {resp.status_code} {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Discord channel send error: {e}")
            return False

    async def _send_dm(
        self,
        content: str | None = None,
        embed: dict[str, Any] | None = None,
    ) -> bool:
        channel_id = await self._get_dm_channel()
        if not channel_id:
            return False
        return await self._send_to_channel(channel_id, content, embed)

    def _is_throttled(self, ticker: str) -> bool:
        last = self._last_alert.get(ticker.upper())
        if not last:
            return False
        return datetime.now(timezone.utc) - last < timedelta(hours=2)

    def _gem_color(self, classification: str) -> int:
        return {
            "strong_gem": 0x22C55E,
            "potential_gem": 0xEAB308,
            "watchlist": 0x9CA3AF,
            "discard": 0x6B7280,
        }.get(classification, 0x6B7280)

    def _gem_emoji(self, classification: str) -> str:
        return {
            "strong_gem": "🔥",
            "potential_gem": "💎",
            "watchlist": "👀",
            "discard": "🗑️",
        }.get(classification, "📊")

    def _is_urgent(self, gem: GemSignal) -> bool:
        if gem.total_score >= 85 and gem.source_count >= 3:
            return True
        if gem.total_score >= 80 and gem.source_count >= 4:
            return True
        if gem.reddit_score >= 20 and gem.discord_score >= 15 and gem.news_score >= 15:
            return True
        return False

    async def send_gem_alert(self, gem: GemSignal) -> bool:
        if not self._ensure_client():
            return False

        if self._is_throttled(gem.ticker_symbol):
            logger.info(f"Discord alert throttled for {gem.ticker_symbol}")
            return False

        embed = {
            "title": f"{self._gem_emoji(gem.classification.value)} Stradegy Gem Alert",
            "description": (
                f"**${gem.ticker_symbol}** — {gem.classification.value.replace('_', ' ').title()}\n"
                f"Score: **{gem.total_score:.0f}/100** | Sources: {gem.source_count}"
            ),
            "color": self._gem_color(gem.classification.value),
            "fields": [
                {"name": "Reddit", "value": f"{gem.reddit_score:.1f}/25", "inline": True},
                {"name": "Discord", "value": f"{gem.discord_score:.1f}/25", "inline": True},
                {"name": "SEC", "value": f"{gem.sec_score:.1f}/30", "inline": True},
                {"name": "News", "value": f"{gem.news_score:.1f}/20", "inline": True},
                {"name": "Technical", "value": f"{gem.technical_score:.1f}/25", "inline": True},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Stradegy Trading Bot"},
        }

        if gem.evidence_urls:
            embed["fields"].append(
                {"name": "Evidence", "value": "\n".join(gem.evidence_urls[:3]), "inline": False}
            )

        is_urgent = self._is_urgent(gem)
        success = False

        if is_urgent:
            success = await self._send_dm(embed=embed)
            if success:
                logger.info(f"URGENT gem DM sent for {gem.ticker_symbol} (score: {gem.total_score})")
        elif self.general_channel_id:
            success = await self._send_to_channel(self.general_channel_id, embed=embed)
            if success:
                logger.info(f"Gem posted to #general for {gem.ticker_symbol}")
        else:
            success = await self._send_dm(embed=embed)
            if success:
                logger.info(f"Gem DM sent for {gem.ticker_symbol}")

        if success:
            self._last_alert[gem.ticker_symbol.upper()] = datetime.now(timezone.utc)
        return success

    async def send_trade_notification(self, trade: dict[str, Any]) -> bool:
        if not self._ensure_client():
            return False

        side = trade.get("side", "").lower()
        symbol = trade.get("symbol", "")
        qty = trade.get("qty", 0)
        price = trade.get("price", 0.0)
        total = trade.get("total", 0.0)

        emoji = "🟢" if side == "buy" else "🔴"
        action = "BOUGHT" if side == "buy" else "SOLD"
        color = 0x22C55E if side == "buy" else 0xEF4444

        embed = {
            "title": f"{emoji} Trade Executed — {action}",
            "description": f"**${symbol}**",
            "color": color,
            "fields": [
                {"name": "Quantity", "value": str(qty), "inline": True},
                {"name": "Price", "value": f"${price:.2f}", "inline": True},
                {"name": "Total", "value": f"${total:,.2f}", "inline": True},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Stradegy Trading Bot"},
        }

        success = False
        if self.general_channel_id:
            success = await self._send_to_channel(self.general_channel_id, embed=embed)
        if not success:
            success = await self._send_dm(embed=embed)

        if success:
            logger.info(f"Trade notification sent for {symbol}")
        return success

    async def send_risk_alert(self, data: dict[str, Any]) -> bool:
        if not self._ensure_client():
            return False

        emergencies = data.get("emergencies", [])
        drawdown = data.get("drawdown_status", {})
        pdt = data.get("pdt_status", {})

        if not emergencies:
            return False

        color = 0xEF4444
        description = "\n".join(f"• {e}" for e in emergencies)

        fields = []
        if drawdown:
            fields.append({
                "name": "Drawdown",
                "value": f"{drawdown.get('drawdown', 0):.1%} / limit {drawdown.get('limit', 0):.0%}",
                "inline": True,
            })
        if pdt:
            fields.append({
                "name": "PDT Count",
                "value": f"{pdt.get('pdt_count', 0)} / {pdt.get('pdt_limit', 3)}",
                "inline": True,
            })

        embed = {
            "title": "🚨 Risk Alert — Trading Halted",
            "description": description,
            "color": color,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Stradegy Trading Bot — Manual intervention may be required"},
        }

        success = await self._send_dm(embed=embed)
        if success:
            logger.info("Risk alert DM sent")
        return success

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
