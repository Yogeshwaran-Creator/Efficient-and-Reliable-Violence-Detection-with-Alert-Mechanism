import os
import cv2
import json
import torch
import time
from threading import Timer
import torch.nn as nn
from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from transformers import BartModel, BartTokenizer
from torchvision import models, transforms
from PIL import Image
from collections import Counter
from functools import wraps
from werkzeug.utils import secure_filename
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config_email import EMAIL_CONFIG
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['TEMP_FOLDER'] = 'static/temp'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'jpg', 'jpeg', 'png'}
db = SQLAlchemy(app)

# Create upload directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=False)
    email_notifications_enabled = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Email Alert Log model - Track all suspicious activity alerts sent
class EmailAlertLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    detection_type = db.Column(db.String(100), nullable=False)
    detection_details = db.Column(db.Text)
    predictions = db.Column(db.Text)  # JSON string of predictions
    sent_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    status = db.Column(db.String(50), default='sent')  # 'sent', 'failed', 'pending'
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<EmailAlert {self.id}: {self.detection_type} to {self.recipient_email}>'

# Create tables and run a lightweight, robust migration for SQLite
with app.app_context():
    db.create_all()

    try:
        # Use a connection context and SQLAlchemy text() for compatibility
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info('user')"))
            rows = result.fetchall()
            existing_cols = [row[1] for row in rows]
            if 'email_notifications_enabled' not in existing_cols:
                try:
                    conn.execute(text("ALTER TABLE user ADD COLUMN email_notifications_enabled INTEGER DEFAULT 1"))
                    app.logger.info("DB migration: added column 'email_notifications_enabled' to user table")
                except Exception:
                    app.logger.exception("Failed to add column email_notifications_enabled to user table")
    except Exception:
        app.logger.exception("Error inspecting user table for migrations")

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def cleanup_file(filepath, delay=3600):
    """Delete a file after delay seconds"""
    def remove_file():
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            app.logger.error(f"Error deleting file {filepath}: {str(e)}")
    Timer(delay, remove_file).start()

