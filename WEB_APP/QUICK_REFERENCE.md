# 🎯 Quick Reference - Email Notification Feature

## What Was Added?

A complete **email notification system** that automatically sends emails when the AI model detects suspicious activities.

## Files Added (7)

| File | Purpose | User Action Required |
|------|---------|---------------------|
| `config_email.py` | Email configuration | ⚠️ **MUST CONFIGURE** |
| `config_email_examples.py` | Example configs | Reference only |
| `EMAIL_SETUP.md` | Detailed setup guide | For configuration |
| `EMAIL_FEATURE.md` | Full documentation | For reference |
| `IMPLEMENTATION_SUMMARY.md` | Overview | For understanding |
| `DEPLOYMENT_CHECKLIST.md` | Deployment guide | Before going live |
| `templates/admin_alerts.html` | Admin dashboard | Automatic |

## Files Modified (1)

- **app.py** - Added email functions, routes, and detection logic

## 🚀 30-Minute Setup

### Step 1: Get Email Password (5 min)

**For Gmail:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer"
3. Copy the 16-character password

**For Others:** See EMAIL_SETUP.md

### Step 2: Configure Email (2 min)

Edit `config_email.py`:

```python
EMAIL_CONFIG = {
    'sender_email': 'your-email@gmail.com',          # Your email
    'sender_password': 'xxxx xxxx xxxx xxxx',        # 16-char app password
    'smtp_server': 'smtp.gmail.com',                 # Server
    'smtp_port': 587,                                 # Port
    'use_tls': True,                                  # TLS encryption
    'enabled': True                                   # ← IMPORTANT: True to enable!
}
```

### Step 3: Test (5 min)

1. Start app: `python app.py`
2. Register with your email
3. Go to `/analyze`
4. Upload image/text with "weapon" or "thief"
5. Check email inbox

### Step 4: Verify Admin Dashboard (3 min)

1. Login as admin
2. Go to `/admin`
3. Click "Email Alert History"
4. You should see your alert logged

## ⚡ Key Features

✅ **Automatic Alerts** - Email sent instantly when threat detected
✅ **5+ Email Providers** - Gmail, Outlook, Yahoo, Office365, etc.
✅ **Admin Dashboard** - View all alerts with filters and stats
✅ **Error Logging** - Database capture of all sent/failed alerts
✅ **Multiple Formats** - HTML and plain text emails
✅ **Security** - App password support, no hardcoded credentials

## 📧 What Users Receive

```
Subject: 🚨 ALERT: Suspicious Activity Detected - WEAPON_DETECTED

Alert Type: WEAPON_DETECTED
Timestamp: 2026-03-03 14:30:45

DETECTION DETAILS:
• Text Analysis: weapon
• Image Analysis: weapon
• Combined Analysis: weapon
• Video Analysis: N/A
```

## 🔍 Detectable Alerts

- 🔫 **WEAPON_DETECTED** - Gun, knife, weapon found
- 👤 **THIEF_DETECTED** - Theft/burglary detected
- 👊 **FIGHT_DETECTED** - Fight/violence detected
- 🔥 **FIRE_DETECTED** - Fire/smoke detected
- ⚠️ **SUSPICIOUS_ACTIVITY** - Generic suspicious behavior

## 📊 Admin Features

### View Alert History
- Go to `/admin` → "Email Alert History"
- See all alerts sent to users
- Filter by status: Sent or Failed
- View success rate percentage

### Statistics Available
- **Total Alerts** - All time count
- **Sent** - Successfully delivered ✓
- **Failed** - Delivery failures ✗
- **Success Rate** - Percentage delivered

### API Endpoint
GET `/api/alert-stats`

Returns:
```json
{
    "total": 45,
    "sent": 42,
    "failed": 3,
    "by_type": {
        "WEAPON_DETECTED": 15,
        "SUSPICIOUS_ACTIVITY": 18,
        "THIEF_DETECTED": 7,
        "FIRE_DETECTED": 5
    }
}
```

## 🔧 Configuration Examples

### Gmail
```python
EMAIL_CONFIG = {
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'xxxx xxxx xxxx xxxx',  # App password!
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}
```

### Outlook
```python
EMAIL_CONFIG = {
    'sender_email': 'your-email@outlook.com',
    'sender_password': 'your-password',
    'smtp_server': 'smtp.live.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}
```

