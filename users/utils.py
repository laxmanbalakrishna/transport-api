# utils.py
from twilio.rest import Client
from django.conf import settings
from django.core.cache import cache
import random

def generate_otp(contact_number):
    otp = random.randint(100000, 999999)
    cache_key = f"otp_{contact_number}"
    cache.set(cache_key, otp, timeout=300)  # OTP valid for 5 minutes
    return otp

def send_otp_via_twilio(contact_number, otp):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"Your OTP is {otp}",
        from_=settings.TWILIO_PHONE_NUMBER,  # Use the verified caller ID here
        to=contact_number
    )
    return message.sid

def verify_otp(contact_number, input_otp):
    cache_key = f"otp_{contact_number}"
    stored_otp = cache.get(cache_key)
    if stored_otp and str(stored_otp) == str(input_otp):
        cache.delete(cache_key)  # Invalidate OTP after verification
        return True
    return False
