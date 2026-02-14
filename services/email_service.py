import os
import resend
from flask import current_app

def send_email(to_email, subject, html_content):
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