### Yahoo
```python
EMAIL_CONFIG = {
    'sender_email': 'your-email@yahoo.com',
    'sender_password': 'xxxx xxxx xxxx xxxx',  # App password!
    'smtp_server': 'smtp.mail.yahoo.com',
    'smtp_port': 587,
    'use_tls': True,
    'enabled': True
}
```

See `config_email_examples.py` for more providers.

## ⚠️ Important Notes

### Must Do
- ✅ Edit `config_email.py` with your email
- ✅ Use **app-specific password** (not regular password)
- ✅ Set `'enabled': True`
- ✅ Verify SMTP server and port match provider

### Common Mistakes
- ❌ Using regular Google password instead of app password
- ❌ Forgetting to set `'enabled': True`
- ❌ Wrong SMTP server address
- ❌ Wrong port number (usually 587, not 25 or 465)

### Security Tips
- 🔒 Don't commit `config_email.py` with real credentials
- 🔒 Use different passwords for different accounts
- 🔒 Enable 2-factor authentication on email account
- 🔒 Regularly review admin dashboard for suspicious alerts

## 🐛 Troubleshooting

### "Email notifications are disabled"
- Check `config_email.py` - set `'enabled': True`
- Then restart Flask app

### "SMTP Authentication failed"
- Gmail? Use 16-character **app password**, not regular password
- Wrong email address? Check `sender_email`
- Check that 2-factor verification is enabled

### "Connection refused"
- Port blocked? Try port 465 instead of 587
- Set `'use_tls': False` for port 465
- Check firewall isn't blocking ports

### "Email sent but not received"
- Check spam/junk folder
- Verify recipient email is correct
- Check database logs: `/admin/alerts`

### No alerts in admin dashboard
- Did detection happen? Check Flask console
- Is alert keyword present? (weapon, thief, fight, fire)
- Is email enabled? Check (`'enabled': True`)

## 📚 Detailed Documentation

- **EMAIL_SETUP.md** - Step-by-step for each provider (200+ lines)
- **EMAIL_FEATURE.md** - Complete technical documentation (400+ lines)
- **IMPLEMENTATION_SUMMARY.md** - Implementation details
- **DEPLOYMENT_CHECKLIST.md** - Pre-production checklist

## 🎯 Next Steps

1. **Configure**: Edit `config_email.py`
2. **Test**: Upload media and trigger detection
3. **Verify**: Check email and admin dashboard
4. **Monitor**: Review admin alerts dashboard regularly
5. **Optimize**: If needed, add async email sending (future)

## 📞 Quick Support

**Problem**: Emails not sending
1. Check Flask console for [ERROR] messages
2. Verify `'enabled': True` in config
3. Check credentials in config_email.py
4. See EMAIL_SETUP.md Troubleshooting section

**Problem**: Can't find admin dashboard
Access: `/admin` → "Email Alert History" button

**Problem**: Alert not detected
1. Check Flask console - is model detecting?
2. Use detection keyword: weapon, thief, fight, fire, suspicious
3. Check that suspicious activity is actually in image/text

## 📈 Database

New table: `email_alert_log`

Stores:
- User and recipient email
- Detection type and details
- Predictions and timestamp
- Send status (sent/failed)
- Error messages if failed

Accessible via: Admin Dashboard → Email Alert History

## 🚀 Performance

- Email sending: **Synchronous** - waits for response
- Timeout: **10 seconds** - won't hang forever
- Database: **Logged** - audit trail maintained
- Dashboard: **Paginated** - 20 alerts per page
- API: **Fast** - statistics calculated on demand

## ✨ Summary

✅ **Feature**: Complete and production-ready
✅ **Documentation**: Comprehensive guides provided
✅ **Configuration**: Easy 2-minute setup
✅ **Testing**: Works out of the box once configured
✅ **Support**: Detailed troubleshooting provided

---

## Quick Links

- **Setup Guide**: See EMAIL_SETUP.md
- **Configuration Examples**: See config_email_examples.py
- **Troubleshooting**: See EMAIL_SETUP.md or EMAIL_FEATURE.md
- **Admin Dashboard**: Go to `/admin` when logged in

## Support Contacts

For issues:
1. Check EMAIL_SETUP.md section matching your email provider
2. Review Flask console error messages
3. Check DEPLOYMENT_CHECKLIST.md
4. Review EMAIL_FEATURE.md for detailed documentation

---

**Ready to deploy?** Run `python app.py` after configuring `config_email.py`!
