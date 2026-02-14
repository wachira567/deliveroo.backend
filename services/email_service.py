import os
import resend
from flask import current_app

def send_email(to_email, subject, html_content, attachments=None):
    """
    Sends an email using Resend API.
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        api_key = os.environ.get("RESEND_API_KEY")
        if not api_key:
            logger.error("RESEND_API_KEY not found in environment variables.")
            return False
            
        resend.api_key = api_key

        sender = os.environ.get("EMAIL_SENDER", "Deliveroo <onboarding@resend.dev>")

        params = {
            "from": sender, 
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        if attachments:
            params["attachments"] = attachments

        email = resend.Emails.send(params)
        logger.info(f"Email sent successfully: {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
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
        
    attachments = [{
        "filename": f"receipt_order_{order_id}.pdf",
        "content": list(content)
    }]
    
    return send_email(user_email, subject, html_content, attachments)

def send_order_created_email(user_email, order_details):
    subject = f"Order #{order_details['id']} Created - Delivery Code Inside"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Order Created Successfully!</h2>
        <p>Your order for <strong>{order_details['parcel_name']}</strong> has been created.</p>
        <p><strong>Tracking ID:</strong> #{order_details['id']}</p>
        
        <div style="background-color: #fee2e2; padding: 15px; border-left: 5px solid #dc2626; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; color: #991b1b; font-weight: bold; text-transform: uppercase;">Security Alert</p>
            <p style="margin-top: 10px; color: #7f1d1d;">
                Your Delivery Confirmation Code is: <span style="font-size: 1.5em; font-weight: bold; background: white; padding: 2px 8px; border-radius: 4px; border: 1px solid #fecaca;">{order_details['delivery_code']}</span>
            </p>
            <p style="margin-top: 10px; font-size: 0.9em; color: #7f1d1d;">
                <strong>DO NOT SHARE</strong> this code until the courier physically arrives to deliver your parcel. The courier will ask for this code to complete the delivery.
            </p>
        </div>

        <p>We will notify you via email when a courier accepts your order.</p>
        <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/orders/{order_details['id']}" style="background-color: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">Track Order</a>
    </div>
    """
    return send_email(user_email, subject, html_content)


def send_order_status_email(user_email, order_id, status, parcel_name):
    status_messages = {
        "assigned": "has been assigned a courier.",
        "picked_up": "has been picked up by the courier.",
        "in_transit": "is on its way!",
        "delivered": "has been delivered successfully!",
        "cancelled": "has been cancelled."
    }
    
    status_message = status_messages.get(status, f"status has been updated to: {status}")
    
    subject = f"Order #{order_id} Update: {status.replace('_', ' ').title()}"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Order Status Update</h2>
        <p>Your order <strong>#{order_id}</strong> ({parcel_name}) {status_message}</p>
        
        <div style="margin-top: 20px;">
            <p>Current Status: <strong style="text-transform: uppercase; color: #f97316;">{status.replace('_', ' ')}</strong></p>
        </div>
        
        <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/orders/{order_id}" style="background-color: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">Track Order</a>
    </div>
    """
    return send_email(user_email, subject, html_content)

def send_order_delivered_email(user_email, order_details):
    order_id = order_details.get('id')
    parcel_name = order_details.get('parcel_name')
    subject = f"Delivered! - Order #{order_id} has arrived"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #f97316;">Order Delivered!</h1>
            <p style="font-size: 1.1em;">Your package has arrived safely.</p>
        </div>
        
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-top: 0;">Order Summary</h3>
            <p><strong>Order ID:</strong> #{order_id}</p>
            <p><strong>Item:</strong> {parcel_name}</p>
            <p><strong>Status:</strong> <span style="color: #16a34a; font-weight: bold;">DELIVERED</span></p>
        </div>
        
        <p>We hope you had a great experience with Deliveroo. Thank you for choosing us!</p>
        
        <div style="text-align: center; margin-top: 30px;">
             <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/orders/{order_id}" style="background-color: #f97316; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Order Details</a>
        </div>
        
        <p style="margin-top: 40px; font-size: 0.9em; color: #666; text-align: center;">
            Need help? Contact our support team.
        </p>
    </div>
    """
    return send_email(user_email, subject, html_content)
