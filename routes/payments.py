from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Payment, ParcelOrder, User, Notification
from extensions import db
from services.mpesa_service import initiate_stk_push

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
    user = User.query.get(current_user_id)
    
    if not phone_number:
        phone_number = user.phone
        
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400
        
    # Initiate STK Push
    response = initiate_stk_push(phone_number, order.price, order.id)
    
    if "error" in response:
        return jsonify({"error": response["error"]}), 500
        
    # Create Payment Record
    payment = Payment(
        order_id=order.id,
        amount=order.price,
        payment_method="mpesa",
        status="pending"
    )
    db.session.add(payment)
    db.session.commit()
    
    return jsonify({
        "message": "STK Push initiated successfully",
        "checkout_request_id": response.get("CheckoutRequestID")
    }), 200

@payments_bp.route('/callback', methods=['POST'])
def callback():
    data = request.get_json()
    print(f"M-Pesa Callback: {data}")
    
    # Process callback
    # Note: In a real app, you parse the body to get exact status
    # For now, we assume success or check result code
    
    try:
        body = data.get("Body", {}).get("stkCallback", {})
        result_code = body.get("ResultCode")
        # metadata = body.get("CallbackMetadata", {}).get("Item", [])
        
        # We need to find the payment by checkout request id if we stored it
        # or just assume the order is paid
        
        if result_code == 0:
            # Payment Successful
            # In a real scenario, we match CheckoutRequestID to the Payment record
            pass
            
        return jsonify({"message": "Callback received"}), 200
    except Exception as e:
         print(f"Error processing callback: {e}")
         return jsonify({"error": "Processing failed"}), 500
