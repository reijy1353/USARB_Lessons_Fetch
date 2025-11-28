import os
import logging

from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from main import CalendarSchedule

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load the enviromental variables
load_dotenv()

# Get enviroments variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class TelegramBot:

    def __init__(self, app: CalendarSchedule) -> None:
        self.token = TELEGRAM_BOT_TOKEN
        self.app = app

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}!\nFeel free to type /help for help of course!",
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        await update.message.reply_text("/sync - will sync your calendar properly")

    async def sync(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message."""
        await update.message.reply_text("🔵 Sync in process...")
        self.app.sync_schedule()
        await update.message.reply_text("✅ Succesfully synced!")

    def run_bot(self):
        # Create the Application and pass it your bot's token.
        application = Application.builder().token(self.token).build()

        # on different commands - answer in Telegram
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("sync", self.sync))

        # on non command i.e message - echo the message on Telegram

        # Run the bot until the user presses Ctrl-C
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    """Start the bot."""
    app = CalendarSchedule()

    bot = TelegramBot(app)
    bot.run_bot()


if __name__ == "__main__":
    main()