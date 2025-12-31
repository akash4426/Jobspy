# JobSpy - Job Search with Email Notifications 🎯

An interactive web application that searches for jobs across multiple platforms and sends results via email.

## Features ✨

- 🔍 **Multi-Platform Search**: Searches Indeed, LinkedIn, ZipRecruiter, and Glassdoor
- 📧 **Email Notifications**: Sends beautiful HTML emails with job listings
- 📎 **CSV Attachments**: Includes a CSV file with all job details
- 🎨 **Modern UI**: Clean, responsive web interface
- ⚡ **Real-time Updates**: Asynchronous job scraping
- 🌐 **Multiple Locations**: Search jobs anywhere in the US

## Installation 🚀

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Email Settings**

For Gmail (Recommended):
- Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
- Generate a new app password
- Set environment variables:

```bash
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="your-app-password"
```

For other email providers:
```bash
export SMTP_SERVER="smtp.office365.com"  # For Outlook
export SMTP_PORT="587"
export SENDER_EMAIL="your-email@outlook.com"
export SENDER_PASSWORD="your-password"
```

## Usage 📖

1. **Start the Application**
```bash
python app.py
```

2. **Open Your Browser**
Navigate to: `http://127.0.0.1:5000`

3. **Search for Jobs**
- Enter job role (e.g., "Software Engineer")
- Enter location (e.g., "New York")
- Enter your email address
- Click "Search & Send to Email"

4. **Check Your Email**
You'll receive a detailed email with:
- Top 10 job listings with clickable links
- Company names and locations
- Job descriptions
- CSV attachment with complete results

## Configuration ⚙️

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SENDER_EMAIL` | Email address to send from | Required |
| `SENDER_PASSWORD` | Email password/app password | Required |
| `SMTP_SERVER` | SMTP server address | smtp.gmail.com |
| `SMTP_PORT` | SMTP port number | 587 |

### Email Provider Settings

**Gmail:**
- SMTP Server: `smtp.gmail.com`
- Port: `587`
- Enable "Less secure app access" or use App Password

**Outlook/Office365:**
- SMTP Server: `smtp.office365.com`
- Port: `587`

**Yahoo:**
- SMTP Server: `smtp.mail.yahoo.com`
- Port: `587`

## API Endpoints 🛠️

### POST /search
Initiates job search and sends email notification.

**Parameters:**
- `job_role` (required): Job title or role
- `location` (required): Location to search
- `email` (required): Recipient email address
- `results_wanted` (optional): Number of results (default: 10)

### POST /quick-search
Returns job results directly without email (for testing).

**JSON Parameters:**
```json
{
  "job_role": "Data Scientist",
  "location": "San Francisco",
  "results_wanted": 5
}
```

## Troubleshooting 🔧

### Email Not Sending

1. **Gmail Users**: Make sure you're using an App Password, not your regular password
   - Visit: https://myaccount.google.com/apppasswords
   - Enable 2-Step Verification first
   - Generate app password for "Mail"

2. **Check Credentials**: Verify environment variables are set correctly
```bash
echo $SENDER_EMAIL
echo $SENDER_PASSWORD
```

3. **Firewall/Port Issues**: Ensure port 587 is not blocked

### No Jobs Found

- Try broader search terms
- Check if location is valid
- Verify internet connection
- Some job boards may have rate limits

### Module Not Found

```bash
pip install -r requirements.txt --upgrade
```

## Example Email Output 📬

The email you receive will include:
- **Subject**: "Job Alert: X Software Engineer positions found!"
- **Body**: Formatted HTML with job cards showing:
  - Job title (clickable link)
  - Company name
  - Location
  - Salary (if available)
  - Job description preview
- **Attachment**: CSV file with all job details

## Advanced Usage 🚀

### Schedule Automated Job Searches

Use cron (Linux/Mac) or Task Scheduler (Windows):

```bash
# Example cron job - search every day at 9 AM
0 9 * * * cd /path/to/Jobspy && python -c "from app import scrape_and_send_jobs; scrape_and_send_jobs('Software Engineer', 'Remote', 'your@email.com', 20)"
```

### Customize Email Template

Edit the HTML template in `app.py` function `send_email_notification()` to customize:
- Colors and styling
- Email layout
- Additional job details

## Dependencies 📦

- **Flask**: Web framework
- **python-jobspy**: Job scraping library
- **pandas**: Data manipulation
- **smtplib**: Email sending

## Security Notes 🔒

- Never commit `.env` files or credentials to version control
- Use environment variables for sensitive data
- Use app-specific passwords when available
- Keep dependencies updated

## Contributing 🤝

Feel free to submit issues, fork the repository, and create pull requests!

## License 📄

MIT License - feel free to use this project for personal or commercial purposes.

## Support 💬

For issues related to:
- **python-jobspy**: Visit [JobSpy GitHub](https://github.com/Bunsly/JobSpy)
- **This application**: Create an issue in this repository

---

**Happy Job Hunting! 🎉**
