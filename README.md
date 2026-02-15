# Deliveroo Backend API

A robust Flask-based backend for the Deliveroo parcel delivery platform. This API handles user authentication, order management, courier assignment, M-Pesa payments, and email notifications.

## Features

- **Authentication**: Secure user registration and login using JWT (JSON Web Tokens).
- **User Roles**: distinct roles for Customers, Couriers, and Admins.
- **Order Management**: Create, track, and update parcel delivery orders.
- **Geolocation**: Integrated with Mapbox for address geocoding, distance calculation, and routing.
- **Payments**: Integrated with Safaricom M-Pesa (Daraja API) for mobile payments.
- **Email Notifications**: Automated emails for welcome, order creation, status updates, and delivery confirmation using Resend.
- **Courier Features**: Real-time location updates, earnings tracking, and delivery code verification.
- **Admin Dashboard**: Comprehensive stats and management endpoints.

## Tech Stack

- **Framework**: Flask (Python)
- **Database**: PostgreSQL (Production) / SQLite (Dev)
- **ORM**: SQLAlchemy
- **Authentication**: Flask-JWT-Extended
- **Migrations**: Flask-Migrate (Alembic)
- **Email**: Resend API
- **Maps**: Mapbox API
- **Payments**: M-Pesa Daraja API
- **Deployment**: Render

## Prerequisites

- Python 3.8+
- PostgreSQL (optional for local dev, required for prod)
- Cloudinary Account
- Mapbox Account
- Resend Account
- M-Pesa Daraja Account

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd backend
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory with the following variables:

    ```env
    # App Secrets
    SECRET_KEY=your_secret_key
    JWT_SECRET_KEY=your_jwt_secret_key

    # Database
    DATABASE_URL=sqlite:///app.db  # Or your PostgreSQL URL

    # External APIs
    RESEND_API_KEY=re_123...
    MAPBOX_ACCESS_TOKEN=pk.eyJ...
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME=...
    CLOUDINARY_API_KEY=...
    CLOUDINARY_API_SECRET=...

    # M-Pesa (Sandbox/Live)
    MPESA_CONSUMER_KEY=...
    MPESA_CONSUMER_SECRET=...
    MPESA_PASSKEY=...
    MPESA_SHORTCODE=...
    MPESA_CALLBACK_URL=https://your-app.onrender.com/api/payments/callback

    # Frontend URL (for redirects & emails)
    FRONTEND_URL=https://your-frontend.vercel.app
    EMAIL_SENDER=Deliveroo <notifications@yourdomain.com>
    ```

5.  **Initialize Database:**
    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

## Running the Application

**Development Mode:**
```bash
python3 app.py
```
The API will be available at `http://localhost:5000` (or `http://127.0.0.1:5000`).

**Production Mode (Gunicorn):**
```bash
gunicorn app:app
```

## API Endpoints Overview

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| **Auth** | | | |
| `POST` | `/api/register` | Register a new user | No |
| `POST` | `/api/login` | Login and get JWT | No |
| `POST` | `/api/verify-email` | Verify email address | Yes (Token) |
| **Orders** | | | |
| `POST` | `/api/orders` | Create a new delivery order | Yes (Customer) |
| `GET` | `/api/orders` | Get user's orders | Yes |
| `POST` | `/api/orders/<id>/complete` | Complete delivery (Courier) | Yes (Courier) |
| **Courier** | | | |
| `GET` | `/api/courier/orders` | Get assigned orders | Yes (Courier) |
| `PATCH` | `/api/courier/orders/<id>/status` | Update order status | Yes (Courier) |
| **Payments** | | | |
| `POST` | `/api/payments/pay` | Initiate M-Pesa STK Push | Yes |

## Deployment

This app is configured for deployment on **Render**.

1.  Connect your repo to Render.
2.  Set `Build Command` to `pip install -r requirements.txt`.
3.  Set `Start Command` to `gunicorn app:app`.
4.  Add all environment variables in the Render Dashboard.

## License

MIT
