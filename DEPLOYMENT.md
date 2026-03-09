# Sahel JobPulse: Production Deployment Guide

This guide provides step-by-step instructions for deploying the Sahel JobPulse Django application to a fresh Ubuntu VPS (IP: `31.97.63.178`) using Docker Compose, Nginx (as a reverse proxy), and GitHub Actions for CI/CD, adhering to production best practices.

## Phase 1: VPS Security & Initial Setup

*Execute these commands by SSHing into your VPS as `root`.*

### 1. Update Packages & Install Essentials

```bash
apt update && apt upgrade -y
apt install -y curl ufw fail2ban default-jre
```

### 2. Create a Non-Root User (Best Practice)

Never run your applications as the `root` user.

```bash
adduser deeps
usermod -aG sudo deeps
```

*Switch to the new user for the remainder of the setup:*

```bash
su - deeps
```

### 3. Configure the Firewall (UFW)

Allow only essential ports (SSH, HTTP, HTTPS).

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 4. Install Docker & Docker Compose

```bash
# Add Docker's official GPG key & Repo
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group so you don't need 'sudo' for every docker command
sudo usermod -aG docker deeps
newgrp docker

# Install Docker Compose plugin
sudo apt-get install docker-compose-plugin
```

---

## Phase 2: Manual Initial Project Setup

*Execute as the `deeps` user on the VPS.*

### 1. Clone the Repository

```bash
mkdir -p ~/sahel-app
cd ~/sahel-app
git clone https://github.com/mohammadSelimReza/JobPulse-Web-App.git .
```

### 2. Configure Environment Variables

Copy the template and fill in your actual production secrets.

```bash
cp .env.example .env
nano .env
```

**CRITICAL:**

* Change `SECRET_KEY` to a completely random string.
* Ensure `DEBUG=False`.
* Set `ALLOWED_HOSTS=31.97.63.178,yourdomain.com`.
* Update the Database and Redis tokens if desired (make sure they match the `docker-compose.prod.yml`).
* Insert your valid Orange SMS API keys.

### 3. First-Time Docker Spin Up

Test that the stack comes up cleanly.

```bash
make prod-build
make prod-up
```

Verify everything is running gracefully: `docker ps`.

### 4. Run Initial Migrations & Create Admin

```bash
make migrate
make collectstatic
make shell
# Inside the python shell:
# > from api.models import User
# > User.objects.create_superuser(phone_number='admin@admin.com', password='your_secure_password', is_admin=True, is_staff=True)
# > exit()
```

---

## Phase 3: Nginx Reverse Proxy Setup

Nginx acts as the gatekeeper, receiving web traffic on Port 80/443 and forwarding it securely to Gunicorn inside your Docker container on Port 8000.

### 1. Install Nginx

```bash
sudo apt install -y nginx
```

### 2. Configure Nginx

Create a configuration file for your app:

```bash
sudo nano /etc/nginx/sites-available/sahel
```

Paste the following (replace `yourdomain.com` if you have one, or just use the IP `31.97.63.178`):

```nginx
server {
    listen 80;
    server_name 31.97.63.178; # Or yourdomain.com

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Serve static files directly via Nginx for speed
    location /static/ {
        alias /home/deeps/sahel-app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location /media/ {
        alias /home/deeps/sahel-app/media/;
    }
}
```

### 3. Enable and Restart Nginx

```bash
sudo ln -s /etc/nginx/sites-available/sahel /etc/nginx/sites-enabled/
sudo unlink /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

> **Optional, but highly recommended: Add HTTPS/SSL via Certbot**
>
> ```bash
> sudo apt install certbot python3-certbot-nginx
> sudo certbot --nginx -d yourdomain.com
> ```

---

## Phase 4: GitHub Actions CI/CD Pipeline

We will set up a pipeline so that every time you push to the `main` branch, the VPS automatically pulls the code and restarts the specific Docker containers that changed.

### 1. Generate SSH Key Pair for GitHub Actions

On your LOCAL machine (or the VPS), generate an SSH key specifically for deployment:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f github_deploy_key
```

1. DO NOT enter a passphrase (leave it blank).
2. Print the public key: `cat github_deploy_key.pub`.
3. Add this **public key** to the `~/.ssh/authorized_keys` file on the VPS for the `deeps` user.
4. Print the private key: `cat github_deploy_key`. Copy the entire output.

### 2. Add GitHub Repository Secrets

Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions.
Add the following "New repository secrets":

* `HOST`: `31.97.63.178`
* `USERNAME`: `deeps`
* `SSH_PRIVATE_KEY`: *(Paste the exact contents of `github_deploy_key` here)*
* `WORK_DIR`: `/home/deeps/sahel-app`

### 3. Create the GitHub Actions Workflow File

In your codebase, create a new folder `.github/workflows/` and add a file named `deploy.yml`:

```yaml
name: Deploy to Production VPS

on:
  push:
    branches: [ "main" ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd ${{ secrets.WORK_DIR }}
            echo "1. Pulling latest code..."
            git pull origin main
            
            echo "2. Rebuilding Web Container..."
            make prod-build
            
            echo "3. Restarting Services..."
            make prod-up
            
            echo "4. Running Migrations & Collecting Static..."
            make migrate
            make collectstatic
            
            echo "Deployment Complete! ✅"
```

### 4. Commit and Push

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add automated deployment workflow"
git push origin main
```

**Congratulations!** 🚀
Because of the GitHub Action, your push just triggered an automated deployment to your VPS. You can track its progress in the "Actions" tab of your GitHub repository.