def send_email_alert(recipient_email, detection_type, detail_text="", predictions=None, user_id=None):
    """
    Send email notification when suspicious activity is detected
    Also logs the alert in the database for audit trail
    
    Args:
        recipient_email: Email address to send alert to
        detection_type: Type of detection (suspicious_activity, weapon, thief, etc.)
        detail_text: Additional detail text
        predictions: Dictionary with detection predictions
        user_id: User ID for logging
    """
    if not EMAIL_CONFIG.get('enabled', False):
        app.logger.warning("Email notifications are disabled in config_email.py")
        app.logger.warning(f"Would have sent alert to {recipient_email} for {detection_type}")
        return False
    
    try:
        # Prepare email content
        subject = f"🚨 ALERT: Suspicious Activity Detected - {detection_type.upper()}"
        
        # Build email body
        body = f"""
SUSPICIOUS ACTIVITY DETECTION ALERT
====================================

Alert Type: {detection_type.upper()}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Recipient: {recipient_email}

DETECTION DETAILS:
------------------
"""
        
        if predictions:
            body += f"\n• Text Analysis: {predictions.get('pred_text', 'N/A')}"
            body += f"\n• Image Analysis: {predictions.get('pred_image', 'N/A')}"
            body += f"\n• Combined Analysis: {predictions.get('pred_both', 'N/A')}"
            body += f"\n• Video Analysis: {predictions.get('pred_video', 'N/A')}"
        
        if detail_text:
            body += f"\n\nAdditional Information:\n{detail_text}"
        
        body += """

IMPORTANT:
-----------
• This is an automated alert from the Suspicious Activity Detection System
• Please verify the alert and take appropriate action
• For false positives, please report to the administrator
• Do not reply to this email

System Information:
• Detection Model: MultiModal Classifier (BART + ResNet18)
• Confidence Assessment: Automated detection based on multimodal analysis

Please log in to the dashboard to view detailed analysis results.
        """
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = recipient_email
        msg['X-Priority'] = '1'  # High priority
        
        # Add plain text and HTML versions
        part1 = MIMEText(body, 'plain')
        msg.attach(part1)
        
        # HTML version
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 20px; border-radius: 5px; border-left: 5px solid #d32f2f;">
                    <h2 style="color: #d32f2f;">🚨 ALERT: Suspicious Activity Detected</h2>
                    <p><strong>Detection Type:</strong> {detection_type.upper()}</p>
                    <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    <h3 style="color: #333;">Detection Details:</h3>
                    <ul style="background-color: #f9f9f9; padding: 10px; border-radius: 3px;">
        """
        
        if predictions:
            html_body += f"<li><strong>Text Analysis:</strong> {predictions.get('pred_text', 'N/A')}</li>"
            html_body += f"<li><strong>Image Analysis:</strong> {predictions.get('pred_image', 'N/A')}</li>"
            html_body += f"<li><strong>Combined Analysis:</strong> {predictions.get('pred_both', 'N/A')}</li>"
            html_body += f"<li><strong>Video Analysis:</strong> {predictions.get('pred_video', 'N/A')}</li>"
        
        html_body += """
                    </ul>
                    <p style="color: #666; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <em>This is an automated alert. Please verify and take appropriate action.</em>
                    </p>
                </div>
            </body>
        </html>
        """
        
        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)
        
        # Send email
        send_success = False
        error_msg = None
        
        try:
            app.logger.info(f"Attempting to send email to {recipient_email} via {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=10)
            app.logger.info("SMTP connection established")
            
            if EMAIL_CONFIG.get('use_tls', True):
                server.starttls()
                app.logger.info("TLS encryption enabled")
            
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            app.logger.info(f"Logged in as {EMAIL_CONFIG['sender_email']}")
            
            server.send_message(msg)
            app.logger.info(f"Message sent to {recipient_email}")
            
            server.quit()
            
            send_success = True
            error_msg = None
            app.logger.info(f"✅ Email alert sent successfully to {recipient_email} for {detection_type}")
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Email authentication failed - check sender_email and sender_password in config_email.py: {str(e)}"
            app.logger.error(f"❌ {error_msg}")
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error while sending email: {str(e)}"
            app.logger.error(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            app.logger.error(f"❌ {error_msg}")
        
        # Log alert to database
        try:
            if user_id:
                alert_log = EmailAlertLog(
                    user_id=user_id,
                    recipient_email=recipient_email,
                    detection_type=detection_type,
                    detection_details=detail_text,
                    predictions=json.dumps(predictions) if predictions else None,
                    status='sent' if send_success else 'failed',
                    error_message=error_msg
                )
                db.session.add(alert_log)
                db.session.commit()
                app.logger.info(f"Alert logged to database for user {user_id}")
        except Exception as e:
            app.logger.error(f"Error logging alert to database: {str(e)}")
            db.session.rollback()
        
        return send_success
            
    except Exception as e:
        app.logger.error(f"Error preparing email alert: {str(e)}")
        return False

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

#########################################
# 1. Define the Model Architecture
#########################################
class MultiModalClassifier(nn.Module):
    def __init__(self, text_model, image_model, text_feat_dim, image_feat_dim, hidden_dim, num_classes):
        super(MultiModalClassifier, self).__init__()
        self.text_model = text_model
        self.image_model = image_model
        self.text_fc = nn.Linear(text_feat_dim, hidden_dim)
        self.image_fc = nn.Linear(image_feat_dim, hidden_dim)
        self.classifier = nn.Linear(hidden_dim, num_classes)
    
    def forward(self, text_input=None, image_input=None):
        features = None
        if text_input is not None:
            text_input_filtered = {k: v for k, v in text_input.items() if k != "labels"}
            text_outputs = self.text_model(**text_input_filtered)
            pooled_text = text_outputs.last_hidden_state.mean(dim=1)
            text_features = self.text_fc(pooled_text)
            features = text_features if features is None else features + text_features
        if image_input is not None:
            image_features = self.image_model(image_input)
            image_features = self.image_fc(image_features)
            features = image_features if features is None else features + image_features
        if (text_input is not None) and (image_input is not None):
            features = features / 2
        logits = self.classifier(features)
        return logits

#########################################
# 2. Setup Device, Label Mapping & Load Encoders
#########################################
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
label_list = ["accident", "accident", "Fall-person", "fight", "fire", "suspicious_activity", "thief", "weapon"]
label2id = {label: idx for idx, label in enumerate(label_list)}
id2label = {idx: label for label, idx in label2id.items()}
num_classes = len(label_list)

model_name = "facebook/bart-base"
text_encoder = BartModel.from_pretrained(model_name).to(device)
text_feat_dim = text_encoder.config.d_model

image_encoder = models.resnet18(pretrained=True)
num_img_features = image_encoder.fc.in_features
image_encoder.fc = nn.Identity()
image_encoder.to(device)
image_feat_dim = num_img_features

hidden_dim = 512

#########################################
# 3. Instantiate and Load the Model
#########################################
model = None
MODEL_SAVE_PATH = "multimodal_model.pth"

try:
    logger.info("Initializing model...")
    print("[STARTUP] Initializing MultiModalClassifier...")
    
    model = MultiModalClassifier(
        text_model=text_encoder,
        image_model=image_encoder,
        text_feat_dim=text_feat_dim,
        image_feat_dim=image_feat_dim,
        hidden_dim=hidden_dim,
        num_classes=num_classes
    ).to(device)
    print("[STARTUP] Model architecture created")
    
    if not os.path.exists(MODEL_SAVE_PATH):
        print(f"[WARNING] Model weights file not found: {MODEL_SAVE_PATH}")
        logger.warning(f"Model file not found at {MODEL_SAVE_PATH} - inference will return N/A")
        model = None
    else:
        print(f"[STARTUP] Loading model weights from {MODEL_SAVE_PATH}...")
        model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=device))
        model.eval()
        print("[STARTUP] Model loaded successfully and set to eval mode")
        logger.info("Model loaded successfully")
except Exception as e:
    print(f"[ERROR] Failed to load model: {str(e)}")
    logger.error(f"Model loading error: {str(e)}", exc_info=True)
    model = None
    print("[STARTUP] Continuing without model - inference will return N/A")

#########################################
# 4. Prepare Inference Functions
#########################################
image_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

tokenizer = BartTokenizer.from_pretrained(model_name)

def inference_text(model, tokenizer, text, device, max_length=128):
    try:
        if model is None:
            return "N/A"
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return "N/A"
        
        encoding = tokenizer(text, padding="max_length", truncation=True, max_length=max_length, return_tensors="pt")
        for key in encoding:
            encoding[key] = encoding[key].to(device)
        with torch.no_grad():
            logits = model(text_input=encoding, image_input=None)
        pred_id = torch.argmax(logits, dim=1).item()
        return id2label[pred_id]
    except Exception as e:
        app.logger.error(f"Text inference error: {str(e)}")
        raise ValueError(f"Text inference failed: {str(e)}")

def inference_image(model, image, transform, device):
    try:
        if model is None:
            return "N/A"
        if image is None:
            return "N/A"
        
        if isinstance(image, Image.Image):
            image = transform(image).unsqueeze(0).to(device)
        elif isinstance(image, torch.Tensor):
            image = image.unsqueeze(0).to(device)
        else:
            raise TypeError("Image must be PIL Image or torch Tensor")
        
        with torch.no_grad():
            logits = model(text_input=None, image_input=image)
        pred_id = torch.argmax(logits, dim=1).item()
        return id2label[pred_id]
    except Exception as e:
        app.logger.error(f"Image inference error: {str(e)}")
        raise ValueError(f"Image inference failed: {str(e)}")

def inference_both(model, tokenizer, text, image, transform, device, max_length=128):
    try:
        if model is None:
            return "N/A"
        if text is None or image is None:
            return "N/A"
        
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return "N/A"
            
        encoding = tokenizer(text, padding="max_length", truncation=True, max_length=max_length, return_tensors="pt")
        for key in encoding:
            encoding[key] = encoding[key].to(device)
        if isinstance(image, Image.Image):
            image = transform(image).unsqueeze(0).to(device)
        elif isinstance(image, torch.Tensor):
            image = image.unsqueeze(0).to(device)
        else:
            raise TypeError("Image must be PIL Image or torch Tensor")
        
        with torch.no_grad():
            logits = model(text_input=encoding, image_input=image)
        pred_id = torch.argmax(logits, dim=1).item()
        return id2label[pred_id]
    except Exception as e:
        app.logger.error(f"Combined inference error: {str(e)}")
        raise ValueError(f"Combined inference failed: {str(e)}")

def inference_video(model, video_path, transform, device, output_video_path):
    try:
        if model is None:
            return "N/A", []
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 120:
            fps = 30  # Default to 30 FPS if invalid
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid video dimensions: {width}x{height}")
        
        # Use appropriate fourcc codec based on output extension
        ext = os.path.splitext(output_video_path)[1].lower()
        fourcc = None
        
        if ext == '.mp4':
            # Try different codecs for MP4 compatibility
            fourcc = cv2.VideoWriter_fourcc(*'H264')
        elif ext == '.avi':
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        else:
            raise ValueError(f"Unsupported video format {ext}")
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
        
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        if not out.isOpened():
            logger.warning(f"VideoWriter failed with codec. Output file: {output_video_path}")
            # Try with MJPEG as fallback
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
            if not out.isOpened():
                raise ValueError("Could not create output video with any codec")
        
        predictions = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            try:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_pil = Image.fromarray(frame_rgb)
                pred = inference_image(model, frame_pil, transform, device)
                predictions.append(pred)
                
                # Add prediction text to frame
                cv2.putText(frame, f"Pred: {pred}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                out.write(frame)
            except Exception as e:
                app.logger.error(f"Error processing frame: {str(e)}")
                continue
                
        cap.release()
        out.release()
        
        # Verify output file was created and has content
        if not os.path.exists(output_video_path):
            raise ValueError(f"Output video file was not created: {output_video_path}")
        
        file_size = os.path.getsize(output_video_path)
        if file_size == 0:
            raise ValueError("Output video file is empty")
        
        logger.info(f"Video processed successfully. Output: {output_video_path} ({file_size} bytes)")
        
        if not predictions:
            logger.warning("No frames were processed successfully")
            return "N/A", []
            
        most_common = Counter(predictions).most_common(1)[0][0]
        return most_common, predictions
        
    except Exception as e:
        app.logger.error(f"Video processing error: {str(e)}")
        raise

def generate_report(pred_text, pred_image, pred_both, pred_video, video_frame_preds, sample_text, video_url):
    """
    Generate an analysis report summary.
    Skips AI report generation to prevent hanging.
    """
    try:
        # Return a formatted summary without calling external AI APIs
        # This prevents hanging issues with g4f client
        summary = f"""ANALYSIS REPORT
