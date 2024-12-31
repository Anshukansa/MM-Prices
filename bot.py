import os
import time
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime
import logging
from your_existing_file import setup_driver, get_abc_bullion_price, get_aarav_bullion_prices

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store active users who want price updates
active_users = set()

def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    active_users.add(user_id)
    welcome_message = (
        "👋 Welcome to the Gold Price Tracker Bot!\n\n"
        "Available commands:\n"
        "/check - Get current gold prices\n"
        "/subscribe - Subscribe to price updates\n"
        "/unsubscribe - Unsubscribe from updates\n"
        "/help - Show this help message"
    )
    update.message.reply_text(welcome_message)

def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 Gold Price Tracker Bot Commands:\n\n"
        "/check - Get current gold prices\n"
        "/subscribe - Get price updates every hour\n"
        "/unsubscribe - Stop receiving updates\n"
        "/help - Show this help message"
    )
    update.message.reply_text(help_text)

def check_prices(update: Update, context: CallbackContext):
    """Get current prices when /check command is issued."""
    update.message.reply_text("🔍 Checking current gold prices...")
    
    try:
        # Initialize the WebDriver
        driver = setup_driver(headless=True)
        
        try:
            # Get ABC Bullion price
            abc_price = get_abc_bullion_price(
                driver, 
                "https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar"
            )
            
            # Get Aarav Bullion price
            aarav_price = get_aarav_bullion_prices(
                driver, 
                "https://aaravbullion.in/"
            )
            
            # Format message
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"📊 Gold Prices as of {current_time}\n\n"
            
            if abc_price:
                message += f"ABC Bullion: ${abc_price}\n"
            else:
                message += "ABC Bullion: Price unavailable\n"
                
            if aarav_price:
                message += f"Aarav Bullion: Rs.{aarav_price['price']}\n"
            else:
                message += "Aarav Bullion: Price unavailable\n"
            
            update.message.reply_text(message)
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error checking prices: {e}")
        update.message.reply_text("❌ Sorry, there was an error checking the prices. Please try again later.")

def subscribe(update: Update, context: CallbackContext):
    """Subscribe to price updates."""
    user_id = update.effective_user.id
    if user_id not in active_users:
        active_users.add(user_id)
        update.message.reply_text("✅ You've successfully subscribed to price updates! You'll receive updates every hour.")
    else:
        update.message.reply_text("You're already subscribed to price updates!")

def unsubscribe(update: Update, context: CallbackContext):
    """Unsubscribe from price updates."""
    user_id = update.effective_user.id
    if user_id in active_users:
        active_users.remove(user_id)
        update.message.reply_text("❌ You've been unsubscribed from price updates.")
    else:
        update.message.reply_text("You're not currently subscribed to updates!")

def send_price_updates(context: CallbackContext):
    """Send price updates to all subscribed users."""
    if not active_users:
        return
        
    try:
        driver = setup_driver(headless=True)
        
        try:
            # Get prices
            abc_price = get_abc_bullion_price(
                driver, 
                "https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar"
            )
            aarav_price = get_aarav_bullion_prices(
                driver, 
                "https://aaravbullion.in/"
            )
            
            # Format message
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"🔄 Scheduled Update - {current_time}\n\n"
            
            if abc_price:
                message += f"ABC Bullion: ${abc_price}\n"
            else:
                message += "ABC Bullion: Price unavailable\n"
                
            if aarav_price:
                message += f"Aarav Bullion: Rs.{aarav_price['price']}\n"
            else:
                message += "Aarav Bullion: Price unavailable\n"
            
            # Send to all subscribed users
            bot = context.bot
            for user_id in active_users:
                try:
                    bot.send_message(chat_id=user_id, text=message)
                except Exception as e:
                    logger.error(f"Error sending update to user {user_id}: {e}")
                    
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error in scheduled update: {e}")

def main():
    """Start the bot."""
    # Get your token from environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    # Create the Updater and pass it your bot's token
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("check", check_prices))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Add job for periodic updates (every hour)
    updater.job_queue.run_repeating(send_price_updates, interval=3600, first=10)

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main()
