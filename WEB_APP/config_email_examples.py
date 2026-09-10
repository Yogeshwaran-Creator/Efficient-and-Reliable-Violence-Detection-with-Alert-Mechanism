# config_email_examples.py
# This file shows example configurations for different email providers
# Copy the relevant configuration to config_email.py and fill in your credentials

# EXAMPLE 1: Gmail Configuration
GMAIL_EXAMPLE = {
    'sender_email': 'prosdgunal@gmail.com',
    'sender_password': 'ngrx rgag ooey yhci',  # 16-char app password from https://myaccount.google.com/apppasswords
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}

# EXAMPLE 2: Outlook/Hotmail Configuration
OUTLOOK_EXAMPLE = {
    'sender_email': 'your-email@outlook.com',
    'sender_password': 'your-password',
    'smtp_server': 'smtp.live.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}

# EXAMPLE 3: Office 365 Configuration
OFFICE365_EXAMPLE = {
    'sender_email': 'your-email@company.onmicrosoft.com',
    'sender_password': 'your-password',
    'smtp_server': 'smtp.office365.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}

# EXAMPLE 4: Yahoo Configuration
YAHOO_EXAMPLE = {
    'sender_email': 'your-email@yahoo.com',
    'sender_password': 'xxxx xxxx xxxx xxxx',  # App password
    'smtp_server': 'smtp.mail.yahoo.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}

# EXAMPLE 5: Gmail with SSL (port 465)
GMAIL_SSL_EXAMPLE = {
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'xxxx xxxx xxxx xxxx',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 465,
    'use_tls': False,  # Use SSL instead of TLS
    'enabled': True
}

# EXAMPLE 6: Custom SMTP Server (e.g., SendGrid)
SENDGRID_EXAMPLE = {
    'sender_email': 'apikey@sendgrid.net',
    'sender_password': 'SG.xxxxxxxxxxxxx',  # SendGrid API key
    'smtp_server': 'smtp.sendgrid.net',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}

# EXAMPLE 7: Testing Mode (Disabled)
DISABLED_EXAMPLE = {
    'sender_email': 'your-email@example.com',
    'sender_password': 'placeholder',
    'smtp_server': 'smtp.example.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': False  # Alerts are disabled
}

print("""
Email Provider Configuration Examples
=====================================

Choose one example configuration and copy it to config_email.py

Steps:
1. Pick the configuration that matches your email provider
2. Fill in your actual email and password
3. Copy the EMAIL_CONFIG = {...} part to config_email.py
4. Set 'enabled': True when ready to test
5. Restart the Flask app

For detailed setup instructions, see EMAIL_SETUP.md
""")