================

Detection Results:
- Text Analysis: {pred_text}
- Image Analysis: {pred_image}
- Combined Analysis: {pred_both}
- Video Analysis: {pred_video}

Consistency Assessment:
The predictions have been generated using a multimodal deep learning classifier.
Check the individual analysis results above for specific detections.

Note: For real-time analysis, please refer to the individual detection scores.
"""
        logger.info("Report summary generated successfully")
        return summary
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        # Fallback to minimal summary
        return f"Text: {pred_text} | Image: {pred_image} | Combined: {pred_both} | Video: {pred_video}"

#########################################
# 5. Define Routes for the Flask App
#########################################

# Routes for serving uploaded and processed files
@app.route('/uploads/<filename>')
def serve_upload(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        app.logger.error(f"Error serving upload: {str(e)}")
        return jsonify({"error": "File not found"}), 404

@app.route('/outputs/<filename>')
def serve_output(filename):
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename)
    except Exception as e:
        app.logger.error(f"Error serving output: {str(e)}")
        return jsonify({"error": "File not found"}), 404

@app.route('/temp/<filename>')
def serve_temp(filename):
    try:
        return send_from_directory(app.config['TEMP_FOLDER'], filename)
    except Exception as e:
        app.logger.error(f"Error serving temp file: {str(e)}")
        return jsonify({"error": "File not found"}), 404

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for debugging server issues"""
    status = {
        "status": "ok",
        "model_loaded": model is not None,
        "database": "connected",
        "timestamp": time.time()
    }
    try:
        # Test database connection
        User.query.first()
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    return jsonify(status), 200

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email, full_name=full_name)
        new_user.set_password(password)
        
        # First user is admin
        if User.query.count() == 0:
            new_user.is_admin = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    if request.method == 'POST':
        try:
            # Get text input
            sample_text = request.form.get('text_input', '')
            
            # Process image file if provided
            image = None
            image_url = None
            if 'image_input' in request.files and request.files['image_input'].filename != '':
                image_file = request.files['image_input']
                if image_file and allowed_file(image_file.filename):
                    try:
                        filename = secure_filename(f"img_{int(time.time())}_{image_file.filename}")
                        image_path = os.path.join(app.config['TEMP_FOLDER'], filename)
                        image_file.save(image_path)
                        image = Image.open(image_path).convert("RGB")
                        image_url = f"temp/{filename}"
                        cleanup_file(image_path)
                    except Exception as e:
                        app.logger.error(f"Image processing failed: {str(e)}")
                        image = None
                        image_url = None
            
            # Process video file if provided
            video_url = None
            original_video_url = None
            pred_video = "N/A"
            video_frame_preds = []
            
            if 'video_input' in request.files and request.files['video_input'].filename != '':
                video_file = request.files['video_input']
                if video_file and allowed_file(video_file.filename):
                    try:
                        timestamp = int(time.time())
                        original_filename = secure_filename(f"upload_{timestamp}_{video_file.filename}")
                        output_filename = secure_filename(f"processed_{timestamp}_{os.path.splitext(video_file.filename)[0]}.mp4")
                        
                        original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
                        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                        
                        video_file.save(original_path)
                        
                        # Process video
                        pred_video, video_frame_preds = inference_video(
                            model, original_path, image_transform, device, output_path
                        )
                        
                        # Generate URLs
                        original_video_url = f"uploads/{original_filename}"
                        video_url = f"outputs/{output_filename}"
                        
                        # Schedule cleanup
                        cleanup_file(original_path)
                        cleanup_file(output_path)
                    except Exception as e:
                        app.logger.error(f"Video processing failed: {str(e)}")
                        pred_video = "N/A"
                        video_frame_preds = []
            
            # Run inferences
            try:
                pred_text = inference_text(model, tokenizer, sample_text, device) if sample_text else "N/A"
            except Exception as e:
                app.logger.error(f"Failed to run text inference: {str(e)}")
                pred_text = "N/A"
            
            try:
                pred_image = inference_image(model, image, image_transform, device) if image is not None else "N/A"
            except Exception as e:
                app.logger.error(f"Failed to run image inference: {str(e)}")
                pred_image = "N/A"
            
            try:
                pred_both = inference_both(model, tokenizer, sample_text, image, image_transform, device) if (sample_text and image is not None) else "N/A"
            except Exception as e:
                app.logger.error(f"Failed to run combined inference: {str(e)}")
                pred_both = "N/A"
            
            # Generate AI report (wrapped in try-catch to prevent crashes)
            try:
                ai_report = generate_report(
                    pred_text, pred_image, pred_both, pred_video, 
                    video_frame_preds, sample_text, 
                    url_for('static', filename=video_url) if video_url else "N/A"
                )
            except Exception as e:
                app.logger.error(f"Failed to generate report: {str(e)}")
                ai_report = f"""Analysis Summary:
- Text Detection: {pred_text}
- Image Detection: {pred_image}
- Combined Detection: {pred_both}
- Video Detection: {pred_video}

Report generation was skipped."""
            
            # Check for suspicious activity and send email alert if detected
            try:
                suspicious_detections = []
                suspicious_keywords = ['suspicious_activity', 'weapon', 'thief', 'fight', 'fire']
                
                # Helper to check if prediction contains suspicious keyword
                def is_suspicious(pred):
                    if pred == "N/A" or pred is None:
                        return False
                    pred_lower = str(pred).lower().strip()
                    return any(keyword in pred_lower for keyword in suspicious_keywords)
                
                if is_suspicious(pred_text):
                    suspicious_detections.append(f"Text: {pred_text}")
                    app.logger.info(f"Suspicious text detected: {pred_text}")
                
                if is_suspicious(pred_image):
                    suspicious_detections.append(f"Image: {pred_image}")
                    app.logger.info(f"Suspicious image detected: {pred_image}")
                
                if is_suspicious(pred_both):
                    suspicious_detections.append(f"Combined: {pred_both}")
                    app.logger.info(f"Suspicious combined detection: {pred_both}")
                
                if is_suspicious(pred_video):
                    suspicious_detections.append(f"Video: {pred_video}")
                    app.logger.info(f"Suspicious video detected: {pred_video}")
                
                app.logger.info(f"Total suspicious detections found: {len(suspicious_detections)}")
                
                # Send email if suspicious activity detected AND email is enabled
                if suspicious_detections:
                    if EMAIL_CONFIG.get('enabled', False):
                        user = User.query.get(session['user_id'])
                        if user and user.email:
                            detection_detail = "\n".join(suspicious_detections)
                            
                            # Determine primary detection type
                            detection_type = "SUSPICIOUS_ACTIVITY"
                            if 'weapon' in detection_detail.lower():
                                detection_type = "WEAPON_DETECTED"
                            elif 'thief' in detection_detail.lower():
                                detection_type = "THIEF_DETECTED"
                            elif 'fight' in detection_detail.lower():
                                detection_type = "FIGHT_DETECTED"
                            elif 'fire' in detection_detail.lower():
                                detection_type = "FIRE_DETECTED"
                            
                            predictions_dict = {
                                'pred_text': pred_text,
                                'pred_image': pred_image,
                                'pred_both': pred_both,
                                'pred_video': pred_video
                            }
                            
                            app.logger.info(f"Sending {detection_type} alert to {user.email}")
                            email_sent = send_email_alert(
                                user.email,
                                detection_type,
                                detail_text=detection_detail,
                                predictions=predictions_dict,
                                user_id=session['user_id']
                            )
                            
                            if email_sent:
                                app.logger.info(f"✅ Email alert sent to {user.email} for {detection_type}")
                                flash(f'⚠️ Suspicious activity detected! Alert sent to {user.email}', 'warning')
                            else:
                                app.logger.warning(f"Email alert failed for {user.email}")
                                flash(f'⚠️ Suspicious activity detected! Email notification failed.', 'warning')
                        else:
                            app.logger.warning(f"No user or email found for user_id {session['user_id']}")
                    else:
                        app.logger.info("Suspicious activity detected but email is disabled. Enable it in config_email.py")
                        flash('⚠️ Suspicious activity detected! (Email notifications disabled)', 'warning')
                    
            except Exception as e:
                app.logger.error(f"Error checking/sending email alert: {str(e)}")
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "pred_text": pred_text,
                    "pred_image": pred_image,
                    "pred_both": pred_both,
                    "pred_video": pred_video,
                    "video_frame_preds": video_frame_preds,
                    "ai_report": ai_report,
                    "video_url": video_url,
                    "original_video_url": original_video_url,
                    "image_url": image_url
                })
            
            # Regular form submission response
            return render_template("analyze.html",
                                pred_text=pred_text,
                                pred_image=pred_image,
                                pred_both=pred_both,
                                pred_video=pred_video,
                                video_frame_preds=video_frame_preds,
                                ai_report=ai_report,
                                video_url=video_url,
                                original_video_url=original_video_url,
                                image_url=image_url,
                                sample_text=sample_text)
        
        except Exception as e:
            import traceback
            error_msg = f"Analysis error: {str(e)}"
            error_trace = traceback.format_exc()
            app.logger.error(f"{error_msg}\n{error_trace}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": error_msg}), 500
            flash(error_msg, 'danger')
            return redirect(url_for('analyze'))
    
    # GET request - show empty form
    return render_template("analyze.html")

