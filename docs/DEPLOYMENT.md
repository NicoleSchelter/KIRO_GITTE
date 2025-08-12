# GITTE Deployment Guide

This guide covers deploying GITTE (Great Individual Tutor Embodiment) in production environments.

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD
- Network: 1Gbps

**Recommended Requirements:**
- CPU: 8 cores
- RAM: 16GB
- Storage: 100GB SSD
- GPU: NVIDIA GPU with 8GB+ VRAM (for image generation)
- Network: 1Gbps

### Software Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- SSL certificates (for HTTPS)

### Network Requirements

**Inbound Ports:**
- 80 (HTTP)
- 443 (HTTPS)
- 22 (SSH for management)

**Outbound Ports:**
- 80, 443 (Package downloads, external APIs)
- 53 (DNS)

## 🚀 Production Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login to apply group changes
```

### 2. Application Setup

```bash
# Clone repository
git clone <repository-url>
cd gitte-federated-learning-system

# Create production environment file
cp .env.example .env.prod
```

### 3. Environment Configuration

Edit `.env.prod` with production values:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here

# MinIO
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key

# Application Security
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_32_byte_encryption_key_here

# Domain Configuration
DOMAIN=yourdomain.com
SSL_EMAIL=admin@yourdomain.com

# Feature Flags
FEATURE_ENABLE_MONITORING=true
FEATURE_ENABLE_SSL=true
```

### 4. SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to nginx directory
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
```

#### Option B: Self-Signed (Development/Testing)

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/privkey.pem \
    -out nginx/ssl/fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### 5. Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream gitte_app {
        server gitte-app:8501;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # SSL Configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;

        # Security Headers
        add_header Strict-Transport-Security "max-age=63072000" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # Main application
        location / {
            proxy_pass http://gitte_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        # Static files
        location /static {
            alias /app/static;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### 6. Database Initialization

```bash
# Start database service
docker-compose -f docker-compose.prod.yml up -d postgres

# Wait for database to be ready
sleep 30

# Run migrations
docker-compose -f docker-compose.prod.yml exec gitte-app python -m alembic upgrade head

# Seed initial data
docker-compose -f docker-compose.prod.yml exec gitte-app python scripts/seed_database.py
```

### 7. Start Production Services

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 8. Verify Deployment

```bash
# Check application health
curl -f https://yourdomain.com/health

# Check service endpoints
curl -f https://yourdomain.com/_stcore/health

# Test database connection
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U gitte -d data_collector
```

## 🔧 Configuration Management

### Environment Variables

Key production environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `POSTGRES_PASSWORD` | Database password | `secure_password` |
| `SECRET_KEY` | Application secret key | `your_secret_key` |
| `ENCRYPTION_KEY` | Data encryption key | `32_byte_key` |
| `DOMAIN` | Application domain | `yourdomain.com` |

### Feature Flags

Control production features:

```bash
# Core Features
FEATURE_ENABLE_CONSENT_GATE=true
FEATURE_ENABLE_IMAGE_GENERATION=true
FEATURE_USE_FEDERATED_LEARNING=false

# Monitoring & Logging
FEATURE_ENABLE_MONITORING=true
FEATURE_SAVE_LLM_LOGS=true
FEATURE_ENABLE_AUDIT_LOGGING=true

# Security
FEATURE_ENABLE_SSL=true
FEATURE_ENABLE_RATE_LIMITING=true
```

## 📊 Monitoring & Logging

### Application Logs

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs gitte-app

# View database logs
docker-compose -f docker-compose.prod.yml logs postgres

# View all service logs
docker-compose -f docker-compose.prod.yml logs
```

### Health Checks

```bash
# Application health
curl https://yourdomain.com/_stcore/health

# Database health
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# MinIO health
curl http://localhost:9000/minio/health/live

# Ollama health
curl http://localhost:11434/api/tags
```

### Metrics Collection

If Prometheus is enabled:

```bash
# Access Prometheus
http://localhost:9090

# Key metrics to monitor:
# - gitte_requests_total
# - gitte_response_time_seconds
# - gitte_errors_total
# - postgres_connections
# - minio_storage_usage
```

## 🔄 Maintenance

### Backup Procedures

#### Database Backup

```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U gitte data_collector > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U gitte data_collector > $BACKUP_DIR/gitte_backup_$DATE.sql
find $BACKUP_DIR -name "gitte_backup_*.sql" -mtime +7 -delete
```

#### File Storage Backup

```bash
# Backup generated images
tar -czf images_backup_$(date +%Y%m%d).tar.gz generated_images/

# Backup MinIO data
docker run --rm -v gitte-federated-learning-system_minio_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/minio_backup_$(date +%Y%m%d).tar.gz /data
```

### Updates & Upgrades

```bash
# Pull latest code
git pull origin main

# Rebuild and restart services
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Run any new migrations
docker-compose -f docker-compose.prod.yml exec gitte-app python -m alembic upgrade head
```

### SSL Certificate Renewal

```bash
# Renew Let's Encrypt certificates
sudo certbot renew

# Copy renewed certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## 🚨 Troubleshooting

### Common Issues

#### Application Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs gitte-app

# Common causes:
# - Database connection issues
# - Missing environment variables
# - Port conflicts
# - Insufficient resources
```

#### Database Connection Issues

```bash
# Check database status
docker-compose -f docker-compose.prod.yml ps postgres

# Test connection
docker-compose -f docker-compose.prod.yml exec postgres psql -U gitte -d data_collector -c "SELECT 1;"

# Check network connectivity
docker-compose -f docker-compose.prod.yml exec gitte-app ping postgres
```

#### SSL/HTTPS Issues

```bash
# Check certificate validity
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Test SSL configuration
curl -I https://yourdomain.com

# Check nginx configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### Performance Issues

#### High Memory Usage

```bash
# Check container resource usage
docker stats

# Optimize PostgreSQL settings in docker-compose.prod.yml
# Adjust shared_buffers, effective_cache_size based on available RAM
```

#### Slow Response Times

```bash
# Check application metrics
curl https://yourdomain.com/admin/metrics

# Monitor database performance
docker-compose -f docker-compose.prod.yml exec postgres psql -U gitte -d data_collector -c "SELECT * FROM pg_stat_activity;"

# Check Ollama model loading
curl http://localhost:11434/api/tags
```

## 🔒 Security Considerations

### Network Security

- Use firewall to restrict access to internal ports
- Enable fail2ban for SSH protection
- Regular security updates
- Monitor access logs

### Application Security

- Regular dependency updates
- Secure environment variable storage
- Database access restrictions
- API rate limiting

### Data Protection

- Encrypt data at rest
- Secure backup storage
- Regular security audits
- GDPR compliance monitoring

## 📞 Support

For deployment issues:

1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Verify configuration: Review environment variables and nginx config
3. Test connectivity: Ensure all services can communicate
4. Monitor resources: Check CPU, memory, and disk usage
5. Review documentation: Consult troubleshooting section

For additional support, contact the development team or create an issue in the project repository.