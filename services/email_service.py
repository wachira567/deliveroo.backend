import os
import resend
from flask import current_app

def send_email(to_email, subject, html_content, attachments=None):
    """
    Sends an email using Resend API.
    """
    try:
        api_key = os.environ.get("RESEND_API_KEY")
        if not api_key:
            print("RESEND_API_KEY not found in environment variables.")
            return False
            
        resend.api_key = api_key

        params = {
            "from": "Deliveroo <onboarding@resend.dev>", 
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        if attachments:
            params["attachments"] = attachments

        email = resend.Emails.send(params)
        print(f"Email sent successfully: {email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_magic_link(user_email, magic_link_url):
    subject = "Welcome to Deliveroo - Confirm your email"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Welcome to Deliveroo!</h2>
        <p>Thanks for signing up. Please click the link below to confirm your email and log in:</p>
        <a href="{magic_link_url}" style="background-color: #00CCBC; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Confirm Email</a>
        <p>Or copy and paste this link: {magic_link_url}</p>
    </div>
    """
    return send_email(user_email, subject, html_content)

def send_payment_success_email(user_email, order_id, amount, pdf_buffer):
    subject = f"Payment Successful - Order #{order_id}"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Payment Received!</h2>
        <p>Your payment of <strong>KES {amount}</strong> for Order #{order_id} has been successfully received.</p>
        <p>Please find your receipt attached.</p>
        <p>Thank you for choosing Deliveroo!</p>
    </div>
    """
    
    # Check if pdf_buffer is bytes or buffer
    if hasattr(pdf_buffer, 'getvalue'):
        content = pdf_buffer.getvalue()
    else:
        content = pdf_buffer
        
    # Convert to list of integers (bytes) because Resend SDK expects list of ints or bytes
    # Actually Resend Python SDK expects:
    # "attachments": [{"filename": "invoice.pdf", "content": list(file_bytes)}]
    
    attachments = [{
        "filename": f"receipt_order_{order_id}.pdf",
        "content": list(content)
    }]
    
    return send_email(user_email, subject, html_content, attachments)
