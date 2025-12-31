from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from jobspy import scrape_jobs
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime
import threading
from dotenv import load_dotenv
from io import StringIO

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Email Configuration (users should set these as environment variables)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')

def scrape_and_send_jobs(job_role, location, email, results_wanted=10, experience_level=None):
    """Scrape jobs and send email notification"""
    try:
        # Detect country from location
        location_lower = location.lower()
        country_indeed = 'USA'  # default
        
        if 'india' in location_lower:
            country_indeed = 'India'
        elif 'canada' in location_lower:
            country_indeed = 'Canada'
        elif 'uk' in location_lower or 'united kingdom' in location_lower or 'britain' in location_lower:
            country_indeed = 'UK'
        elif 'australia' in location_lower:
            country_indeed = 'Australia'
        elif 'germany' in location_lower:
            country_indeed = 'Germany'
        elif 'france' in location_lower:
            country_indeed = 'France'
        elif 'singapore' in location_lower:
            country_indeed = 'Singapore'
        
        # Prepare scraping parameters
        scrape_params = {
            "site_name": ["indeed", "linkedin", "zip_recruiter", "glassdoor"],
            "search_term": job_role,
            "location": location,
            "results_wanted": results_wanted,
            "hours_old": 72,
            "country_indeed": country_indeed
        }
        
        # Add experience level if specified
        if experience_level and experience_level != 'all':
            scrape_params["job_type"] = experience_level
        
        # Scrape jobs using jobspy
        jobs = scrape_jobs(**scrape_params)
        
        if jobs.empty:
            return {"status": "error", "message": "No jobs found matching your criteria"}
        
        # Sort by date_posted to get earliest (most recent) postings first
        if 'date_posted' in jobs.columns:
            jobs['date_posted'] = pd.to_datetime(jobs['date_posted'], errors='coerce')
            jobs = jobs.sort_values('date_posted', ascending=False, na_position='last')
        
        # Send email with results (CSV will be created in memory)
        send_email_notification(email, job_role, location, jobs)
        
        return {
            "status": "success", 
            "message": f"Found {len(jobs)} jobs! Email sent to {email}",
            "jobs_count": len(jobs)
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}

