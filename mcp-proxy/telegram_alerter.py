"""Send Telegram alerts for failures and summaries."""
import logging
from datetime import datetime
from typing import Dict, Any
from telegram import Bot
from telegram.error import TelegramError

from config import config
from models import PendingTransaction

logger = logging.getLogger(__name__)

class TelegramAlerter:
    """Send alerts via Telegram bot."""
    
    def __init__(self):
        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_BOT_TOKEN != "test_bot_token":
            self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            self.chat_id = config.TELEGRAM_ALERT_CHAT_ID
            self.enabled = True
            logger.info("Telegram alerter initialized")
        else:
            self.bot = None
            self.chat_id = None
            self.enabled = False
            logger.warning("Telegram alerter disabled (no valid token)")
    
    async def send_failure_alert(self, pending_tx: PendingTransaction) -> bool:
        """
        Send alert for failed transaction after max retries.
        
        Args:
            pending_tx: The failed pending transaction
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Telegram alerts disabled, skipping alert")
            return False
        
        # Format timestamp in IST
        created_ist = pending_tx.created_at.astimezone()
        
        message = f"""⚠️ Transaction Failed

Message: "{pending_tx.raw_message}"
Attempts: {pending_tx.attempt_count}
Last error: {pending_tx.last_error or 'Unknown error'}
Time: {created_ist.strftime('%Y-%m-%d %H:%M IST')}

Please check system health:
bash /root/system/scripts/check-telegram-sync.sh"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Sent failure alert for pending_tx {pending_tx.id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    async def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """
        Send daily summary report.
        
        Args:
            stats: Dictionary with:
                - successful_count
                - retry_count
                - failed_count
                - success_rate
                - avg_latency_ms
                - wal_size_mb
                - pending_count
                
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Telegram alerts disabled, skipping summary")
            return False
        
        from datetime import date
        
        # Format metrics
        success_emoji = "✅" if stats['failed_count'] == 0 else "⚠️"
        health_status = "🟢 Healthy" if stats['success_rate'] >= 99.0 else "🟡 Degraded"
        
        message = f"""📊 Sync Report ({date.today().strftime('%b %d, %Y')})

✅ Successful: {stats['successful_count']} transactions
⚠️ Retried: {stats['retry_count']} (all succeeded)
❌ Failed: {stats['failed_count']}
📈 Success rate: {stats['success_rate']:.1f}%
⏱️ Avg latency: {stats['avg_latency_ms']:.1f}ms
💾 WAL size: {stats['wal_size_mb']:.1f} MB
📋 Pending: {stats['pending_count']}

System: {health_status}"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            logger.info("Sent daily summary")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    async def send_admin_alert(self, message: str) -> bool:
        """
        Send custom admin alert.
        
        Args:
            message: Alert message
            
        Returns:
            True if sent successfully
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"⚠️ Admin Alert\n\n{message}"
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send admin alert: {e}")
            return False

# Global alerter instance
alerter = TelegramAlerter()