@app.route('/admin')
@login_required
def admin():
    if not session.get('is_admin'):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/alerts')
@login_required
def admin_alerts():
    """View email alert history"""
    if not session.get('is_admin'):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Get all alerts or filter by user/status
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        
        query = EmailAlertLog.query
        
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        # Paginate results (20 per page)
        alerts = query.order_by(EmailAlertLog.sent_at.desc()).paginate(page=page, per_page=20)
        
        # Get statistics
        total_alerts = EmailAlertLog.query.count()
        sent_count = EmailAlertLog.query.filter_by(status='sent').count()
        failed_count = EmailAlertLog.query.filter_by(status='failed').count()
        
        return render_template('admin_alerts.html', 
                             alerts=alerts,
                             total_alerts=total_alerts,
                             sent_count=sent_count,
                             failed_count=failed_count,
                             status_filter=status_filter)
    except Exception as e:
        app.logger.error(f"Error loading alerts page: {str(e)}")
        flash(f'Error loading alerts: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route('/api/alert-stats')
@login_required
def alert_stats():
    """API endpoint for alert statistics"""
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        total = EmailAlertLog.query.count()
        sent = EmailAlertLog.query.filter_by(status='sent').count()
        failed = EmailAlertLog.query.filter_by(status='failed').count()
        
        # Get alerts by type
        alerts_by_type = {}
        for alert_type in ['SUSPICIOUS_ACTIVITY', 'WEAPON_DETECTED', 'THIEF_DETECTED', 'FIGHT_DETECTED', 'FIRE_DETECTED']:
            count = EmailAlertLog.query.filter_by(detection_type=alert_type).count()
            if count > 0:
                alerts_by_type[alert_type] = count
        
        return jsonify({
            "total": total,
            "sent": sent,
            "failed": failed,
            "by_type": alerts_by_type
        })
    except Exception as e:
        app.logger.error(f"Error getting alert stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Global error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Internal server error: {str(error)}', exc_info=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"error": "Internal server error. Please try again later."}), 500
    flash('Internal server error. Please try again later.', 'danger')
    return redirect(url_for('home')), 500

@app.errorhandler(404)
def not_found(error):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"error": "Resource not found"}), 404
    return render_template('home.html'), 404

if __name__ == '__main__':
    print("\n" + "="*60)
    print("[STARTUP] SUSPICIOUS ACTIVITY DETECTION WEB APP")
    print("="*60)
    print("[STARTUP] Flask app initializing...")
    print("[STARTUP] Database: SQLite")
    print("[STARTUP] Model Status:", "LOADED" if model is not None else "NOT LOADED")
    print("[STARTUP] Server starting on http://127.0.0.1:5000")
    print("="*60 + "\n")
    logger.info(f"Application starting. Model loaded: {model is not None}")
    app.run(debug=True, use_reloader=False)