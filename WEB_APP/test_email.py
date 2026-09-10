#!/usr/bin/env python3
"""
Email Configuration Diagnostic Script
Tests SMTP connection and email sending
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config_email import EMAIL_CONFIG

def test_email_config():
    print("=" * 60)
    print("EMAIL CONFIGURATION TEST")
    print("=" * 60)
    
    # Display config (mask password)
    print(f"\n📧 Configuration:")
    print(f"   Sender Email: {EMAIL_CONFIG['sender_email']}")
    print(f"   SMTP Server: {EMAIL_CONFIG['smtp_server']}")
    print(f"   SMTP Port: {EMAIL_CONFIG['smtp_port']}")
    print(f"   Use TLS: {EMAIL_CONFIG.get('use_tls', True)}")
    print(f"   Enabled: {EMAIL_CONFIG.get('enabled', False)}")
    print(f"   Password: {'***' + EMAIL_CONFIG['sender_password'][-4:] if EMAIL_CONFIG['sender_password'] else 'NOT SET'}")
    
    if not EMAIL_CONFIG.get('enabled', False):
        print("\n❌ Email notifications are DISABLED in config_email.py")
        print("   Set 'enabled': True to enable email notifications")
        return False
    
    # Test SMTP connection
    print(f"\n🔗 Testing SMTP Connection...")
    try:
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=10)
        print(f"   ✅ Connected to {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        
        if EMAIL_CONFIG.get('use_tls', True):
            server.starttls()
            print("   ✅ TLS encryption enabled")
        
        # Test login
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        print(f"   ✅ Successfully logged in as {EMAIL_CONFIG['sender_email']}")
        
        # Test sending a test email
        print(f"\n📬 Sending test email to {EMAIL_CONFIG['sender_email']}...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🧪 Test Email from Suspicious Activity Detection System"
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['sender_email']
        
        test_body = """This is a test email from the Suspicious Activity Detection System.

If you received this email, the SMTP configuration is working correctly!

Configuration Details:
- SMTP Server: {0}
- Port: {1}
- TLS Enabled: {2}
- Sender: {3}

You can now receive email alerts when suspicious activity is detected.
""".format(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], 
          EMAIL_CONFIG.get('use_tls', True), EMAIL_CONFIG['sender_email'])
        
        part = MIMEText(test_body, 'plain')
        msg.attach(part)
        
        server.send_message(msg)
        print(f"   ✅ Test email sent successfully!")
        
        server.quit()
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Email configuration is working!")
        print("=" * 60)
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Authentication Error: {str(e)}")
        print("   Check your sender_email and sender_password in config_email.py")
        print("   For Gmail, use an App Password, not your regular password")
        return False
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP Error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_email_config()
    exit(0 if success else 1)
