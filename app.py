# JobSpy Flask App — build: 2026-06-08
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
import secrets as _secrets
app.secret_key = os.getenv('SECRET_KEY') or _secrets.token_hex(32)

# Email Configuration (users should set these as environment variables)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')


def detect_country(location):
    """Detect country from location string"""
    location_lower = location.lower()
    if 'india' in location_lower:
        return 'India'
    elif 'canada' in location_lower:
        return 'Canada'
    elif 'uk' in location_lower or 'united kingdom' in location_lower or 'britain' in location_lower:
        return 'UK'
    elif 'australia' in location_lower:
        return 'Australia'
    elif 'germany' in location_lower:
        return 'Germany'
    elif 'france' in location_lower:
        return 'France'
    elif 'singapore' in location_lower:
        return 'Singapore'
    return 'USA'


def format_salary(job):
    """Format salary info from a job row"""
    min_amt = job.get('min_amount')
    max_amt = job.get('max_amount')
    currency = job.get('currency', 'USD') or 'USD'
    interval = job.get('interval', '') or ''

    if min_amt and max_amt and str(min_amt) not in ['nan', 'None', '']:
        try:
            min_val = int(float(min_amt))
            max_val = int(float(max_amt))
            symbol = '$' if 'USD' in str(currency).upper() else str(currency)
            period = f'/{interval}' if interval else ''
            return f"{symbol}{min_val:,} – {symbol}{max_val:,}{period}"
        except (ValueError, TypeError):
            pass
    return None


def clean_jobs_for_display(jobs_df, limit=20):
    """Convert jobs dataframe to clean JSON-serializable list"""
    jobs_list = []
    for _, job in jobs_df.head(limit).iterrows():
        description = str(job.get('description', '') or '')
        if len(description) > 400:
            description = description[:400].rsplit(' ', 1)[0] + '…'

        date_posted = job.get('date_posted', '')
        if date_posted and str(date_posted) not in ['nan', 'None', '']:
            try:
                dt = pd.to_datetime(date_posted)
                date_posted = dt.strftime('%b %d, %Y')
            except Exception:
                date_posted = str(date_posted)[:10]
        else:
            date_posted = 'Recently'

        jobs_list.append({
            'title': str(job.get('title', 'Untitled')) or 'Untitled',
            'company': str(job.get('company', 'Unknown Company')) or 'Unknown Company',
            'location': str(job.get('location', 'Remote')) or 'Remote',
            'job_type': str(job.get('job_type', '')) or '',
            'date_posted': date_posted,
            'salary': format_salary(job),
            'job_url': str(job.get('job_url', '#')) or '#',
            'description': description,
            'site': str(job.get('site', '')) or '',
            'is_remote': bool(job.get('is_remote', False)),
        })
    return jobs_list


