"""
Telegram bot for automatic schedule monitoring and calendar sync.
"""
import os
import logging
from datetime import datetime
from typing import Optional, List, Any
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes

from main import CalendarSync
from schedule_monitor import ScheduleMonitor
from data_parser import calc_university_week_from_date


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ScheduleBot:
    """Telegram bot for schedule monitoring and sync."""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.group_name = os.getenv("GROUP_NAME", "IT11Z")
        self.monitor_weeks = int(os.getenv("MONITOR_WEEKS", "2"))  # Monitor current + next N weeks
        
        # Initialize calendar sync
        caldav_url = os.getenv("CALDAV_URL", "https://caldav.icloud.com/")
        username = os.getenv("ICLOUD_USERNAME")
        password = os.getenv("ICLOUD_PASSWORD")
        calendar_name = os.getenv("CALENDAR_NAME", "USARB Schedule")
        
        self.calendar_sync = CalendarSync(caldav_url, username, password, calendar_name)
        self.schedule_monitor = ScheduleMonitor()
        self._job_scheduled = False
        
        # Check if credentials are available
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
        if not username or not password:
            raise ValueError("ICLOUD_USERNAME and ICLOUD_PASSWORD must be set")
        
        # Initialize bot
        self.application = Application.builder().token(self.bot_token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Register command handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("sync", self.sync_command))
        self.application.add_handler(CommandHandler("check", self.check_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
    
    async def start_command(self, update: Any, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        # Schedule periodic job on first /start
        if not self._job_scheduled:
            if getattr(context, "job_queue", None) is None:
                logger.warning("JobQueue not available. Install extras: pip install 'python-telegram-bot[job-queue]'")
            else:
                check_interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
                context.job_queue.run_repeating(
                    self.auto_check,
                    interval=check_interval * 60,
                    first=10,
                )
                self._job_scheduled = True
                logger.info("Scheduled auto_check job (every %s minutes)", check_interval)

        await update.message.reply_text(
            "👋 Hello! I'm your USARB schedule monitor bot.\n\n"
            "I can:\n"
            "• Monitor schedule changes automatically\n"
            "• Sync lessons to your iCloud Calendar\n"
            "• Notify you when changes are detected\n\n"
            "Use /help for available commands."
        )
    
    async def help_command(self, update: Any, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
📚 Available Commands:

/start - Start the bot
/status - Check current status and monitored weeks
/sync - Manually sync schedule to calendar
/check - Check for schedule changes
/help - Show this help message

The bot automatically checks for changes every hour and notifies you when updates are detected.
        """
        await update.message.reply_text(help_text)
    
    async def status_command(self, update: Any, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        today = datetime.today().date()
        current_week = calc_university_week_from_date(today)
        weeks_to_monitor = list(range(current_week, current_week + self.monitor_weeks + 1))
        
        status_text = f"""
📊 Bot Status:

Group: {self.group_name}
Monitoring: Current week + next {self.monitor_weeks} week(s)
Weeks: {', '.join(map(str, weeks_to_monitor))}

Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Use /check to check for changes now.
Use /sync to sync to calendar.
        """
        await update.message.reply_text(status_text)
    
    async def check_command(self, update: Any, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command - check for schedule changes."""
        await update.message.reply_text("🔍 Checking for schedule changes...")
        
        today = datetime.today().date()
        current_week = calc_university_week_from_date(today)
        weeks_to_monitor = list(range(current_week, current_week + self.monitor_weeks + 1))
        
        try:
            # Fetch current schedule
            current_schedule = self.schedule_monitor.fetch_current_schedule(
                self.group_name, weeks_to_monitor
            )
            
            # Detect changes
            changes = self.schedule_monitor.detect_changes(
                self.group_name, weeks_to_monitor, current_schedule
            )
            
            if changes:
                # Format and send changes
                changes_text = self.schedule_monitor.format_changes(changes)
                await update.message.reply_text(changes_text)
                
                # Ask if user wants to sync
                await update.message.reply_text(
                    "Would you like to sync these changes to your calendar? Use /sync"
                )
            else:
                await update.message.reply_text("✅ No changes detected!")
                
        except Exception as e:
            logger.error(f"Error checking schedule: {e}")
            await update.message.reply_text(f"❌ Error checking schedule: {e}")
    
    async def sync_command(self, update: Any, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sync command - sync schedule to calendar."""
        await update.message.reply_text("🔄 Syncing schedule to calendar...")
        
        today = datetime.today().date()
        current_week = calc_university_week_from_date(today)
        weeks_to_monitor = list(range(current_week, current_week + self.monitor_weeks + 1))
        
        try:
            # Connect to calendar
            if not self.calendar_sync.calendar:
                if not self.calendar_sync.connect():
                    await update.message.reply_text("❌ Failed to connect to calendar")
                    return
            
            # Sync lessons
            self.calendar_sync.sync_lessons(
                group_name=self.group_name,
                weeks=weeks_to_monitor,
                overwrite=True,
                debug=False
            )
            
            # Update snapshot after successful sync
            current_schedule = self.schedule_monitor.fetch_current_schedule(
                self.group_name, weeks_to_monitor
            )
            self.schedule_monitor.update_snapshot(
                self.group_name, weeks_to_monitor, current_schedule
            )
            
            await update.message.reply_text("✅ Schedule synced successfully!")
            
        except Exception as e:
            logger.error(f"Error syncing schedule: {e}")
            await update.message.reply_text(f"❌ Error syncing schedule: {e}")
    
    async def auto_check(self, context: ContextTypes.DEFAULT_TYPE):
        """Automatic check for schedule changes (called periodically)."""
        try:
            today = datetime.today().date()
            current_week = calc_university_week_from_date(today)
            weeks_to_monitor = list(range(current_week, current_week + self.monitor_weeks + 1))
            
            # Fetch current schedule
            current_schedule = self.schedule_monitor.fetch_current_schedule(
                self.group_name, weeks_to_monitor
            )
            
            # Detect changes
            changes = self.schedule_monitor.detect_changes(
                self.group_name, weeks_to_monitor, current_schedule
            )
            
            if changes:
                # Format changes
                changes_text = self.schedule_monitor.format_changes(changes)
                
                # Send notification
                if self.chat_id:
                    await context.bot.send_message(
                        chat_id=self.chat_id,
                        text=f"🔔 Schedule Update Detected!\n\n{changes_text}\n\nUse /sync to update your calendar."
                    )
                
                # Auto-sync if configured
                auto_sync = os.getenv("AUTO_SYNC", "false").lower() == "true"
                if auto_sync:
                    logger.info("Auto-syncing calendar...")
                    if not self.calendar_sync.calendar:
                        self.calendar_sync.connect()
                    
                    self.calendar_sync.sync_lessons(
                        group_name=self.group_name,
                        weeks=weeks_to_monitor,
                        overwrite=True,
                        debug=False
                    )
                    
                    # Update snapshot after sync
                    self.schedule_monitor.update_snapshot(
                        self.group_name, weeks_to_monitor, current_schedule
                    )
                    
                    if self.chat_id:
                        await context.bot.send_message(
                            chat_id=self.chat_id,
                            text="✅ Calendar automatically updated!"
                        )
            
        except Exception as e:
            logger.error(f"Error in auto check: {e}")
            if self.chat_id:
                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"⚠️ Error during auto check: {e}"
                )
    
    def run(self):
        """Start the bot."""
        logger.info("Bot started. Monitoring schedule changes...")
        # Simply run polling; the job is scheduled on first /start
        self.application.run_polling()


def main():
    """Main function."""
    try:
        bot = ScheduleBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


if __name__ == "__main__":
    main()

