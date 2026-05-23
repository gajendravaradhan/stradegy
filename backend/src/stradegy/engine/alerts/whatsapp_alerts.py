from __future__ import annotations
import requests
from datetime import datetime
from loguru import logger

from stradegy.config import settings


class WhatsAppAlertManager:
    BASE_URL = "https://api.callmebot.com/whatsapp.php"

    def __init__(self):
        self.phone = settings.whatsapp_phone_number
        self.api_key = settings.whatsapp_api_key
        self.enabled = bool(self.phone and self.api_key)
        if self.enabled:
            logger.info(f"WhatsApp alert manager initialized for {self.phone}")
        else:
            logger.info("WhatsApp not configured — add WHATSAPP_PHONE_NUMBER and WHATSAPP_API_KEY to .env")

    def _send(self, message: str) -> bool:
        if not self.enabled:
            return False
        try:
            params = {
                "phone": self.phone,
                "text": message,
                "apikey": self.api_key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            success = resp.status_code == 200
            if not success:
                logger.warning(f"WhatsApp send failed: HTTP {resp.status_code}")
            return success
        except Exception as e:
            logger.warning(f"WhatsApp send error: {e}")
            return False

    def send_gem_alert(self, gem: GemSignal) -> bool:
        if not self.enabled:
            return False
        msg = (
            f"🚀 *Gem Found: {gem.ticker_symbol}*\n"
            f"Score: {gem.total_score}/100\n"
            f"Class: {gem.classification.value}\n"
            f"Sources: {gem.source_count}\n"
        )
        if gem.reddit_score > 0:
            msg += f"Reddit: {gem.reddit_score}\n"
        if gem.discord_score > 0:
            msg += f"Discord: {gem.discord_score}\n"
        if gem.stocktwits_score > 0:
            msg += f"StockTwits: {gem.stocktwits_score}\n"
        if gem.insider_score > 0:
            msg += f"Insider: {gem.insider_score}\n"
        if gem.trends_score > 0:
            msg += f"Trends: {gem.trends_score}\n"
        if gem.earnings_score > 0:
            msg += f"Earnings: {gem.earnings_score}\n"
        msg += f"\n_Time: {datetime.now().strftime('%H:%M:%S')}_"
        return self._send(msg)

    def send_trade_notification(self, ticker: str, action: str, shares: int, price: float, pnl: float | None = None) -> bool:
        if not self.enabled:
            return False
        msg = (
            f"{'🟢' if action == 'buy' else '🔴'} *Trade Executed*\n"
            f"{action.upper()}: {shares} {ticker} @ ${price:.2f}\n"
        )
        if pnl is not None:
            emoji = "📈" if pnl >= 0 else "📉"
            msg += f"P&L: {emoji} ${pnl:+.2f}\n"
        msg += f"\n_Time: {datetime.now().strftime('%H:%M:%S')}_"
        return self._send(msg)

    def send_risk_alert(self, title: str, body: str) -> bool:
        if not self.enabled:
            return False
        msg = f"⚠️ *Risk Alert: {title}*\n{body}\n\n_Time: {datetime.now().strftime('%H:%M:%S')}_"
        return self._send(msg)

    def send_daily_summary(self, gem_count: int, trade_count: int, portfolio_value: float) -> bool:
        if not self.enabled:
            return False
        msg = (
            f"📊 *Daily Summary*\n"
            f"Gems: {gem_count}\n"
            f"Trades: {trade_count}\n"
            f"Portfolio: ${portfolio_value:,.2f}\n"
            f"\n_Time: {datetime.now().strftime('%H:%M:%S')}_"
        )
        return self._send(msg)
