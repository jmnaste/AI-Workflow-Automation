"""SMS delivery service using Twilio."""
import os
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


def get_twilio_config() -> Optional[dict]:
    """Get Twilio configuration from environment."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, phone_number]):
        return None
    
    return {
        "account_sid": account_sid,
        "auth_token": auth_token,
        "phone_number": phone_number,
    }


def is_twilio_configured() -> bool:
    """Check if Twilio is configured."""
    return get_twilio_config() is not None


def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via SMS using Twilio.
    
    Args:
        phone: Phone number with country code (e.g., +1234567890)
        otp: 6-digit OTP code
    
    Returns:
        True if sent successfully, False otherwise
    """
    config = get_twilio_config()
    if not config:
        raise ValueError("Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER")
    
    try:
        client = Client(config["account_sid"], config["auth_token"])
        
        message = client.messages.create(
            body=f"Your Flovify verification code is: {otp}\n\nThis code expires in 5 minutes. Never share this code.",
            from_=config["phone_number"],
            to=phone
        )
        
        return message.sid is not None
    except TwilioRestException as e:
        print(f"Twilio error: {e}")
        return False
    except Exception as e:
        print(f"SMS send error: {e}")
        return False
