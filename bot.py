import asyncio
import logging
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 1200))
TARGET_URL = os.getenv("TARGET_URL")

# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

SOLD_OUT_TEXT = "Currently all event tickets are sold-out!"


async def check_tickets():
    """Checks the website for ticket availability."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'HX-Request': 'true',
        'HX-Target': 'ticket',
        'HX-Trigger': 'ticket',
        'Referer': 'https://www.baselhack.ch/shop',
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(TARGET_URL, headers=headers, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                sold_out_div = soup.find(string=lambda text: SOLD_OUT_TEXT in text)
                tickets_available = sold_out_div is None
            else:
                tickets_available = False

            return response.status_code, tickets_available, response.text

    except httpx.RequestError as e:
        logger.error(f"Error during request: {e}")
        return None, False, str(e)


def send_email_notification(subject, body):
    """Sends an email notification."""
    if not all([EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_RECIPIENT]):
        logger.warning("Email configuration is incomplete. Skipping email notification.")
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_HOST_USER
    msg['To'] = EMAIL_RECIPIENT

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email notification sent successfully for subject: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise  # Re-raise the exception to be caught by the command handler if needed


async def perform_check(context: ContextTypes.DEFAULT_TYPE):
    """Performs a ticket check and sends a notification based on silent mode."""
    chat_id = context.job.chat_id
    is_silent = context.bot_data.get('is_silent', False)
    logger.info(f"Performing scheduled check. Silent mode: {is_silent}")
    
    status_code, tickets_available, content = await check_tickets()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Case 1: The check failed (network error or bad HTTP status)
    if status_code is None or status_code != 200:
        error_details = f"HTTP Status: {status_code or 'Request Failed'}"
        logger.error(f"Failed to check for tickets. {error_details}")
        
        # Always notify on failure, regardless of silent mode
        telegram_message = f"🚨 **Bot Check FAILED** 🚨\n\n" \
                           f"**Time:** `{now}`\n" \
                           f"**Details:** `{error_details}`"
        await context.bot.send_message(chat_id, text=telegram_message, parse_mode='MarkdownV2')
        
        send_email_notification(
            subject="[Alert] BaselHack Ticket Bot - Check FAILED",
            body=f"The bot failed to check for tickets at {now}.\n\n{error_details}\n\nResponse snippet:\n{content[:500]}"
        )
        return

    # Case 2: The check succeeded
    if tickets_available:
        logger.info("Tickets are available!")
        await context.bot.send_message(chat_id, text="🎉 **TICKETS ARE AVAILABLE\\!** 🎉\n\nGo to https://www\\.baselhack\\.ch/shop", parse_mode='MarkdownV2')
        send_email_notification(
            subject="[SUCCESS] BaselHack Tickets Available!",
            body="Tickets for BaselHack are available! Check the website now: https://www.baselhack.ch/shop"
        )
    else:  # Tickets not available
        logger.info("Tickets still sold out.")
        if not is_silent:
            message = f"✅ **Ticket Check Report**\n\n" \
                      f"**Time:** `{now}`\n" \
                      f"**HTTP Status:** `{status_code}`\n" \
                      f"**Tickets Available:** `False`"
            await context.bot.send_message(chat_id, text=message, parse_mode='MarkdownV2')
        else:
            logger.info("Silent mode is ON. Suppressing 'no tickets' notification.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the bot and schedules the check job."""
    chat_id = update.effective_chat.id
    if str(chat_id) != TELEGRAM_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return
        
    # Remove any existing jobs
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()

    try:
        interval = int(context.args[0]) if context.args else CHECK_INTERVAL_SECONDS
    except (IndexError, ValueError):
        interval = CHECK_INTERVAL_SECONDS

    context.job_queue.run_repeating(perform_check, interval=interval, first=1, chat_id=chat_id, name=str(chat_id))
    await update.message.reply_text(f"Bot started! Checking every {interval} seconds.")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stops the bot."""
    chat_id = update.effective_chat.id
    if str(chat_id) != TELEGRAM_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if not current_jobs:
        await update.message.reply_text("Bot is not currently running.")
        return
        
    for job in current_jobs:
        job.schedule_removal()
        
    await update.message.reply_text("Bot stopped.")


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forces an immediate check."""
    chat_id = update.effective_chat.id
    if str(chat_id) != TELEGRAM_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    await update.message.reply_text("Performing an immediate check...")
    
    # We can reuse the perform_check logic by creating a dummy job object
    class DummyJob:
        def __init__(self, chat_id):
            self.chat_id = chat_id
    
    dummy_job = DummyJob(chat_id)
    context.job = dummy_job
    await perform_check(context)


async def toggle_silent_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggles silent mode on or off."""
    chat_id = update.effective_chat.id
    if str(chat_id) != TELEGRAM_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return
        
    current_state = context.bot_data.get('is_silent', False)
    new_state = not current_state
    context.bot_data['is_silent'] = new_state
    
    status_text = "ON" if new_state else "OFF"
    await update.message.reply_text(
        f"Silent mode is now **{status_text}**.\n\n"
        f"You will only be notified if tickets are found or if a check fails.",
        parse_mode='Markdown'
    )


async def test_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a test email."""
    chat_id = update.effective_chat.id
    if str(chat_id) != TELEGRAM_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    await update.message.reply_text("Sending a test email...")
    try:
        send_email_notification(
            subject="[Test] BaselHack Ticket Bot",
            body="This is a test email to confirm your email notification settings are working correctly."
        )
        await update.message.reply_text("✅ Test email sent successfully! Please check your inbox.")
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        await update.message.reply_text(f"❌ Failed to send test email. Check the logs for details:\n`{e}`", parse_mode='Markdown')


def main():
    """Run the bot."""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TARGET_URL]):
        logger.error("Missing critical environment variables. Please check your .env file.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Initialize bot data
    application.bot_data['is_silent'] = False

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("check", check_now))
    application.add_handler(CommandHandler("togglesilent", toggle_silent_mode))
    application.add_handler(CommandHandler("testemail", test_email))

    # Send a startup message
    async def post_init(app: Application):
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="🤖 Bot has started up and is running.",
            disable_notification=True,
        )

    application.post_init = post_init
    application.run_polling()


if __name__ == "__main__":
    main()
