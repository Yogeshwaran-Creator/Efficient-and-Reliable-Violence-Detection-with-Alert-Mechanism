# 📐 Email Feature Architecture & Data Flow

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUSPICIOUS ACTIVITY DETECTION                 │
│                      EMAIL NOTIFICATION SYSTEM                   │
└─────────────────────────────────────────────────────────────────┘

                              USER INPUT
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                  TEXT          IMAGE        VIDEO
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                         ┌────────▼────────┐
                         │  AI Analysis    │
                         │ (BART + ResNet) │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              Text Pred    Image Pred    Video Pred
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                         ┌────────▼────────────┐
                         │ Check for Suspicious│
                         │ (weapon, thief...)  │
                         └────────┬────────────┘
                                  │
                     ┌────────────┤
                     │            │
               NO THREAT    THREAT DETECTED
                     │            │
                     └──────┐  ┌──┘
                            │  │
                    ┌───────▼──▼────────┐
                    │ send_email_alert()│
                    │   [SMTP Client]   │
                    └───────┬───────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
      ┌─────▼────┐  ┌──────▼─────┐  ┌─────▼────┐
      │ EmailAlert│  │   SMTP     │  │ Database │
      │   Model   │  │   Server   │  │ Logging  │
      └───────────┘  └────────────┘  └──────────┘
            │               │               │
            │          [Gmail/Outlook]      │
            │          [Yahoo/Office365]    │
            │          [Custom SMTP]        │
            │               │               │
            └───────────────┼───────────────┘
                            │
                  ┌─────────▼─────────┐
                  │  Email Delivered  │
                  │ to User's Inbox   │
                  └───────────────────┘
```

## Data Flow - Step by Step

```
1. USER UPLOADS MEDIA
   ↓
2. AI MODEL ANALYZES
   (Text Encoder: BART)
   (Image Encoder: ResNet18)
   (Video: Frame-by-frame inference)
   ↓
3. PREDICTIONS GENERATED
   ├─ Text Prediction
   ├─ Image Prediction
   ├─ Combined Prediction
   └─ Video Prediction
   ↓
4. CHECK FOR THREATS
   Keywords: weapon, thief, fight, fire, suspicious_activity
   ├─ Text contains keyword? → YES
   ├─ Image contains keyword? → YES
   ├─ Combined contains keyword? → YES
   └─ Video contains keyword? → YES
   ↓
5. THREAT DETECTED?
   ├─ YES → Proceed to step 6
   └─ NO → Stop (no alert sent)
   ↓
6. CATEGORIZE THREAT
   If contains "weapon" → WEAPON_DETECTED
   If contains "thief" → THIEF_DETECTED
   If contains "fight" → FIGHT_DETECTED
   If contains "fire" → FIRE_DETECTED
   Otherwise → SUSPICIOUS_ACTIVITY
   ↓
7. PREPARE EMAIL
   ├─ Format: HTML + Plain Text
   ├─ Subject: 🚨 ALERT: [TYPE]
   ├─ Body: Full predictions + details
   ├─ Priority: High
   └─ TO: User's registered email
   ↓
8. SEND EMAIL (SMTP)
   ├─ Connect to SMTP server
   ├─ Login with credentials
   ├─ Send message
   └─ Disconnect
   ↓
9. LOG TO DATABASE
   ├─ User ID
   ├─ Recipient email
   ├─ Detection type
   ├─ Predictions (JSON)
   ├─ Timestamp
   ├─ Status (sent/failed)
   └─ Error message (if any)
   ↓
10. NOTIFY USER
    ├─ Flash message: "Alert sent to your@email.com"
    ├─ Show in response
    └─ Visible in form
    ↓
11. USER CHECKS EMAIL
    └─ Review alert details and take action
```

## Component Interaction

```
┌──────────────┐
│   Flask App  │
│   (app.py)   │
└──────┬───────┘
       │
       ├─────────────────────────────────────┐
       │                                     │
       ▼                                     ▼
┌─────────────────┐              ┌──────────────────┐
│  /analyze Route │              │ Config Management│
│ [Upload Media]  │              │(config_email.py) │
└────────┬────────┘              └──────────────────┘
         │                                │
         ├─────────────────────────────┬──┘
         │                             │
         ▼                             ▼
    [AI Model]              [SMTP Configuration]
         │                           │
         ├─────────────────────────┬─┘
         │                         │
         ▼                         ▼
   [Predictions]         [SMTP Credentials]
         │                        │
         ├──────────────────┬─────┘
         │                  │
         ▼                  ▼
