# Deployment Guide for Render

This backend application is configured for deployment on Render.

## 1. Prerequisites

- A [Render](https://render.com/) account.
- This repository connected to your Render account.

## 2. Service Setup

1.  **Create a New Web Service** on Render.
2.  **Connect your repository**: select `wachira567/deliveroo.backend`.
3.  **Configure the service**:
    -   **Name**: `deliveroo-backend` (or your preferred name)
    -   **Region**: Closest to your users (e.g., Frankfurt, Oregon)
    -   **Branch**: `main`
    -   **Runtime**: `Python 3`
    -   **Build Command**: `pip install -r requirements.txt`
    -   **Start Command**: `gunicorn app:app` (Adjust `app:app` if your main entry point is different, e.g., `wsgi:app` or `run:app` based on your `app.py` structure).
        *Note: If you are using `flask run`, change it to a production server like `gunicorn`.*

## 3. Environment Variables

You must set the following environment variables in the Render dashboard under "Environment":

-   `PYTHON_VERSION`: `3.10.12` (Optional, if `.python-version` is not picked up, but recommended to force the version).
-   `DATABASE_URL`: Your production database URL (e.g., from Render PostgreSQL or Supabase).
-   `SECRET_KEY`: A strong random string for session security.
-   Any other variables defined in your `.env.example`.

## 4. Python Version

Since we are supporting multiple local python versions, we have removed the `.python-version` file to avoid conflicts.

**You MUST set the Python version manually on Render:**
1.  Go to your service **Settings** > **Environment**.
2.  Add a new variable: `PYTHON_VERSION` with value `3.10.12`.

## 5. First Deployment

-   Click **Create Web Service**.
-   Watch the logs. Render will install dependencies from `requirements.txt` and start the application.
