from aiohttp import web
from database import db
from robokassa import verify_payment_signature
from handlers import process_payment_success
from config import (
    ROBOKASSA_CHANNEL_1_PASSWORD_2,
    ROBOKASSA_CHANNEL_2_PASSWORD_2
)
from aiogram import Bot
import os
import logging

logger = logging.getLogger(__name__)

async def robokassa_result_handler(request):
    """Handle Robokassa ResultURL (notification)"""
    bot = request.app['bot']
    
    try:
        # Get parameters from request
        data = await request.post()
        
        logger.info(f"[Robokassa] Received payment notification: {dict(data)}")
        
        OutSum = data.get('OutSum', '')
        InvId = data.get('InvId', '')
        SignatureValue = data.get('SignatureValue', '')
        
        logger.info(f"[Robokassa] OutSum={OutSum}, InvId={InvId}, SignatureValue={SignatureValue}")
        
        if not all([OutSum, InvId, SignatureValue]):
            error_msg = "ERROR: Missing parameters"
            logger.error(f"[Robokassa] {error_msg}: OutSum={OutSum}, InvId={InvId}, SignatureValue={SignatureValue}")
            return web.Response(text=error_msg)
        
        # Extract all shp_ parameters (must be in alphabetical order for signature)
        shp_params = {}
        for key, value in data.items():
            if key.startswith('Shp_'):
                shp_params[key] = value
        
        logger.info(f"[Robokassa] Shp parameters: {shp_params}")
        
        # Get payment record to determine channel
        payment = await db.get_payment(InvId)
        if not payment:
            error_msg = f"ERROR: Payment not found for InvId={InvId}"
            logger.error(f"[Robokassa] {error_msg}")
            return web.Response(text=error_msg)
        
        logger.info(f"[Robokassa] Payment found: {payment}")
        
        # Select correct password based on channel
        channel_name = payment['channel_name']
        if channel_name == "channel_1":
            password_2 = ROBOKASSA_CHANNEL_1_PASSWORD_2
        elif channel_name == "channel_2":
            password_2 = ROBOKASSA_CHANNEL_2_PASSWORD_2
        else:
            error_msg = f"ERROR: Unknown channel: {channel_name}"
            logger.error(f"[Robokassa] {error_msg}")
            return web.Response(text=error_msg)
        
        # Verify signature with channel-specific password and shp_ parameters
        signature_valid = verify_payment_signature(OutSum, InvId, SignatureValue, password_2, shp_params)
        
        if not signature_valid:
            error_msg = "ERROR: Invalid signature"
            logger.error(f"[Robokassa] {error_msg} for InvId={InvId}")
            logger.error(f"[Robokassa] Expected signature calculation: OutSum={OutSum}, InvId={InvId}, Password2=***, ShpParams={shp_params}")
            return web.Response(text=error_msg)
        
        logger.info(f"[Robokassa] Signature verified successfully for InvId={InvId}")
        
        # Check if already processed
        if payment['status'] == 'success':
            logger.info(f"[Robokassa] Payment {InvId} already processed, returning OK")
            return web.Response(text=f"OK{InvId}")
        
        # Update payment status
        await db.update_payment_status(InvId, 'success')
        logger.info(f"[Robokassa] Payment status updated to 'success' for InvId={InvId}")
        
        # Process payment success
        user_id = payment['telegram_id']
        
        try:
            await process_payment_success(user_id, channel_name, bot)
            logger.info(f"[Robokassa] Payment success processed for user {user_id}, channel {channel_name}")
        except Exception as e:
            logger.error(f"[Robokassa] Error processing payment success: {e}", exc_info=True)
        
        logger.info(f"[Robokassa] Returning OK for InvId={InvId}")
        return web.Response(text=f"OK{InvId}")
        
    except Exception as e:
        logger.error(f"[Robokassa] Unexpected error in result handler: {e}", exc_info=True)
        return web.Response(text=f"ERROR: {str(e)}")

async def robokassa_success_handler(request):
    """Handle Robokassa SuccessURL (user redirect after payment)"""
    # This is just a redirect page, payment is processed via ResultURL
    return web.Response(
        text="<html><body><h1>Оплата успешно обработана!</h1><p>Вы можете закрыть эту страницу и вернуться в бот.</p></body></html>",
        content_type="text/html"
    )

async def robokassa_fail_handler(request):
    """Handle Robokassa FailURL (user redirect if payment failed)"""
    return web.Response(
        text="<html><body><h1>Оплата не была завершена</h1><p>Вы можете закрыть эту страницу и вернуться в бот.</p></body></html>",
        content_type="text/html"
    )

async def robokassa_health_check(request):
    """Health check endpoint to verify webhook server is accessible"""
    return web.Response(
        text="Robokassa webhook server is running",
        content_type="text/plain"
    )

def setup_payment_routes(app: web.Application, bot: Bot):
    """Setup payment webhook routes"""
    app['bot'] = bot
    app.router.add_post('/robokassa/result', robokassa_result_handler)
    app.router.add_get('/robokassa/success', robokassa_success_handler)
    app.router.add_get('/robokassa/fail', robokassa_fail_handler)
    app.router.add_get('/robokassa/health', robokassa_health_check)  # For testing accessibility

