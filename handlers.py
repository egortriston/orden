from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime, timedelta
from database import Database
from keyboards import (
    get_main_menu_keyboard, get_payment_keyboard, get_reminder_keyboard,
    get_expired_keyboard, get_back_to_main_keyboard, get_legal_info_keyboard
)
from messages import (
    get_start_message, get_channel_1_info_message, get_channel_2_info_message,
    get_subscriptions_message, get_legal_info_message, get_gift_welcome_message,
    get_reminder_message, get_expired_message, get_payment_success_message,
    get_payment_success_with_bonus_message
)
from robokassa import generate_payment_url
from config import (
    CHANNEL_1_ID, CHANNEL_2_ID, CHANNEL_1_PRICE, CHANNEL_2_PRICE,
    FREE_TRIAL_DAYS, PAID_SUBSCRIPTION_DAYS, ADMIN_IDS
)
from aiogram import Bot

router = Router()
db = Database()

async def add_user_to_channel(bot: Bot, user_id: int, channel_id: str):
    """Add user to channel"""
    try:
        await bot.unban_chat_member(chat_id=channel_id, user_id=user_id)
    except Exception as e:
        print(f"Error adding user to channel: {e}")

async def remove_user_from_channel(bot: Bot, user_id: int, channel_id: str):
    """Remove user from channel"""
    try:
        await bot.ban_chat_member(chat_id=channel_id, user_id=user_id)
    except Exception as e:
        print(f"Error removing user from channel: {e}")

