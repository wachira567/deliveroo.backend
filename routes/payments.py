from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Payment, ParcelOrder, User, Notification
from extensions import db
from services.mpesa_service import initiate_stk_push

from services.email_service import send_payment_success_email
from utils.pdf import generate_receipt_pdf
from utils import create_notification

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/pay', methods=['POST'])
@jwt_required()
def pay():
    data = request.get_json()
    order_id = data.get('order_id')
    phone_number = data.get('phone_number') # Optional, fallback to user phone
    
    if not order_id:
        return jsonify({"error": "Order ID is required"}), 400
        
    order = ParcelOrder.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    user = User.query.get(current_user_id)
    
    if not phone_number:
        phone_number = user.phone
        
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400
        
    # Initiate STK Push
    response = initiate_stk_push(phone_number, order.price, order.id)
    
    if "error" in response:
        return jsonify({"error": response["error"]}), 500
        
    checkout_request_id = response.get("CheckoutRequestID")
    
    # Check if payment already exists for this order (retry?)
    # For now, create new or update
    
    # Create Payment Record
    payment = Payment(
        order_id=order.id,
        amount=order.price,
        payment_method="mpesa",
        status="pending",
        transaction_id=checkout_request_id # Store CheckoutRequestID temporarily to match callback
    )
    db.session.add(payment)
    db.session.commit()
    
    return jsonify({
        "message": "STK Push initiated successfully",
        "checkout_request_id": checkout_request_id
    }), 200

@payments_bp.route('/callback', methods=['POST'])
def callback():
    data = request.get_json()
    print(f"M-Pesa Callback: {data}")
    
    try:
        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        checkout_request_id = body.get("CheckoutRequestID")
        
        payment = Payment.query.filter_by(transaction_id=checkout_request_id).first()
        
        if not payment:
            print(f"Payment not found for CheckoutRequestID: {checkout_request_id}")
            return jsonify({"error": "Payment record not found"}), 404
            
        if result_code == 0:
            # Payment Successful
            print(f"Payment Successful for CheckoutRequestID: {checkout_request_id}")
            
            # Update Payment
            payment.status = "completed"
            
            # Update Order
            order = ParcelOrder.query.get(payment.order_id)
            if order:
                # order.status = "assigned" # Or keep pending until courier accepts?
                # Requirement: "money is sent... notification of payment successful"
                # Let's keep status as pending but maybe add a paid flag? 
                # Or just rely on payment status. 
                # User said "successful if it went through all this should update automatically"
                # For now let's not change order status to 'assigned' automatically unless logic dictates.
                # But 'pending' usually means 'waiting for courier'.
                # Let's just create notification.
                
                # Payment confirmed notification
                create_notification(
                    user_id=order.customer_id,
                    order_id=order.id,
                    message=f"Payment of KES {payment.amount} received successfully.",
                    type_="payment_received"
                )
                
                # Generate PDF
                try:
                    pdf_buffer = generate_receipt_pdf(order, payment)
                    
                    # Send Email
                    send_payment_success_email(
                        order.customer.email, 
                        order.id, 
                        payment.amount, 
                        pdf_buffer
                    )
                except Exception as e:
                    print(f"Error generating PDF or sending email: {e}")
                    import traceback
                    traceback.print_exc()

        else:
            # Payment Failed
            print(f"Payment Failed for CheckoutRequestID: {checkout_request_id}")
            payment.status = "failed"
            
            order = ParcelOrder.query.get(payment.order_id)
            if order:
                 create_notification(
                    user_id=order.customer_id,
                    order_id=order.id,
                    message=f"Payment failed. Reason: {body.get('ResultDesc')}",
                    type_="payment_failed"
                )
            
        db.session.commit()
            
        return jsonify({"message": "Callback processed"}), 200
    except Exception as e:
         import traceback
         traceback.print_exc()
         print(f"Error processing callback: {e}")
         return jsonify({"error": "Processing failed"}), 500
