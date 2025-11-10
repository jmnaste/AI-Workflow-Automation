"""Email delivery service using SMTP."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


def get_smtp_config() -> Optional[dict]:
    """Get SMTP configuration from environment."""
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    from_email = os.environ.get("SMTP_FROM", "noreply@flovify.ca")
    
    if not all([host, user, password]):
        return None
    
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_email": from_email,
    }


def is_smtp_configured() -> bool:
    """Check if SMTP is configured."""
    return get_smtp_config() is not None


def send_otp_email(email: str, otp: str) -> bool:
    """Send OTP via email.
    
    Args:
        email: Recipient email address
        otp: 6-digit OTP code
    
    Returns:
        True if sent successfully, False otherwise
    """
    config = get_smtp_config()
    if not config:
        raise ValueError("SMTP not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASS")
    
    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Flovify Verification Code"
    msg["From"] = config["from_email"]
    msg["To"] = email
    
    # Plain text version
    text = f"""Your Flovify verification code is: {otp}

This code expires in 5 minutes.

Never share this code with anyone.

If you didn't request this code, please ignore this email.
"""
    
    # HTML version
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #5865f2;
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            text-align: center;
        }}
        .content h2 {{
            color: #333;
            margin: 0 0 20px 0;
            font-size: 24px;
        }}
        .otp-code {{
            background: #f0f2f5;
            border: 2px solid #5865f2;
            border-radius: 8px;
            padding: 20px;
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
            color: #5865f2;
            margin: 30px 0;
            font-family: 'Courier New', monospace;
        }}
        .warning {{
            color: #e74c3c;
            font-weight: 600;
            margin-top: 20px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Flovify</h1>
        </div>
        <div class="content">
            <h2>Your Verification Code</h2>
            <p>Enter this code to sign in:</p>
            <div class="otp-code">{otp}</div>
            <p>This code expires in 5 minutes.</p>
            <p class="warning">⚠️ Never share this code with anyone.</p>
        </div>
        <div class="footer">
            <p>If you didn't request this code, please ignore this email.</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Attach both versions
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # Connect and send
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls()
            server.login(config["user"], config["password"])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False
