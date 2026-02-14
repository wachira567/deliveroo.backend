from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime

def generate_receipt_pdf(order, payment):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("Deliveroo - Payment Receipt", title_style))
    elements.append(Spacer(1, 20))
    
    # Order Details
    data = [
        ["Order ID", f"#{order.id}"],
        ["Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Customer", order.customer.full_name],
        ["Parcel", order.parcel_name],
        ["Pickup", order.pickup_address],
        ["Destination", order.destination_address],
        ["Distance", f"{order.distance} km"],
        ["Weight", f"{order.weight} kg"],
    ]
    
    t = Table(data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Payment Details
    elements.append(Paragraph("Payment Details", styles['Heading2']))
    payment_data = [
        ["Transaction ID", payment.transaction_id],
        ["Method", "M-Pesa"],
        ["Amount", f"KES {payment.amount}"],
        ["Status", "Completed"]
    ]
    
    pt = Table(payment_data, colWidths=[150, 300])
    pt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(pt)
    
    # Total
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Total Paid: KES {order.price}", styles['Heading2']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