[Detection Logic]   [Email Constructor]
         │                  │
         ├──────────┬───────┘
         │          │
         ▼          ▼
  [Threat Found?] [Message Formatted]
         │          │
    YES  ├──────────┤
         │          │
         ▼          ▼
 [send_email_alert()]
         │
         ├─────────────────────┐
         │                     │
         ▼                     ▼
  [SMTP Client]         [Database Logger]
         │                     │
         ├──────────┬──────────┘
         │          │
         ▼          ▼
   [Send Email]  [Save Log]
         │          │
         └─────┬────┘
              │
              ▼
      [Email Delivered]
      [Alert Logged]
      [User Notified]
```

## Database Schema

```
┌────────────────────────────────────┐
│      EmailAlertLog Table           │
├────────────────────────────────────┤
│ id (INT, PRIMARY KEY)              │
├────────────────────────────────────┤
│ user_id (INT, FOREIGN KEY → User)  │
│ recipient_email (VARCHAR)          │
│ detection_type (VARCHAR)           │
│ detection_details (TEXT)           │
│ predictions (TEXT - JSON)          │
│ sent_at (DATETIME)                 │
│ status (VARCHAR: sent/failed)      │
│ error_message (TEXT, NULLABLE)     │
├────────────────────────────────────┤
│ Indexes:                           │
│  - user_id                         │
│  - status                          │
│  - sent_at                         │
│  - detection_type                  │
└────────────────────────────────────┘
        ▲
        │ References
        │
┌──────┴──────────────────────────────┐
│      User Table (Updated)           │
├─────────────────────────────────────┤
│ id                                   │
│ username                            │
│ email (← Receives alerts)           │
│ password_hash                       │
│ full_name                           │
│ is_admin                            │
│ email_notifications_enabled (NEW)   │
└─────────────────────────────────────┘
```

## Configuration Structure

```
config_email.py
│
├─ EMAIL_CONFIG (Dictionary)
│  │
│  ├─ sender_email (String)
│  │  └─ Your email address
│  │
│  ├─ sender_password (String)
│  │  └─ Email password or app-specific password
│  │
│  ├─ smtp_server (String)
│  │  ├─ smtp.gmail.com (Gmail)
│  │  ├─ smtp.live.com (Outlook)
│  │  ├─ smtp.mail.yahoo.com (Yahoo)
│  │  └─ smtp.office365.com (Office365)
│  │
│  ├─ smtp_port (Integer)
│  │  ├─ 587 (TLS)
│  │  └─ 465 (SSL)
│  │
│  ├─ use_tls (Boolean)
│  │  ├─ True (port 587)
│  │  └─ False (port 465 - SSL)
│  │
│  └─ enabled (Boolean)
│     ├─ True → Alerts enabled
│     └─ False → Alerts disabled
│
└─ Imported in app.py
   └─ Used by send_email_alert()
```

## Email Format

```
┌─────────────────────────────────────────┐
│      Email Message Structure            │
├─────────────────────────────────────────┤
│ From: sender_email                      │
│ To: recipient_email                     │
│ Subject: 🚨 ALERT: [THREAT_TYPE]       │
│ Priority: HIGH (X-Priority: 1)         │
├─────────────────────────────────────────┤
│ Content-Type: multipart/alternative    │
│                                         │
│ Part 1: Plain Text (Fallback)          │
│ ├─ Alert type and timestamp            │
│ ├─ All predictions                     │
│ └─ Instructions                        │
│                                         │
│ Part 2: HTML (Rich Format)             │
│ ├─ Styled alert box                    │
│ ├─ Color-coded information             │
│ ├─ Formatted predictions               │
│ └─ Professional appearance             │
└─────────────────────────────────────────┘
```

## Admin Dashboard Routes

```
Admin Interface
│
├─ /admin
│  └─ Admin Home Page
│     └─ Links to Email Alert History
│
├─ /admin/alerts  [GET]
│  ├─ Query Parameters:
│  │  ├─ page (default: 1)
│  │  └─ status (default: 'all', values: 'all', 'sent', 'failed')
│  │
│  └─ Displays:
│     ├─ Statistics Cards
│     │  ├─ Total Alerts
│     │  ├─ Sent Count
│     │  ├─ Failed Count
│     │  └─ Success Rate
│     │
│     ├─ Filter Controls
│     │  └─ Status dropdown
│     │
│     ├─ Alert Table
│     │  ├─ Timestamp
│     │  ├─ User/Email
│     │  ├─ Detection Type
│     │  ├─ Status Badge
│     │  └─ View Button
│     │
│     └─ Pagination
│        ├─ Previous/Next
│        └─ Page numbers
│
└─ /api/alert-stats  [GET]
   └─ JSON Response
      ├─ total (number)
      ├─ sent (number)
      ├─ failed (number)
      └─ by_type (object)
         ├─ WEAPON_DETECTED
         ├─ THIEF_DETECTED
         ├─ FIGHT_DETECTED
         ├─ FIRE_DETECTED
         └─ SUSPICIOUS_ACTIVITY
