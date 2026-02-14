import os
import base64
import requests
from datetime import datetime

def generate_mpesa_access_token():
    consumer_key = os.environ.get("MPESA_CONSUMER_KEY")
    consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        credentials = f"{consumer_key}:{consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        print(f"Error generating access token: {e}")
        return None

def initiate_stk_push(phone_number, amount, order_id):
    access_token = generate_mpesa_access_token()
    if not access_token:
        return {"error": "Failed to generate access token"}

    process_request_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    business_short_code = os.environ.get("MPESA_SHORTCODE")
    passkey = os.environ.get("MPESA_PASSKEY")
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((business_short_code + passkey + timestamp).encode()).decode()
    
    # Format phone number to 254... using phonenumbers library for robustness
    try:
        import phonenumbers
        parsed_phone = phonenumbers.parse(phone_number, "KE") # Default to Kenya if no region
        if not phonenumbers.is_valid_number(parsed_phone):
             # Fallback to simple formatting if invalid but maybe usable?
             # But better to error or try simple logic
             pass
        else:
             # Format to E.164 (e.g. +254712345678) then remove +
             phone_number = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164).replace("+", "")
    except Exception as e:
        print(f"Phone formatting error: {e}")
        # Fallback to manual
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("+"):
            phone_number = phone_number.replace("+", "")
        
    payload = {
        "BusinessShortCode": business_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": business_short_code,
        "PhoneNumber": phone_number,
        "CallBackURL": os.environ.get("MPESA_CALLBACK_URL"),
        "AccountReference": f"Order {order_id}",
        "TransactionDesc": f"Payment for Order {order_id}"
    }
    
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print(f"Initiating STK Push to {phone_number} for amount {int(amount)}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(process_request_url, json=payload, headers=headers)
        print(f"M-Pesa STK Push Response Status: {response.status_code}")
        print(f"M-Pesa STK Push Response Body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error initiating STK push: {e}")
        # Return the response text if available to help debug 400 errors
        if 'response' in locals() and response is not None:
             try:
                 return response.json() # Try to return the specific error from M-Pesa
             except:
                 pass
        return {"error": str(e)}