@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Add user to database
    await db.add_user(user_id, username, first_name, last_name)
    
    # Check if user should receive gift (from masterclass)
    user = await db.get_user(user_id)
    if user and not user.get('gift_received', False):
        # User from masterclass - send gift message
        start_date = datetime.now()
        end_date = start_date + timedelta(days=FREE_TRIAL_DAYS)
        
        # Create subscription
        await db.create_subscription(
            user_id, "channel_1", "gift", start_date, end_date, is_active=True
        )
        
        # Mark gift as received
        await db.mark_gift_received(user_id)
        
        # Add user to channel
        await add_user_to_channel(bot, user_id, CHANNEL_1_ID)
        
        # Create reminder for day 11
        reminder_date = start_date + timedelta(days=FREE_TRIAL_DAYS - 3)
        await db.create_reminder(user_id, "channel_1", reminder_date)
        
        # Send gift message
        await message.answer(
            get_gift_welcome_message(start_date, end_date),
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Regular user - show main menu
    await message.answer(
        get_start_message(),
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Handle main menu callback"""
    await callback.message.edit_text(
        get_start_message(),
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "channel_1_info")
async def callback_channel_1_info(callback: CallbackQuery):
    """Handle channel 1 info callback"""
    await callback.message.edit_text(
        get_channel_1_info_message(),
        reply_markup=get_payment_keyboard("channel_1")
    )
    await callback.answer()

@router.callback_query(F.data == "channel_2_info")
async def callback_channel_2_info(callback: CallbackQuery):
    """Handle channel 2 info callback"""
    await callback.message.edit_text(
        get_channel_2_info_message(),
        reply_markup=get_payment_keyboard("channel_2")
    )
    await callback.answer()

@router.callback_query(F.data == "my_subscriptions")
async def callback_my_subscriptions(callback: CallbackQuery):
    """Handle my subscriptions callback"""
    user_id = callback.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)
    
    await callback.message.edit_text(
        get_subscriptions_message(subscriptions),
        reply_markup=get_back_to_main_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "legal_info")
async def callback_legal_info(callback: CallbackQuery):
    """Handle legal info callback"""
    await callback.message.edit_text(
        get_legal_info_message(),
        reply_markup=get_legal_info_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def callback_payment(callback: CallbackQuery, bot: Bot):
    """Handle payment callback"""
    user_id = callback.from_user.id
    channel_name = callback.data.split("_")[1]  # channel_1 or channel_2
    
    # Determine price and description
    if channel_name == "channel_1":
        amount = CHANNEL_1_PRICE
        description = "Орден Демиургов - 1 месяц"
    else:
        amount = CHANNEL_2_PRICE
        description = "Родители Демиурги - 1 месяц"
    
    # Generate payment URL
    payment_url, invoice_id = generate_payment_url(amount, description, user_id=user_id)
    
    # Create payment record
    await db.create_payment(user_id, channel_name, amount, invoice_id, "pending")
    
    # Send payment button directly (according to TZ: button immediately redirects to payment)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
        [InlineKeyboardButton(text="На главную", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"{description}\nСумма: {amount} ₽",
        reply_markup=payment_keyboard
    )
    await callback.answer()

async def process_payment_success(user_id: int, channel_name: str, bot: Bot):
    """Process successful payment"""
    # Determine price and period
    if channel_name == "channel_1":
        amount = CHANNEL_1_PRICE
        channel_id = CHANNEL_1_ID
    else:
        amount = CHANNEL_2_PRICE
        channel_id = CHANNEL_2_ID
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=PAID_SUBSCRIPTION_DAYS)
    
    # Create subscription
    await db.create_subscription(
        user_id, channel_name, "paid", start_date, end_date, is_active=True
    )
    
    # Add user to channel
    await add_user_to_channel(bot, user_id, channel_id)
    
    # Special case: if user paid for channel_2 and never had channel_1, give bonus
    if channel_name == "channel_2":
        has_ever_had_channel_1 = await db.has_ever_had_subscription(user_id, "channel_1")
        if not has_ever_had_channel_1:
            # Give bonus gift
            bonus_start = datetime.now()
            bonus_end = bonus_start + timedelta(days=FREE_TRIAL_DAYS)
            await db.create_subscription(
                user_id, "channel_1", "gift", bonus_start, bonus_end, is_active=True
            )
            await add_user_to_channel(bot, user_id, CHANNEL_1_ID)
            
            # Send message with bonus
            await bot.send_message(
                user_id,
                get_payment_success_with_bonus_message(
                    start_date, end_date, bonus_start, bonus_end
                ),
                reply_markup=get_back_to_main_keyboard()
            )
            return
    
    # Regular payment success message
    await bot.send_message(
        user_id,
        get_payment_success_message(channel_name, start_date, end_date),
        reply_markup=get_back_to_main_keyboard()
    )

# Admin handlers
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel entry point"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "Админ-панель\n\n"
        "Доступные команды:\n"
        "/import_users - Импорт пользователей из мастер-класса\n"
        "Формат: /import_users 123456789 987654321 111222333"
    )

@router.message(Command("import_users"))
async def cmd_import_users(message: Message, bot: Bot):
    """Import users from masterclass"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    # Parse telegram IDs from command
    parts = message.text.split()[1:]
    if not parts:
        await message.answer("Укажите telegram_id пользователей через пробел.")
        return
    
    try:
        telegram_ids = [int(tid) for tid in parts]
    except ValueError:
        await message.answer("Ошибка: все ID должны быть числами.")
        return
    
    # Import users
    users_to_gift = await db.import_users_from_masterclass(telegram_ids)
    
    # Send gift messages to eligible users
    for user_id in users_to_gift:
        start_date = datetime.now()
        end_date = start_date + timedelta(days=FREE_TRIAL_DAYS)
        
        # Create subscription
        await db.create_subscription(
            user_id, "channel_1", "gift", start_date, end_date, is_active=True
        )
        
        # Mark gift as received
        await db.mark_gift_received(user_id)
        
        # Add user to channel
        await add_user_to_channel(bot, user_id, CHANNEL_1_ID)
        
        # Create reminder
        reminder_date = start_date + timedelta(days=FREE_TRIAL_DAYS - 3)
        await db.create_reminder(user_id, "channel_1", reminder_date)
        
        # Send gift message
        try:
            await bot.send_message(
                user_id,
                get_gift_welcome_message(start_date, end_date),
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")
    
    await message.answer(
        f"Импорт завершен.\n"
        f"Всего пользователей: {len(telegram_ids)}\n"
        f"Получили подарок: {len(users_to_gift)}"
    )

