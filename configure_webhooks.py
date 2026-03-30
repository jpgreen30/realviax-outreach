#!/usr/bin/env python3
"""
Configure Stripe and Brevo webhooks for Realviax Outreach.

This script:
1. Reads configuration from .env file
2. Registers a Stripe webhook endpoint for checkout.session.completed
3. Registers a Brevo webhook for email events (sent, delivered, opened, clicked, bounce)
4. Updates .env with any returned webhook secrets

Usage:
    python configure_webhooks.py

Requirements:
    pip install stripe requests python-dotenv
"""

import os
import sys
import stripe
import requests
import secrets
from pathlib import Path
from dotenv import load_dotenv, set_key, find_dotenv

def main():
    # Locate .env file in project root
    project_root = Path(__file__).parent.resolve()
    env_path = project_root / '.env'
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)

    load_dotenv(dotenv_path=env_path)

    # Determine backend URL
    # Priority: BACKEND_URL env var; else derive from FRONTEND_URL (assuming Vercel proxy)
    backend_url = os.getenv('BACKEND_URL')
    if not backend_url:
        frontend_url = os.getenv('FRONTEND_URL', 'https://realviax-ai-boost.vercel.app')
        # Vercel proxy pattern: frontend_url/api -> backend
        backend_url = frontend_url.rstrip('/') + '/api'
        print(f"Using derived backend API URL: {backend_url}")
    else:
        backend_url = backend_url.rstrip('/')
        if not backend_url.endswith('/api'):
            backend_url += '/api'
        print(f"Using BACKEND_URL: {backend_url}")

    # Stripe configuration
    stripe_key = os.getenv('STRIPE_SECRET_KEY', '').strip()
    if not stripe_key or 'your_stripe_secret' in stripe_key.lower() or stripe_key.startswith('sk_test_'):
        print("Stripe secret key is missing or a placeholder. Skipping Stripe webhook setup.")
        print("  To set up manually: go to Stripe Dashboard > Developers > Webhooks, add endpoint:")
        print(f"  {backend_url}/webhooks/stripe and select events: checkout.session.completed")
    else:
        stripe.api_key = stripe_key
        stripe_webhook_url = backend_url + '/webhooks/stripe'
        print(f"Creating Stripe webhook endpoint: {stripe_webhook_url}")
        try:
            # Define events based on handler in routes.py
            enabled_events = ['checkout.session.completed']
            endpoint = stripe.WebhookEndpoint.create(
                url=stripe_webhook_url,
                enabled_events=enabled_events,
                # Optionally: connect to specific account if using Stripe Connect
            )
            webhook_secret = endpoint.secret
            # Save to .env
            set_key(str(env_path), 'STRIPE_WEBHOOK_SECRET', webhook_secret)
            print(f"Stripe webhook endpoint created successfully.")
            print(f"  ID: {endpoint.id}")
            print(f"  Secret stored in .env")
        except Exception as e:
            print(f"ERROR: Stripe webhook creation failed: {e}")
            print("Please check your Stripe secret key and try again.")

    # Brevo configuration
    brevo_key = os.getenv('BREVO_API_KEY', '').strip()
    if not brevo_key or 'your_brevo_api_key' in brevo_key.lower():
        print("Brevo API key is missing or a placeholder. Skipping Brevo webhook setup.")
        print("  To set up manually: use Brevo v3 API to create webhook at:")
        print(f"  {backend_url}/webhooks/brevo with events: sent, delivered, opened, clicked, bounce")
    else:
        brevo_webhook_url = backend_url + '/webhooks/brevo'
        print(f"Creating Brevo webhook endpoint: {brevo_webhook_url}")
        # Generate a random secret for signature verification
        brevo_secret = secrets.token_hex(32)
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': brevo_key
        }
        payload = {
            'url': brevo_webhook_url,
            'event': ['sent', 'delivered', 'opened', 'clicked', 'bounce'],
            'secret': brevo_secret
        }
        try:
            resp = requests.post(
                'https://api.brevo.com/v3/webhooks',
                json=payload,
                headers=headers,
                timeout=15
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                webhook_id = data.get('id')
                # Brevo returns the secret if we sent one, else generates one; check response.
                returned_secret = data.get('secret', brevo_secret)
                set_key(str(env_path), 'BREVO_WEBHOOK_SECRET', returned_secret)
                print(f"Brevo webhook created successfully.")
                print(f"  ID: {webhook_id}")
                print(f"  Secret stored in .env")
            else:
                print(f"ERROR: Brevo webhook creation failed with status {resp.status_code}")
                print(f"  Response: {resp.text}")
        except requests.RequestException as e:
            print(f"ERROR: Network error while creating Brevo webhook: {e}")

    print("\nWebhook configuration complete.")
    print("Note: The backend must be publicly accessible for webhooks to work.")
    print("If you changed any settings, restart the backend to pick up new environment variables.")

if __name__ == '__main__':
    main()