```

## Threat Detection Logic

```
Analysis Results
│
├─ Check pred_text
│  └─ Contains? → weapon | thief | fight | fire | suspicious_activity
│     └─ YES → Add to suspicious_detections
│
├─ Check pred_image
│  └─ Contains? → weapon | thief | fight | fire | suspicious_activity
│     └─ YES → Add to suspicious_detections
│
├─ Check pred_both
│  └─ Contains? → weapon | thief | fight | fire | suspicious_activity
│     └─ YES → Add to suspicious_detections
│
├─ Check pred_video
│  └─ Contains? → weapon | thief | fight | fire | suspicious_activity
│     └─ YES → Add to suspicious_detections
│
└─ If suspicious_detections not empty
   └─ SEND ALERT!
      └─ Determine type from keywords
         ├─ weapon → WEAPON_DETECTED
         ├─ thief → THIEF_DETECTED
         ├─ fight → FIGHT_DETECTED
         ├─ fire → FIRE_DETECTED
         └─ default → SUSPICIOUS_ACTIVITY
```

## SMTP Connection Flow

```
┌─ Connect to SMTP Server
│  └─ server = SMTP(smtp_server, smtp_port, timeout=10)
│
├─ Start TLS (if enabled)
│  └─ server.starttls()
│
├─ Authenticate
│  └─ server.login(sender_email, sender_password)
│
├─ Send Message
│  └─ server.send_message(msg)
│
├─ Disconnect
│  └─ server.quit()
│
└─ Result
   ├─ SUCCESS → status = 'sent'
   │  └─ Log to database: status='sent'
   │
   └─ FAILURE → status = 'failed'
      ├─ Capture error message
      └─ Log to database: status='failed', error_message=...
```

## Error Handling Flow

```
send_email_alert()
│
├─ Validate enabled flag
│  └─ If not enabled → LOG: "disabled" → RETURN False
│
├─ Prepare email content
│  ├─ Format subject
│  ├─ Build body text
│  ├─ Build HTML body
│  └─ Create MIME message
│     └─ Handle any formatting errors
│
├─ Send email
│  ├─ Connect to SMTP
│  ├─ Catch SMTPAuthenticationError → Log error
│  ├─ Catch SMTPException → Log error
│  ├─ Catch other exceptions → Log error
│  └─ If success → set send_success = True
│
├─ Log to database
│  ├─ Create EmailAlertLog record
│  ├─ Set status and error message
│  ├─ Save to database
│  └─ Catch DB errors → Log separately
│
└─ Return result
   ├─ True = Email sent and logged
   └─ False = Email failed or disabled
```

## File Relationships

```
app.py
├─ Imports from config_email.py
│  └─ EMAIL_CONFIG dictionary
│
├─ Imports SMTP modules
│  ├─ smtplib
│  ├─ email.mime
│  └─ datetime
│
├─ Defines models
│  ├─ User (modified)
│  └─ EmailAlertLog (new)
│
├─ Defines functions
│  └─ send_email_alert() (new)
│
├─ Defines routes
│  ├─ /analyze (modified)
│  ├─ /admin/alerts (new)
│  └─ /api/alert-stats (new)
│
└─ Defines template variables
   └─ For admin_alerts.html

config_email.py
└─ Email configuration
   └─ Imported by app.py

templates/admin_alerts.html
├─ Displays alert history
├─ Shows statistics
├─ Provides filters
├─ Shows detail modals
└─ References /admin/alerts route
```

---

This architecture ensures:
✅ Clean separation of concerns
✅ Easy configuration management
✅ Proper error handling
✅ Database audit trail
✅ Admin visibility
✅ Secure credential storage
✅ Scalable design