def scrape_and_send_jobs(job_role, location, email, results_wanted=10, experience_level=None):
    """Scrape jobs and send email notification"""
    try:
        country_indeed = detect_country(location)

        scrape_params = {
            "site_name": ["indeed", "linkedin", "zip_recruiter", "glassdoor"],
            "search_term": job_role,
            "location": location,
            "results_wanted": results_wanted,
            "hours_old": 72,
            "country_indeed": country_indeed
        }

        if experience_level and experience_level != 'all':
            scrape_params["job_type"] = experience_level

        jobs = scrape_jobs(**scrape_params)

        if jobs.empty:
            return {"status": "error", "message": "No jobs found matching your criteria"}

        if 'date_posted' in jobs.columns:
            jobs['date_posted'] = pd.to_datetime(jobs['date_posted'], errors='coerce')
            jobs = jobs.sort_values('date_posted', ascending=False, na_position='last')

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

    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f'Job Alert: {len(jobs_df)} {job_role} positions found!'

    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; background: #0f172a; }}
                .header {{ background: linear-gradient(135deg, #6366f1, #ec4899); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
                .content {{ padding: 24px; background: #1e293b; }}
                .job-card {{
                    border: 1px solid #334155;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 16px 0;
                    background: #0f172a;
                }}
                .job-title {{ color: #818cf8; font-size: 18px; font-weight: bold; text-decoration: none; }}
                .company {{ color: #94a3b8; font-size: 15px; margin: 6px 0; }}
                .location {{ color: #64748b; font-size: 13px; }}
                .salary {{ color: #10b981; font-weight: bold; margin: 8px 0; }}
                .description {{ margin-top: 10px; color: #cbd5e1; font-size: 14px; }}
                .footer {{ text-align: center; padding: 20px; color: #64748b; font-size: 12px; background: #1e293b; border-radius: 0 0 12px 12px; }}
                a {{ color: #818cf8; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 Job Alert: {job_role}</h1>
                <p>We found {len(jobs_df)} opportunities for you in {location}!</p>
            </div>
            <div class="content">
                <p style="color:#94a3b8;"><strong>Date:</strong> {datetime.now().strftime("%B %d, %Y")}</p>
                <hr style="border-color:#334155;">
    """

    for idx, job in jobs_df.head(10).iterrows():
        job_url = job.get('job_url', '#')
        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        job_location = job.get('location', 'N/A')
        description = job.get('description', 'No description available')
        salary = format_salary(job)

        if len(str(description)) > 300:
            description = str(description)[:300] + "..."

        salary_html = f"<p class='salary'>💰 {salary}</p>" if salary else ""

        html_body += f"""
            <div class="job-card">
                <div class="job-title"><a href="{job_url}" target="_blank">{title}</a></div>
                <div class="company">🏢 {company}</div>
                <div class="location">📍 {job_location}</div>
                {salary_html}
                <div class="description">{description}</div>
            </div>
        """

    if len(jobs_df) > 10:
        html_body += f"<p style='color:#94a3b8;'><em>...and {len(jobs_df) - 10} more jobs! See attached CSV for full list.</em></p>"

    html_body += """
            </div>
            <div class="footer">
                <p>This is an automated job alert from JobSpy</p>
                <p>Happy Job Hunting! 🚀</p>
            </div>
        </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

    try:
        csv_buffer = StringIO()
        jobs_df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jobs_{job_role.replace(' ', '_')}_{timestamp}.csv"
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(csv_content.encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(part)
    except Exception as e:
        print(f"Could not attach CSV: {e}")

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()
    print(f"Email sent successfully to {recipient_email}")


@app.route('/')
def index():
    """Home page with search form"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search_jobs():
    """Handle job search request with email notification"""
    try:
        job_role = request.form.get('job_role', '').strip()
        location = request.form.get('location', '').strip()
        email = request.form.get('email', '').strip()
        results_wanted = int(request.form.get('results_wanted', 10))
        experience_level = request.form.get('experience_level', 'all').strip()

        if not job_role:
            return jsonify({"status": "error", "message": "Job role is required"})
        if not email:
            return jsonify({"status": "error", "message": "Email is required"})
        if not location:
            location = "United States"

        def background_task():
            result = scrape_and_send_jobs(job_role, location, email, results_wanted, experience_level)
            print(result)

        thread = threading.Thread(target=background_task)
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"Job search started for '{job_role}' in {location}. Results will be emailed to {email} shortly!"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/search-jobs', methods=['POST'])
def api_search_jobs():
    """Search jobs and return results directly in the response for UI display"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid request body"})

        job_role = data.get('job_role', '').strip()
        location = data.get('location', 'United States').strip()
        results_wanted = min(int(data.get('results_wanted', 10)), 50)
        experience_level = data.get('experience_level', 'all').strip()

        if not job_role:
            return jsonify({"status": "error", "message": "Job role is required"})

        if not location:
            location = "United States"

        country_indeed = detect_country(location)

        scrape_params = {
            "site_name": ["indeed", "linkedin", "zip_recruiter", "glassdoor"],
            "search_term": job_role,
            "location": location,
            "results_wanted": results_wanted,
            "hours_old": 72,
            "country_indeed": country_indeed
        }

        if experience_level and experience_level != 'all':
            scrape_params["job_type"] = experience_level

        jobs = scrape_jobs(**scrape_params)

        if jobs.empty:
            return jsonify({
                "status": "success",
                "jobs": [],
                "count": 0,
                "message": "No jobs found. Try broadening your search."
            })

        if 'date_posted' in jobs.columns:
            jobs['date_posted'] = pd.to_datetime(jobs['date_posted'], errors='coerce')
            jobs = jobs.sort_values('date_posted', ascending=False, na_position='last')

        jobs_list = clean_jobs_for_display(jobs, limit=results_wanted)

        return jsonify({
            "status": "success",
            "jobs": jobs_list,
            "count": len(jobs_list),
            "total_found": len(jobs)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Search failed: {str(e)}"})


@app.route('/api/email-jobs', methods=['POST'])
def api_email_jobs():
    """Search jobs and email them"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid request body"})

        job_role = data.get('job_role', '').strip()
        location = data.get('location', 'United States').strip()
        email = data.get('email', '').strip()
        results_wanted = min(int(data.get('results_wanted', 10)), 100)
        experience_level = data.get('experience_level', 'all').strip()

        if not job_role:
            return jsonify({"status": "error", "message": "Job role is required"})
        if not email:
            return jsonify({"status": "error", "message": "Email address is required"})
        if not location:
            location = "United States"

        def background_task():
            result = scrape_and_send_jobs(job_role, location, email, results_wanted, experience_level)
            print(result)

        thread = threading.Thread(target=background_task)
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"We're searching for {job_role} jobs in {location} and will email the results to {email} shortly!"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')

    print("\n" + "="*70)
    print("🎯 JobSpy Application Starting...")
    print("="*70)
    print(f"\n📧 Email: {SENDER_EMAIL if SENDER_EMAIL else '❌ NOT CONFIGURED'}")

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("\n⚠️  Email not configured. Set SENDER_EMAIL and SENDER_PASSWORD env vars.")

    print("\n🚀 Server running at http://127.0.0.1:5000")
    print("="*70 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
