import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    def __init__(self):
        pass

    def send_confirmation(
        self,
        sender: str,
        app_password: str,
        recipient: str,
        name: str,
        job: dict,
        status: str
    ) -> tuple[bool, str]:
        try:
            job_title = job.get("title", "Position")
            company = job.get("company", "Company")
            source = job.get("source", "Unknown")
            url = job.get("url", "")
            applied_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")

            status_color = "#22c55e" if status.lower() in ["success", "applied", "sent"] else "#ef4444"
            status_text = "Application Sent! 🎉" if status.lower() in ["success", "applied", "sent"] else "Application Failed 😔"

            html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #3b82f6; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .status-badge {{ display: inline-block; background: {status_color}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin: 20px 0; }}
        .job-details {{ background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .checklist {{ margin: 20px 0; }}
        .checklist-item {{ margin: 10px 0; padding: 10px; background: #f9fafb; border-radius: 4px; }}
        .footer {{ text-align: center; color: #6b7280; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hello {name}!</h1>
        <p>Your AI Job Application Agent has an update</p>
    </div>

    <div style="text-align: center;">
        <div class="status-badge">{status_text}</div>
    </div>

    <div class="job-details">
        <h2>Job Details</h2>
        <p><strong>Position:</strong> {job_title}</p>
        <p><strong>Company:</strong> {company}</p>
        <p><strong>Source:</strong> {source}</p>
        <p><strong>Applied:</strong> {applied_time}</p>
        {f'<p><strong>URL:</strong> <a href="{url}">View Job</a></p>' if url else ''}
    </div>

    <div class="checklist">
        <h3>Next Steps Checklist</h3>
        <div class="checklist-item">✅ Follow up in 5-7 days if no response</div>
        <div class="checklist-item">📋 Prepare for potential screening call</div>
        <div class="checklist-item">🔍 Research {company} more thoroughly</div>
        <div class="checklist-item">💼 Keep applying to similar roles</div>
    </div>

    <div class="footer">
        <p>Sent by your AI Job Application Agent</p>
        <p>You're one step closer to your dream job! 🚀</p>
    </div>
</body>
</html>
            """

            msg = MIMEMultipart("alternative")
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Job Application Update: {job_title} at {company}"
            
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, app_password)
                server.send_message(msg)
            
            return (True, "Email sent successfully")

        except smtplib.SMTPAuthenticationError:
            return (False, "Authentication failed. Please check your Gmail App Password.")
        except Exception as e:
            return (False, f"Failed to send email: {str(e)}")

    def send_interview_prep(
        self,
        sender: str,
        app_password: str,
        recipient: str,
        name: str,
        job: dict,
        prep_content: str
    ) -> tuple[bool, str]:
        try:
            job_title = job.get("title", "Position")
            company = job.get("company", "Company")

            html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #10b981; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .section {{ margin: 20px 0; padding: 20px; background: #f3f4f6; border-radius: 8px; }}
        h2 {{ color: #1f2937; }}
        pre {{ white-space: pre-wrap; background: #1f2937; color: #f9fafb; padding: 15px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Interview Prep Pack Ready! 📚</h1>
        <p>For your {job_title} interview at {company}</p>
    </div>

    <div class="section">
        <h2>Your Interview Preparation Guide</h2>
        <pre>{prep_content}</pre>
    </div>

    <div style="text-align: center; margin-top: 30px; color: #6b7280;">
        <p>Good luck with your interview! You've got this! 💪</p>
    </div>
</body>
</html>
            """

            msg = MIMEMultipart("alternative")
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Interview Prep: {job_title} at {company}"
            
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, app_password)
                server.send_message(msg)
            
            return (True, "Interview prep email sent successfully")

        except Exception as e:
            return (False, f"Failed to send email: {str(e)}")

    def send_daily_digest(
        self,
        sender: str,
        app_password: str,
        recipient: str,
        name: str,
        stats: dict,
        recent_jobs: list
    ) -> tuple[bool, str]:
        try:
            today = datetime.now().strftime("%B %d, %Y")
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #8b5cf6; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }}
        .stat-card {{ background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #3b82f6; }}
        .job-card {{ background: #f9fafb; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #3b82f6; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Daily Digest 📊</h1>
        <p>{today}</p>
    </div>

    <h2>Hi {name}! Here's your job search update</h2>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{stats.get('total', 0)}</div>
            <div>Total Applications</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{stats.get('applied', 0)}</div>
            <div>Applied Today</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{stats.get('success_rate', 0)}%</div>
            <div>Success Rate</div>
        </div>
    </div>

    <h3>Recent Applications</h3>
    {''.join([f'<div class="job-card"><strong>{job.get("title", "")}</strong><br>{job.get("company", "")}<br><span style="color: #6b7280;">{job.get("stage", "Saved")}</span></div>' for job in recent_jobs[:3]])}

    <div style="text-align: center; margin-top: 30px; color: #6b7280;">
        <p>Keep up the great work! Consistency is key! 🔑</p>
    </div>
</body>
</html>
            """

            msg = MIMEMultipart("alternative")
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Job Search Digest - {today}"
            
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, app_password)
                server.send_message(msg)
            
            return (True, "Daily digest sent successfully")

        except Exception as e:
            return (False, f"Failed to send email: {str(e)}")
