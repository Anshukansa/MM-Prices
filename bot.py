import os
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from datetime import datetime
import asyncio
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 Gold Price Tracker Bot Commands:\n\n"
        "/check - Get current gold prices\n"
        "/subscribe - Get price updates every hour\n"
        "/unsubscribe - Stop receiving updates\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def check_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current prices when /check command is issued."""
    await update.message.reply_text("🔍 Checking current gold prices...")
    
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
            
            await update.message.reply_text(message)
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error checking prices: {e}")
        await update.message.reply_text("❌ Sorry, there was an error checking the prices. Please try again later.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to price updates."""
    user_id = update.effective_user.id
    if user_id not in active_users:
        active_users.add(user_id)
        await update.message.reply_text("✅ You've successfully subscribed to price updates! You'll receive updates every hour.")
    else:
        await update.message.reply_text("You're already subscribed to price updates!")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from price updates."""
    user_id = update.effective_user.id
    if user_id in active_users:
        active_users.remove(user_id)
        await update.message.reply_text("❌ You've been unsubscribed from price updates.")
    else:
        await update.message.reply_text("You're not currently subscribed to updates!")

async def send_price_updates(context: ContextTypes.DEFAULT_TYPE):
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
            for user_id in active_users:
                try:
                    await context.bot.send_message(chat_id=user_id, text=message)
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

    # Create the Application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_prices))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Add job for periodic updates (every hour)
    application.job_queue.run_repeating(send_price_updates, interval=3600, first=10)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
