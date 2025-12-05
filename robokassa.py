import hashlib
import time
import random
from urllib.parse import urlencode
from config import (
    ROBOKASSA_CHANNEL_1_MERCHANT_LOGIN,
    ROBOKASSA_CHANNEL_1_PASSWORD_1,
    ROBOKASSA_CHANNEL_1_PASSWORD_2,
    ROBOKASSA_CHANNEL_2_MERCHANT_LOGIN,
    ROBOKASSA_CHANNEL_2_PASSWORD_1,
    ROBOKASSA_CHANNEL_2_PASSWORD_2,
    ROBOKASSA_BASE_URL,
    ROBOKASSA_TEST_MODE
)

def generate_payment_url(amount: float, description: str, invoice_id: str = None, user_id: int = None, channel_name: str = None) -> tuple:
    """
    Generate Robokassa payment URL
    
    Args:
        amount: Payment amount in rubles
        description: Payment description
        invoice_id: Unique invoice ID (if None, will be generated)
        user_id: User telegram ID
        channel_name: Channel name ('channel_1' or 'channel_2') to use correct credentials
    
    Returns:
        Payment URL and invoice_id
    """
    # Select credentials based on channel
    if channel_name == "channel_1":
        merchant_login = ROBOKASSA_CHANNEL_1_MERCHANT_LOGIN
        password_1 = ROBOKASSA_CHANNEL_1_PASSWORD_1
    elif channel_name == "channel_2":
        merchant_login = ROBOKASSA_CHANNEL_2_MERCHANT_LOGIN
        password_1 = ROBOKASSA_CHANNEL_2_PASSWORD_1
    else:
        raise ValueError(f"Unknown channel_name: {channel_name}. Must be 'channel_1' or 'channel_2'")
    
    if invoice_id is None:
        # Generate unique integer ID (Robokassa requires integer from 1 to 9223372036854775807)
        # Using microseconds timestamp + random component to ensure uniqueness
        timestamp_part = int(time.time() * 1000000)
        random_part = random.randint(100, 999)  # 3-digit random component
        invoice_id = str(timestamp_part + random_part)
    
    # Convert amount to format expected by Robokassa (e.g., 1990.00)
    amount_str = f"{amount:.2f}"
    
    # Build URL parameters (without signature first)
    params = {
        'MerchantLogin': merchant_login,
        'OutSum': amount_str,
        'InvId': invoice_id,
        'Description': description,
    }
    
    if ROBOKASSA_TEST_MODE:
        params['IsTest'] = '1'
    
    # Add shp_ parameters (must be in alphabetical order for signature)
    shp_params = {}
    if user_id:
        params['Shp_user_id'] = str(user_id)
        shp_params['Shp_user_id'] = str(user_id)
    
    # Create signature: MerchantLogin:OutSum:InvId:Password1[:shp_params in alphabetical order]
    signature_string = f"{merchant_login}:{amount_str}:{invoice_id}:{password_1}"
    
    # Add shp_ parameters to signature in alphabetical order
    if shp_params:
        # Sort shp_ parameters alphabetically
        sorted_shp = sorted(shp_params.items())
        shp_string = ':'.join([f"{key}={value}" for key, value in sorted_shp])
        signature_string = f"{signature_string}:{shp_string}"
    
    signature = hashlib.md5(signature_string.encode()).hexdigest()
    params['SignatureValue'] = signature
    
    # Build URL
    url = f"{ROBOKASSA_BASE_URL}?{urlencode(params)}"
    return url, invoice_id

def verify_payment_signature(amount: str, invoice_id: str, signature: str, password: str, shp_params: dict = None) -> bool:
    """
    Verify Robokassa payment signature
    
    Args:
        amount: Payment amount
        invoice_id: Invoice ID
        signature: Signature from Robokassa
        password: Password for verification (Password #2)
        shp_params: Dictionary of shp_ parameters (e.g., {'Shp_user_id': '123'})
    
    Returns:
        True if signature is valid
    """
    # Formula: OutSum:InvId:Password2[:shp_params in alphabetical order]
    signature_string = f"{amount}:{invoice_id}:{password}"
    
    # Add shp_ parameters to signature in alphabetical order
    if shp_params:
        sorted_shp = sorted(shp_params.items())
        shp_string = ':'.join([f"{key}={value}" for key, value in sorted_shp])
        signature_string = f"{signature_string}:{shp_string}"
    
    calculated_signature = hashlib.md5(signature_string.encode()).hexdigest()
    return calculated_signature.lower() == signature.lower()

def get_result_url_signature(amount: str, invoice_id: str, password: str) -> str:
    """
    Generate signature for ResultURL (notification from Robokassa)
    
    Args:
        amount: Payment amount
        invoice_id: Invoice ID
        password: Password #1 (channel-specific)
    
    Returns:
        Signature string
    """
    signature_string = f"{amount}:{invoice_id}:{password}"
    return hashlib.md5(signature_string.encode()).hexdigest()

