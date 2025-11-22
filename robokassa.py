import hashlib
import uuid
from urllib.parse import urlencode
from config import (
    ROBOKASSA_MERCHANT_LOGIN,
    ROBOKASSA_PASSWORD_1,
    ROBOKASSA_PASSWORD_2,
    ROBOKASSA_BASE_URL,
    ROBOKASSA_TEST_MODE
)

def generate_payment_url(amount: float, description: str, invoice_id: str = None, user_id: int = None) -> str:
    """
    Generate Robokassa payment URL
    
    Args:
        amount: Payment amount in rubles
        description: Payment description
        invoice_id: Unique invoice ID (if None, will be generated)
        user_id: User telegram ID
    
    Returns:
        Payment URL
    """
    if invoice_id is None:
        invoice_id = str(uuid.uuid4())
    
    # Convert amount to format expected by Robokassa (e.g., 1990.00)
    amount_str = f"{amount:.2f}"
    
    # Create signature
    signature_string = f"{ROBOKASSA_MERCHANT_LOGIN}:{amount_str}:{invoice_id}:{ROBOKASSA_PASSWORD_1}"
    signature = hashlib.md5(signature_string.encode()).hexdigest()
    
    # Build URL parameters
    params = {
        'MerchantLogin': ROBOKASSA_MERCHANT_LOGIN,
        'OutSum': amount_str,
        'InvId': invoice_id,
        'Description': description,
        'SignatureValue': signature,
    }
    
    if ROBOKASSA_TEST_MODE:
        params['IsTest'] = '1'
    
    if user_id:
        params['Shp_user_id'] = str(user_id)
    
    # Build URL
    url = f"{ROBOKASSA_BASE_URL}?{urlencode(params)}"
    return url, invoice_id

def verify_payment_signature(amount: str, invoice_id: str, signature: str, password: str = ROBOKASSA_PASSWORD_2) -> bool:
    """
    Verify Robokassa payment signature
    
    Args:
        amount: Payment amount
        invoice_id: Invoice ID
        signature: Signature from Robokassa
        password: Password for verification (Password #2)
    
    Returns:
        True if signature is valid
    """
    signature_string = f"{amount}:{invoice_id}:{password}"
    calculated_signature = hashlib.md5(signature_string.encode()).hexdigest()
    return calculated_signature.lower() == signature.lower()

def get_result_url_signature(amount: str, invoice_id: str, password: str = ROBOKASSA_PASSWORD_1) -> str:
    """
    Generate signature for ResultURL (notification from Robokassa)
    
    Args:
        amount: Payment amount
        invoice_id: Invoice ID
        password: Password #1
    
    Returns:
        Signature string
    """
    signature_string = f"{amount}:{invoice_id}:{password}"
    return hashlib.md5(signature_string.encode()).hexdigest()

