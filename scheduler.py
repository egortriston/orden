from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from database import Database
from keyboards import get_reminder_keyboard, get_expired_keyboard, get_payment_keyboard
from messages import get_reminder_message, get_expired_message
from config import CHANNEL_1_ID, FREE_TRIAL_DAYS
from aiogram import Bot

db = Database()
scheduler = AsyncIOScheduler()

async def check_reminders(bot: Bot):
    """Check and send reminders"""
    reminders = await db.get_pending_reminders()
    
    for reminder in reminders:
        user_id = reminder['telegram_id']
        channel_name = reminder['channel_name']
        
        # Get subscription to get end date
        subscription = await db.get_active_subscription(user_id, channel_name)
        if subscription:
            end_date = datetime.fromisoformat(subscription['end_date'])
            
            # Send reminder
            try:
                await bot.send_message(
                    user_id,
                    get_reminder_message(end_date),
                    reply_markup=get_reminder_keyboard(channel_name)
                )
                await db.mark_reminder_sent(user_id, channel_name)
            except Exception as e:
                print(f"Error sending reminder to {user_id}: {e}")

async def check_expired_subscriptions(bot: Bot):
    """Check and deactivate expired subscriptions"""
    expired = await db.get_expired_subscriptions()
    
    for subscription in expired:
        user_id = subscription['telegram_id']
        channel_name = subscription['channel_name']
        
        # Deactivate subscription
        await db.deactivate_subscription(user_id, channel_name)
        
        # Remove from channel if it's channel_1
        if channel_name == "channel_1":
            try:
                await bot.ban_chat_member(chat_id=CHANNEL_1_ID, user_id=user_id)
            except Exception as e:
                print(f"Error removing user from channel: {e}")
        
        # Send expiration message
        try:
            await bot.send_message(
                user_id,
                get_expired_message(),
                reply_markup=get_expired_keyboard(channel_name)
            )
        except Exception as e:
            print(f"Error sending expiration message to {user_id}: {e}")

def setup_scheduler(bot: Bot):
    """Setup scheduled tasks"""
    # Check reminders every hour
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(hours=1),
        args=[bot],
        id='check_reminders',
        replace_existing=True
    )
    
    # Check expired subscriptions every 6 hours
    scheduler.add_job(
        check_expired_subscriptions,
        trigger=IntervalTrigger(hours=6),
        args=[bot],
        id='check_expired',
        replace_existing=True
    )
    
    scheduler.start()

