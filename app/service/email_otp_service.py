"""Email OTP Service for test verification."""

import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config.logger_config import log_central


class EmailOTPService:
    """Service for sending OTP emails."""

    def __init__(self):
        """Initialize email service."""
        # Email configuration - Update with your SMTP details
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "shamikpatoliya@gmail.com"  # Update this
        self.sender_password = "$@nket1122005"  # Update this
        self.enabled = False  # Set to True when email is configured

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP code."""
        return str(random.randint(100000, 999999))

    def send_otp_email(self, recipient_email: str, otp_code: str, test_title: str) -> bool:
        """
        Send OTP email to recipient.
        
        Args:
            recipient_email: Email address to send OTP to
            otp_code: 6-digit OTP code
            test_title: Title of the test
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            # For development/testing - just log the OTP
            log_central(
                f"📧 OTP Email (Dev Mode): {otp_code} for {recipient_email}",
                level="info"
            )
            print("\n" + "="*60)
            print("📧 OTP EMAIL (DEVELOPMENT MODE)")
            print("="*60)
            print(f"To: {recipient_email}")
            print(f"Test: {test_title}")
            print(f"OTP Code: {otp_code}")
            print(f"Valid for: 10 minutes")
            print("="*60 + "\n")
            return True

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Your OTP Code for {test_title}"
            message["From"] = self.sender_email
            message["To"] = recipient_email

            # Create HTML email body
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                  <h2 style="color: #667eea; margin-bottom: 20px;">Aptitude Test Verification</h2>
                  
                  <p style="font-size: 16px; color: #333; margin-bottom: 20px;">
                    You have requested access to the aptitude test:
                  </p>
                  
                  <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3 style="color: #495057; margin: 0;">{test_title}</h3>
                  </div>
                  
                  <p style="font-size: 16px; color: #333; margin-bottom: 10px;">
                    Your One-Time Password (OTP) is:
                  </p>
                  
                  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
                    <h1 style="color: white; margin: 0; font-size: 36px; letter-spacing: 8px;">{otp_code}</h1>
                  </div>
                  
                  <p style="font-size: 14px; color: #666; margin-top: 20px;">
                    <strong>Important:</strong>
                  </p>
                  <ul style="font-size: 14px; color: #666;">
                    <li>This OTP is valid for 10 minutes</li>
                    <li>Do not share this code with anyone</li>
                    <li>If you didn't request this, please ignore this email</li>
                  </ul>
                  
                  <hr style="border: none; border-top: 1px solid #e9ecef; margin: 30px 0;">
                  
                  <p style="font-size: 12px; color: #999; text-align: center;">
                    This is an automated email. Please do not reply.
                  </p>
                </div>
              </body>
            </html>
            """

            # Attach HTML part
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())

            log_central(
                f"OTP email sent successfully to {recipient_email}",
                level="info"
            )
            return True

        except Exception as e:
            log_central(
                f"Failed to send OTP email to {recipient_email}: {str(e)}",
                level="error"
            )
            return False

    def verify_otp(self, provided_otp: str, stored_otp: str) -> bool:
        """
        Verify if provided OTP matches stored OTP.
        
        Args:
            provided_otp: OTP code provided by user
            stored_otp: OTP code stored in database
            
        Returns:
            True if OTP matches, False otherwise
        """
        return provided_otp.strip() == stored_otp.strip()