def send_email_notification(recipient_email, job_role, location, jobs_df):
    """Send email with job listings"""
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        raise Exception("Email credentials not configured. Please set SENDER_EMAIL and SENDER_PASSWORD environment variables.")
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f'Job Alert: {len(jobs_df)} {job_role} positions found!'
    
    # Create HTML email body
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .job-card {{ 
                    border: 1px solid #ddd; 
                    border-radius: 8px; 
                    padding: 15px; 
                    margin: 15px 0;
                    background-color: #f9f9f9;
                }}
                .job-title {{ color: #2196F3; font-size: 18px; font-weight: bold; }}
                .company {{ color: #666; font-size: 16px; }}
                .location {{ color: #888; font-size: 14px; }}
                .salary {{ color: #4CAF50; font-weight: bold; }}
                .description {{ margin-top: 10px; color: #555; }}
                .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
                a {{ color: #2196F3; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 Job Alert: {job_role}</h1>
                <p>We found {len(jobs_df)} opportunities for you!</p>
            </div>
            <div class="content">
                <p><strong>Search Location:</strong> {location}</p>
                <p><strong>Date:</strong> {datetime.now().strftime("%B %d, %Y")}</p>
                <hr>
    """
    
    # Add top 10 jobs to email body
    for idx, job in jobs_df.head(10).iterrows():
        job_url = job.get('job_url', '#')
        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        job_location = job.get('location', 'N/A')
        description = job.get('description', 'No description available')
        salary = job.get('min_amount', '')
        
        # Truncate description
        if len(str(description)) > 300:
            description = str(description)[:300] + "..."
        
        salary_text = f"<p class='salary'>Salary: ${salary}</p>" if salary else ""
        
        html_body += f"""
            <div class="job-card">
                <div class="job-title"><a href="{job_url}" target="_blank">{title}</a></div>
                <div class="company">🏢 {company}</div>
                <div class="location">📍 {job_location}</div>
                {salary_text}
                <div class="description">{description}</div>
            </div>
        """
    
    if len(jobs_df) > 10:
        html_body += f"<p><em>...and {len(jobs_df) - 10} more jobs! See attached CSV for full list.</em></p>"
    
    html_body += """
            </div>
            <div class="footer">
                <p>This is an automated job alert from JobSpy Application</p>
                <p>Happy Job Hunting! 🚀</p>
            </div>
        </body>
    </html>
    """
    
    # Attach HTML body
    msg.attach(MIMEText(html_body, 'html'))
    
    # Create CSV in memory and attach
    try:
        # Create CSV in memory
        csv_buffer = StringIO()
        jobs_df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jobs_{job_role.replace(' ', '_')}_{timestamp}.csv"
        
        # Attach CSV
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(csv_content.encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(part)
    except Exception as e:
        print(f"Could not attach CSV: {e}")
    
    # Send email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

@app.route('/')
def index():
    """Home page with search form"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_jobs():
    """Handle job search request"""
    try:
        job_role = request.form.get('job_role', '').strip()
        location = request.form.get('location', '').strip()
        email = request.form.get('email', '').strip()
        results_wanted = int(request.form.get('results_wanted', 10))
        experience_level = request.form.get('experience_level', 'all').strip()
        
        # Validation
        if not job_role:
            return jsonify({"status": "error", "message": "Job role is required"})
        if not email:
            return jsonify({"status": "error", "message": "Email is required"})
        if not location:
            location = "United States"
        
        # Run job scraping in background thread
        def background_task():
            result = scrape_and_send_jobs(job_role, location, email, results_wanted, experience_level)
            print(result)
        
        thread = threading.Thread(target=background_task)
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": f"Job search initiated for '{job_role}' in {location}. You'll receive an email at {email} shortly!"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/quick-search', methods=['POST'])
def quick_search():
    """Quick search that returns results directly without email"""
    try:
        data = request.get_json()
        job_role = data.get('job_role', '').strip()
        location = data.get('location', 'United States').strip()
        results_wanted = int(data.get('results_wanted', 5))
        experience_level = data.get('experience_level', 'all').strip()
        
        if not job_role:
            return jsonify({"status": "error", "message": "Job role is required"})
        
        # Detect country from location
        location_lower = location.lower()
        country_indeed = 'USA'
        
        if 'india' in location_lower:
            country_indeed = 'India'
        elif 'canada' in location_lower:
            country_indeed = 'Canada'
        elif 'uk' in location_lower or 'united kingdom' in location_lower:
            country_indeed = 'UK'
        elif 'australia' in location_lower:
            country_indeed = 'Australia'
        
        # Prepare scraping parameters
        scrape_params = {
            "site_name": ["indeed", "linkedin"],
            "search_term": job_role,
            "location": location,
            "results_wanted": results_wanted,
            "hours_old": 72,
            "country_indeed": country_indeed
        }
        
        # Add experience level if specified
        if experience_level and experience_level != 'all':
            scrape_params["job_type"] = experience_level
        
        # Scrape jobs
        jobs = scrape_jobs(**scrape_params)
        
        if jobs.empty:
            return jsonify({"status": "success", "jobs": [], "message": "No jobs found"})
        
        # Sort by date_posted to get earliest (most recent) postings first
        if 'date_posted' in jobs.columns:
            jobs['date_posted'] = pd.to_datetime(jobs['date_posted'], errors='coerce')
            jobs = jobs.sort_values('date_posted', ascending=False, na_position='last')
        
        # Convert to list of dictionaries
        jobs_list = jobs.head(results_wanted).to_dict('records')
        
        return jsonify({
            "status": "success",
            "jobs": jobs_list,
            "count": len(jobs_list)
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("\n" + "="*70)
    print("🎯 JobSpy Application Starting...")
    print("="*70)
    print("\n📧 Email Configuration:")
    print(f"   SMTP Server: {SMTP_SERVER}")
    print(f"   SMTP Port: {SMTP_PORT}")
    print(f"   Sender Email: {SENDER_EMAIL if SENDER_EMAIL else '❌ NOT CONFIGURED'}")
    print(f"   Password: {'✅ SET' if SENDER_PASSWORD else '❌ NOT SET'}")
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("\n⚠️  WARNING: Email credentials not configured!")
        print("   To configure email, set these environment variables:")
        print("   export SENDER_EMAIL='your-email@gmail.com'")
        print("   export SENDER_PASSWORD='your-app-password'")
        print("\n   Or create a .env file with:")
        print("   SENDER_EMAIL=your-email@gmail.com")
        print("   SENDER_PASSWORD=your-app-password")
    
    print("\n" + "="*70)
    print("🚀 Server running at http://127.0.0.1:5000")
    print("   Press CTRL+C to stop the server")
    print("="*70 + "\n")
    
    # Production: use app.run(host='0.0.0.0', port=5000)
    # Development: use debug=True
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
