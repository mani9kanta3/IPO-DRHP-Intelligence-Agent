# AWS EC2 Deployment Guide — IPO DRHP Intelligence Agent

## Step 1: Launch EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance
2. Settings:
   - Name: drhp-agent
   - AMI: Ubuntu Server 22.04 LTS (Free tier eligible)
   - Instance type: t2.micro (free tier) or t2.small (recommended)
   - Key pair: Create new → download .pem file → save safely
   - Security Group — Add these inbound rules:
     - SSH: Port 22, Source: My IP
     - Custom TCP: Port 8000, Source: 0.0.0.0/0 (FastAPI)
     - Custom TCP: Port 8501, Source: 0.0.0.0/0 (Streamlit)
3. Click Launch Instance
4. Note your EC2 Public IP address

---

## Step 2: Connect to EC2

```bash
# Windows PowerShell
ssh -i "your-key.pem" ubuntu@YOUR-EC2-IP

# If permission error on Windows:
icacls "your-key.pem" /inheritance:r /grant:r "%username%:R"
```

---

## Step 3: Install Docker on EC2

```bash
# Update system
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add ubuntu user to docker group (no sudo needed)
sudo usermod -aG docker ubuntu

# Logout and login again for group change to take effect
exit
```

Reconnect:
```bash
ssh -i "your-key.pem" ubuntu@YOUR-EC2-IP
```

Verify Docker works:
```bash
docker --version
docker-compose --version
```

---

## Step 4: Clone Your Project

```bash
# Clone from GitHub
git clone https://github.com/yourusername/ipo-drhp-agent.git
cd ipo-drhp-agent
```

---

## Step 5: Create .env File on EC2

```bash
nano .env
```

Paste your keys:
```
GOOGLE_API_KEY=your-gemini-key
TAVILY_API_KEY=tvly-your-tavily-key
API_KEY=drhp-secret-key-2024
```

Save: Ctrl+X → Y → Enter

---

## Step 6: Start the Application

```bash
# Build and start both services
docker-compose up -d --build

# Check if running
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f frontend
```

---

## Step 7: Test Your Deployment

Open in browser:
- Streamlit Dashboard: `http://YOUR-EC2-IP:8501`
- FastAPI Docs: `http://YOUR-EC2-IP:8000/docs`
- Health Check: `http://YOUR-EC2-IP:8000/health`

---

## Step 8: Setup GitHub Actions (Auto Deploy)

### Add Secrets to GitHub

Go to: GitHub repo → Settings → Secrets and Variables → Actions → New secret

Add these secrets:
```
GOOGLE_API_KEY     → your Gemini API key
TAVILY_API_KEY     → your Tavily API key
API_KEY            → drhp-secret-key-2024
EC2_HOST           → your EC2 public IP
EC2_SSH_KEY        → contents of your .pem file (entire file)
```

To get SSH key contents:
```bash
# Windows PowerShell
Get-Content "your-key.pem"
```
Copy everything including `-----BEGIN RSA PRIVATE KEY-----`

### Add deploy.yml to your repo

```bash
# In your local project
mkdir -p .github/workflows
# Copy deploy.yml to .github/workflows/deploy.yml
git add .github/workflows/deploy.yml
git commit -m "Add GitHub Actions CI/CD"
git push origin main
```

Now every push to main will:
1. Run pytest tests
2. SSH into EC2
3. Pull latest code
4. Restart Docker containers

---

## Useful Commands

```bash
# Restart everything
docker-compose restart

# Stop everything
docker-compose down

# View running containers
docker ps

# View API logs live
docker-compose logs -f api

# Update after code change
git pull && docker-compose up -d --build

# Free up disk space
docker system prune -f
```

---

## Troubleshooting

**Port already in use:**
```bash
sudo lsof -i :8000
sudo kill -9 PID
```

**Out of memory (t2.micro):**
```bash
# Add swap space
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**ChromaDB permission error:**
```bash
sudo chmod -R 777 chroma_db/
```
