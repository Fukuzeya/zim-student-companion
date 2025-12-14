# Run this script on a fresh Ubuntu 22.04 Linode server
# Usage: curl -sSL https://raw.githubusercontent.com/yourrepo/main/scripts/linode-setup.sh | bash
#
# Prerequisites:
# - Ubuntu 22.04 LTS
# - At least 4GB RAM (Linode 4GB plan recommended)
# - Root or sudo access

set -e  # Exit on any error

echo "🚀 Starting Zim Student Companion Server Setup..."
echo "================================================"

# ============================================================================
# 1. SYSTEM UPDATE & BASIC SECURITY
# ============================================================================
echo "📦 Step 1: Updating system packages..."

apt-get update && apt-get upgrade -y

# Install essential packages
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    ncdu \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban

# ============================================================================
# 2. CREATE DEPLOY USER
# ============================================================================
echo "👤 Step 2: Creating deploy user..."

# Create deploy user if doesn't exist
if ! id "deploy" &>/dev/null; then
    useradd -m -s /bin/bash deploy
    usermod -aG sudo deploy
    
    # Set up SSH for deploy user
    mkdir -p /home/deploy/.ssh
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/ 2>/dev/null || true
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    chmod 600 /home/deploy/.ssh/authorized_keys 2>/dev/null || true
    
    echo "deploy ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/deploy
    echo "✅ Deploy user created"
else
    echo "ℹ️ Deploy user already exists"
fi

# ============================================================================
# 3. CONFIGURE FIREWALL (UFW)
# ============================================================================
echo "🔥 Step 3: Configuring firewall..."

ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

echo "✅ Firewall configured"

# ============================================================================
# 4. CONFIGURE FAIL2BAN (Brute Force Protection)
# ============================================================================
echo "🛡️ Step 4: Configuring Fail2Ban..."

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl restart fail2ban

echo "✅ Fail2Ban configured"

# ============================================================================
# 5. INSTALL DOCKER
# ============================================================================
echo "🐳 Step 5: Installing Docker..."

# Remove old versions
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add deploy user to docker group
usermod -aG docker deploy

# Enable Docker to start on boot
systemctl enable docker
systemctl start docker

echo "✅ Docker installed: $(docker --version)"

# ============================================================================
# 6. INSTALL DOCKER COMPOSE
# ============================================================================
echo "📦 Step 6: Installing Docker Compose..."

DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -oP '"tag_name": "\K(.*)(?=")')
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo "✅ Docker Compose installed: $(docker-compose --version)"

# ============================================================================
# 7. CREATE APPLICATION DIRECTORIES
# ============================================================================
echo "📁 Step 7: Creating application directories..."

mkdir -p /opt/zim-student-companion/{nginx/ssl,logs,backups,data}
mkdir -p /opt/zim-student-companion/data/{postgres,redis,qdrant}

chown -R deploy:deploy /opt/zim-student-companion

echo "✅ Directories created"

# ============================================================================
# 8. INSTALL CERTBOT (SSL Certificates)
# ============================================================================
echo "🔒 Step 8: Installing Certbot for SSL..."

apt-get install -y certbot

echo "✅ Certbot installed"
echo "ℹ️ Run 'sudo certbot certonly --standalone -d yourdomain.com' to get SSL certificate"

# ============================================================================
# 9. SET UP LOG ROTATION
# ============================================================================
echo "📜 Step 9: Configuring log rotation..."

cat > /etc/logrotate.d/zim-student-companion << 'EOF'
/opt/zim-student-companion/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 deploy deploy
    sharedscripts
    postrotate
        docker-compose -f /opt/zim-student-companion/docker-compose.prod.yml restart nginx >/dev/null 2>&1 || true
    endscript
}
EOF

echo "✅ Log rotation configured"

# ============================================================================
# 10. SET UP AUTOMATIC SECURITY UPDATES
# ============================================================================
echo "🔄 Step 10: Configuring automatic security updates..."

apt-get install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

echo "✅ Automatic updates configured"

# ============================================================================
# 11. OPTIMIZE SYSTEM FOR DOCKER
# ============================================================================
echo "⚡ Step 11: Optimizing system settings..."

# Increase file limits
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
EOF

# Optimize network settings
cat >> /etc/sysctl.conf << 'EOF'
# Network optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_tw_buckets = 1440000
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# Memory optimizations
vm.swappiness = 10
vm.dirty_ratio = 60
vm.dirty_background_ratio = 2
EOF

sysctl -p

echo "✅ System optimized"

# ============================================================================
# 12. CREATE BACKUP SCRIPT
# ============================================================================
echo "💾 Step 12: Creating backup script..."

cat > /opt/zim-student-companion/scripts/backup.sh << 'BACKUP_SCRIPT'
#!/bin/bash
# Database Backup Script

set -e

BACKUP_DIR="/opt/zim-student-companion/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Create backup
echo "Starting backup..."
docker-compose -f /opt/zim-student-companion/docker-compose.prod.yml exec -T postgres \
    pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Delete old backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
BACKUP_SCRIPT

chmod +x /opt/zim-student-companion/scripts/backup.sh
mkdir -p /opt/zim-student-companion/scripts

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/zim-student-companion/scripts/backup.sh >> /opt/zim-student-companion/logs/backup.log 2>&1") | crontab -

echo "✅ Backup script created"

# ============================================================================
# 13. PRINT SUMMARY
# ============================================================================
echo ""
echo "=============================================="
echo "🎉 Server Setup Complete!"
echo "=============================================="
echo ""
echo "📋 Next Steps:"
echo "1. Set up GitHub secrets (see secrets guide)"
echo "2. Configure DNS to point to this server: $(curl -s ifconfig.me)"
echo "3. Get SSL certificate: sudo certbot certonly --standalone -d yourdomain.com"
echo "4. Copy SSL certs to /opt/zim-student-companion/nginx/ssl/"
echo "5. Create .env file in /opt/zim-student-companion/"
echo "6. Push to main branch to trigger deployment"
echo ""
echo "🔑 Server IP: $(curl -s ifconfig.me)"
echo "👤 Deploy user: deploy"
echo "📁 App directory: /opt/zim-student-companion"
echo ""

