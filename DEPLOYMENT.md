# 🚀 Deployment Guide - JobSpy Application

## Quick Start (Local Development)

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env with your email credentials
```

3. **Run the Application**
```bash
python app.py
```

Visit: http://127.0.0.1:5000

---

## 📦 Production Deployment Options

### Option 1: Heroku (Recommended for Beginners)

1. **Install Heroku CLI**
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Windows
# Download from: https://devcenter.heroku.com/articles/heroku-cli
```

2. **Login and Create App**
```bash
heroku login
heroku create your-jobspy-app
```

3. **Set Environment Variables**
```bash
heroku config:set SENDER_EMAIL="your-email@gmail.com"
heroku config:set SENDER_PASSWORD="your-app-password"
heroku config:set SMTP_SERVER="smtp.gmail.com"
heroku config:set SMTP_PORT="587"
```

4. **Deploy**
```bash
git init
git add .
git commit -m "Initial deployment"
git push heroku main
```

5. **Open Your App**
```bash
heroku open
```

**Cost**: Free tier available (550-1000 dyno hours/month)

---

### Option 2: AWS EC2

1. **Launch EC2 Instance** (Ubuntu 22.04 LTS recommended)

2. **SSH into Instance**
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

3. **Install Dependencies**
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx -y
```

4. **Setup Application**
```bash
git clone your-repo-url
cd Jobspy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. **Create .env File**
```bash
nano .env
# Add your credentials
```

6. **Run with Gunicorn**
```bash
gunicorn app:app --bind 0.0.0.0:5000 --workers 4 --daemon
```

7. **Configure Nginx (Optional)**
```bash
sudo nano /etc/nginx/sites-available/jobspy
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/jobspy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

8. **Setup as System Service**
```bash
sudo nano /etc/systemd/system/jobspy.service
```

Add:
```ini
[Unit]
Description=JobSpy Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Jobspy
Environment="PATH=/home/ubuntu/Jobspy/venv/bin"
ExecStart=/home/ubuntu/Jobspy/venv/bin/gunicorn app:app --bind 0.0.0.0:5000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable jobspy
sudo systemctl start jobspy
```

**Cost**: Starting at ~$5-10/month for t2.micro

---

### Option 3: DigitalOcean App Platform

1. **Create Account** at digitalocean.com

2. **Create New App** → Import from GitHub

3. **Configure Build Settings**
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `gunicorn app:app --workers 2`

4. **Set Environment Variables** in App Settings

5. **Deploy** → Your app will be live!

**Cost**: Starting at $5/month

---

### Option 4: Google Cloud Run (Serverless)

1. **Create Dockerfile**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

2. **Build and Deploy**
```bash
gcloud builds submit --tag gcr.io/your-project/jobspy
gcloud run deploy jobspy --image gcr.io/your-project/jobspy --platform managed
```

3. **Set Environment Variables** in Cloud Run Console

**Cost**: Pay-per-use (very cheap for low traffic)

---

### Option 5: Render (Easiest)

1. **Sign up** at render.com

2. **New Web Service** → Connect GitHub repo

3. **Configure**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

4. **Add Environment Variables** in dashboard

5. **Deploy** → Done!

**Cost**: Free tier available, paid starts at $7/month

---

## 🔐 Security Best Practices

### 1. Environment Variables
Never commit `.env` file to git. Always use environment variables for:
- Email credentials
- API keys
- Secret keys

### 2. HTTPS/SSL
Always use HTTPS in production. Most platforms provide free SSL:
- Heroku: Automatic
- AWS: Use AWS Certificate Manager
- Others: Let's Encrypt (free)

### 3. Rate Limiting
Add rate limiting to prevent abuse:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/search', methods=['POST'])
@limiter.limit("10 per hour")
def search_jobs():
    # ... existing code
```

### 4. CORS (if needed)
```python
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "https://yourdomain.com"}})
```

---

## 📊 Monitoring & Logging

### Add Logging
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Error Tracking
Consider adding Sentry:
```bash
pip install sentry-sdk[flask]
```

```python
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn")
```

---

## 🎯 Performance Optimization

1. **Use Redis for Caching** (optional)
2. **Add CDN** for static assets
3. **Database** for job history (optional)
4. **Background Queue** (Celery) for long-running tasks

---

## 🔄 Continuous Deployment

### GitHub Actions (Free)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-app-name"
        heroku_email: "your-email@example.com"
```

---

## 📈 Scaling Considerations

- **Horizontal Scaling**: Add more workers/instances
- **Caching**: Cache job search results (Redis)
- **Database**: Store results for analytics
- **CDN**: CloudFlare for global distribution
- **Load Balancer**: Distribute traffic

---

## 🆘 Troubleshooting

### Email Not Sending
- Verify SMTP credentials
- Check firewall/port 587
- Enable "Less secure apps" for Gmail (or use App Password)

### Slow Performance
- Increase worker count
- Add caching
- Optimize job scraping queries

### Out of Memory
- Reduce results_wanted limit
- Increase dyno/instance size
- Implement pagination

---

## 📞 Support

For issues:
1. Check logs: `heroku logs --tail` or system logs
2. Verify environment variables
3. Test email configuration locally first

---

## ✅ Pre-Deployment Checklist

- [ ] Email credentials configured
- [ ] `.env` added to `.gitignore`
- [ ] Secret key changed from default
- [ ] HTTPS enabled
- [ ] Error pages customized
- [ ] Rate limiting added
- [ ] Monitoring setup
- [ ] Backup strategy defined
- [ ] Domain name configured (if applicable)
- [ ] Analytics added (Google Analytics, etc.)

---

**Ready to deploy! 🚀**

Choose your platform and follow the steps above. Good luck!
