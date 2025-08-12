# GITTE Troubleshooting Guide

This guide provides solutions for common issues encountered when deploying and operating GITTE.

## 📋 Quick Diagnostics

### System Health Check

```bash
# Check all services status
docker-compose ps

# Check application health
curl -f http://localhost:8501/_stcore/health

# Check database connectivity
docker-compose exec postgres pg_isready -U gitte -d data_collector

# Check Ollama service
curl -f http://localhost:11434/api/tags

# Check MinIO service
curl -f http://localhost:9000/minio/health/live
```

### Log Analysis

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs gitte-app
docker-compose logs postgres
docker-compose logs ollama
docker-compose logs minio

# Follow logs in real-time
docker-compose logs -f gitte-app

# View last 100 lines
docker-compose logs --tail=100 gitte-app
```

## 🚨 Common Issues

### 1. Application Won't Start

#### Symptoms
- Container exits immediately
- "Connection refused" errors
- Streamlit not accessible

#### Diagnosis
```bash
# Check container status
docker-compose ps

# Check application logs
docker-compose logs gitte-app

# Check resource usage
docker stats

# Verify environment variables
docker-compose exec gitte-app env | grep -E "(POSTGRES|OLLAMA|MINIO)"
```

#### Common Causes & Solutions

**Database Connection Issues:**
```bash
# Check database is running
docker-compose ps postgres

# Test database connection
docker-compose exec postgres psql -U gitte -d data_collector -c "SELECT 1;"

# Check database logs
docker-compose logs postgres

# Solution: Restart database service
docker-compose restart postgres
```

**Missing Environment Variables:**
```bash
# Check .env file exists
ls -la .env

# Verify required variables
grep -E "(POSTGRES_PASSWORD|SECRET_KEY)" .env

# Solution: Copy from example and configure
cp .env.example .env
# Edit .env with proper values
```

**Port Conflicts:**
```bash
# Check if ports are in use
netstat -tulpn | grep -E "(8501|5432|11434|9000)"

# Solution: Change ports in docker-compose.yml or stop conflicting services
```

**Insufficient Resources:**
```bash
# Check available memory
free -h

# Check disk space
df -h

# Solution: Free up resources or increase system capacity
```

### 2. Database Issues

#### Connection Failures

**Symptoms:**
- "Connection to server failed" errors
- Database timeout errors
- Application can't connect to PostgreSQL

**Diagnosis:**
```bash
# Check PostgreSQL container
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection from app container
docker-compose exec gitte-app pg_isready -h postgres -p 5432 -U gitte

# Check network connectivity
docker-compose exec gitte-app ping postgres
```

**Solutions:**
```bash
# Restart PostgreSQL
docker-compose restart postgres

# Recreate database with fresh data
docker-compose down
docker volume rm gitte-federated-learning-system_postgres_data
docker-compose up -d postgres

# Check PostgreSQL configuration
docker-compose exec postgres cat /var/lib/postgresql/data/postgresql.conf
```

#### Migration Issues

**Symptoms:**
- "Table doesn't exist" errors
- Schema version conflicts
- Migration failures

**Diagnosis:**
```bash
# Check current migration status
docker-compose exec gitte-app python -m alembic current

# Check migration history
docker-compose exec gitte-app python -m alembic history

# Check database schema
docker-compose exec postgres psql -U gitte -d data_collector -c "\dt"
```

**Solutions:**
```bash
# Run pending migrations
docker-compose exec gitte-app python -m alembic upgrade head

# Reset database and run migrations
docker-compose down
docker volume rm gitte-federated-learning-system_postgres_data
docker-compose up -d postgres
sleep 30
docker-compose exec gitte-app python -m alembic upgrade head

# Create new migration if needed
docker-compose exec gitte-app python -m alembic revision --autogenerate -m "description"
```

#### Performance Issues

**Symptoms:**
- Slow query responses
- Database timeouts
- High CPU usage

**Diagnosis:**
```bash
# Check active connections
docker-compose exec postgres psql -U gitte -d data_collector -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
docker-compose exec postgres psql -U gitte -d data_collector -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check database size
docker-compose exec postgres psql -U gitte -d data_collector -c "SELECT pg_size_pretty(pg_database_size('data_collector'));"
```

**Solutions:**
```bash
# Analyze and optimize queries
docker-compose exec postgres psql -U gitte -d data_collector -c "ANALYZE;"

# Create indexes for slow queries
docker-compose exec postgres psql -U gitte -d data_collector -c "CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);"

# Increase shared_buffers in docker-compose.yml
# Add to postgres command: -c shared_buffers=256MB
```

### 3. LLM Service Issues

#### Ollama Connection Problems

**Symptoms:**
- Chat responses fail
- "Connection refused" to Ollama
- Timeout errors

**Diagnosis:**
```bash
# Check Ollama container
docker-compose ps ollama

# Check Ollama logs
docker-compose logs ollama

# Test Ollama API
curl -f http://localhost:11434/api/tags

# Check available models
docker-compose exec ollama ollama list
```

**Solutions:**
```bash
# Restart Ollama service
docker-compose restart ollama

# Pull required models
docker-compose exec ollama ollama pull llama2

# Check Ollama configuration
docker-compose exec ollama env | grep OLLAMA

# Increase memory limits in docker-compose.yml
```

#### Model Loading Issues

**Symptoms:**
- Models not available
- "Model not found" errors
- Slow model loading

**Diagnosis:**
```bash
# List available models
docker-compose exec ollama ollama list

# Check model download status
docker-compose logs ollama | grep -i download

# Check disk space for models
docker-compose exec ollama df -h /root/.ollama
```

**Solutions:**
```bash
# Download required models
docker-compose exec ollama ollama pull llama2
docker-compose exec ollama ollama pull codellama

# Remove unused models to free space
docker-compose exec ollama ollama rm unused_model

# Pre-load models in startup script
echo "ollama pull llama2" >> startup.sh
```

#### Performance Issues

**Symptoms:**
- Slow response times
- High memory usage
- GPU not utilized

**Diagnosis:**
```bash
# Check GPU availability
docker-compose exec ollama nvidia-smi

# Monitor resource usage
docker stats ollama

# Check model performance
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2", "prompt": "Hello", "stream": false}'
```

**Solutions:**
```bash
# Enable GPU support in docker-compose.yml
# Add to ollama service:
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: 1
#           capabilities: [gpu]

# Optimize model parameters
# Use smaller models for faster responses
# Adjust context length and temperature
```

### 4. Image Generation Issues

#### Stable Diffusion Problems

**Symptoms:**
- Image generation fails
- "CUDA out of memory" errors
- Very slow generation times

**Diagnosis:**
```bash
# Check GPU memory
nvidia-smi

# Check Python packages
docker-compose exec gitte-app pip list | grep -E "(torch|diffusers)"

# Test image generation
docker-compose exec gitte-app python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CUDA devices: {torch.cuda.device_count()}')
"
```

**Solutions:**
```bash
# Enable GPU support
# Ensure NVIDIA Docker runtime is installed
# Update docker-compose.yml with GPU configuration

# Fallback to CPU mode
# Set DEVICE=cpu in environment variables

# Reduce image size for faster generation
# Use 256x256 instead of 512x512

# Clear GPU memory
docker-compose restart gitte-app
```

#### Storage Issues

**Symptoms:**
- Images not saving
- "Permission denied" errors
- Disk space issues

**Diagnosis:**
```bash
# Check disk space
df -h

# Check image directory permissions
docker-compose exec gitte-app ls -la generated_images/

# Check MinIO connectivity
curl -f http://localhost:9000/minio/health/live

# Check MinIO logs
docker-compose logs minio
```

**Solutions:**
```bash
# Fix permissions
sudo chown -R 1000:1000 generated_images/

# Clean up old images
find generated_images/ -name "*.png" -mtime +30 -delete

# Restart MinIO
docker-compose restart minio

# Check MinIO configuration
docker-compose exec minio mc admin info local
```

### 5. Authentication Issues

#### Login Failures

**Symptoms:**
- "Invalid credentials" errors
- Session timeouts
- Users can't register

**Diagnosis:**
```bash
# Check user table
docker-compose exec postgres psql -U gitte -d data_collector -c "SELECT username, role, created_at FROM users;"

# Check session management
docker-compose logs gitte-app | grep -i session

# Verify password hashing
docker-compose exec gitte-app python -c "
from src.logic.authentication import AuthenticationLogic
print('Auth system loaded successfully')
"
```

**Solutions:**
```bash
# Reset user password
docker-compose exec postgres psql -U gitte -d data_collector -c "
UPDATE users SET password_hash = '\$2b\$12\$...' WHERE username = 'testuser';
"

# Clear sessions
docker-compose exec postgres psql -U gitte -d data_collector -c "DELETE FROM user_sessions;"

# Check session configuration
grep -i session config/config.py
```

#### Permission Issues

**Symptoms:**
- "Access denied" errors
- Admin functions not available
- Role assignment problems

**Diagnosis:**
```bash
# Check user roles
docker-compose exec postgres psql -U gitte -d data_collector -c "SELECT username, role FROM users;"

# Check role-based access
docker-compose logs gitte-app | grep -i "permission\|role\|access"
```

**Solutions:**
```bash
# Update user role
docker-compose exec postgres psql -U gitte -d data_collector -c "
UPDATE users SET role = 'ADMIN' WHERE username = 'admin_user';
"

# Create admin user
docker-compose exec gitte-app python scripts/create_admin.py
```

### 6. Performance Issues

#### Slow Response Times

**Symptoms:**
- Pages load slowly
- API timeouts
- High latency

**Diagnosis:**
```bash
# Check system resources
top
htop
iostat -x 1

# Monitor application performance
docker stats

# Check database performance
docker-compose exec postgres psql -U gitte -d data_collector -c "
SELECT query, mean_time, calls FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
"

# Profile application
docker-compose logs gitte-app | grep -i "latency\|time\|slow"
```

**Solutions:**
```bash
# Optimize database queries
# Add indexes for frequently queried columns
docker-compose exec postgres psql -U gitte -d data_collector -c "
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_pald_data_user_id ON pald_data(user_id);
"

# Increase resource limits
# Update docker-compose.yml with higher memory/CPU limits

# Enable caching
# Configure Redis for session storage and caching

# Optimize Streamlit
# Reduce widget refresh rates
# Use st.cache for expensive operations
```

#### Memory Issues

**Symptoms:**
- Out of memory errors
- Container restarts
- Swap usage high

**Diagnosis:**
```bash
# Check memory usage
free -h
docker stats

# Check for memory leaks
docker-compose logs gitte-app | grep -i "memory\|oom"

# Monitor memory over time
watch -n 5 'docker stats --no-stream'
```

**Solutions:**
```bash
# Increase container memory limits
# Update docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G

# Optimize Python memory usage
# Use generators instead of lists
# Clear unused variables
# Implement garbage collection

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 🔧 Maintenance Tasks

### Regular Maintenance

#### Daily Tasks
```bash
# Check system health
make health-check

# Review error logs
docker-compose logs --since=24h | grep -i error

# Monitor disk space
df -h

# Check backup status
ls -la backups/
```

#### Weekly Tasks
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Clean up old containers and images
docker system prune -f

# Rotate logs
docker-compose logs --since=7d > logs/weekly-$(date +%Y%m%d).log

# Review performance metrics
curl http://localhost:9090/metrics
```

#### Monthly Tasks
```bash
# Full system backup
./scripts/backup.sh

# Security updates
docker-compose pull
docker-compose up -d

# Performance review
# Analyze slow queries
# Review resource usage trends
# Plan capacity upgrades
```

### Emergency Procedures

#### System Recovery
```bash
# Complete system restart
docker-compose down
docker-compose up -d

# Database recovery from backup
docker-compose down
docker volume rm gitte-federated-learning-system_postgres_data
docker-compose up -d postgres
sleep 30
docker-compose exec postgres psql -U gitte -d data_collector < backup.sql

# Application rollback
git checkout previous-stable-tag
docker-compose build
docker-compose up -d
```

#### Data Recovery
```bash
# Restore from backup
docker-compose exec postgres psql -U gitte -d data_collector < backup_YYYYMMDD.sql

# Recover deleted user data (if within retention period)
docker-compose exec postgres psql -U gitte -d data_collector -c "
SELECT * FROM deleted_users WHERE deleted_at > NOW() - INTERVAL '72 hours';
"

# Restore MinIO data
docker run --rm -v gitte-federated-learning-system_minio_data:/data \
  -v $(pwd)/backups:/backup alpine \
  tar xzf /backup/minio_backup_YYYYMMDD.tar.gz -C /
```

## 📞 Getting Help

### Log Collection
```bash
# Collect all logs for support
mkdir -p support-logs
docker-compose logs > support-logs/docker-compose.log
docker stats --no-stream > support-logs/docker-stats.txt
docker system df > support-logs/docker-disk-usage.txt
free -h > support-logs/system-memory.txt
df -h > support-logs/system-disk.txt
tar -czf support-logs-$(date +%Y%m%d-%H%M%S).tar.gz support-logs/
```

### System Information
```bash
# Collect system information
echo "=== System Information ===" > system-info.txt
uname -a >> system-info.txt
docker --version >> system-info.txt
docker-compose --version >> system-info.txt
python --version >> system-info.txt
echo "=== Environment Variables ===" >> system-info.txt
env | grep -E "(POSTGRES|OLLAMA|MINIO|GITTE)" >> system-info.txt
echo "=== Docker Compose Config ===" >> system-info.txt
docker-compose config >> system-info.txt
```

### Support Checklist

Before contacting support, please:

1. ✅ Check this troubleshooting guide
2. ✅ Review application logs
3. ✅ Verify system requirements
4. ✅ Test with minimal configuration
5. ✅ Collect logs and system information
6. ✅ Document steps to reproduce the issue

### Contact Information

- **Documentation:** [Project Wiki/Docs]
- **Issue Tracker:** [GitHub Issues]
- **Community:** [Discord/Slack Channel]
- **Email Support:** [support@gitte.ai]

---

**Note:** This troubleshooting guide is regularly updated. Check for the latest version at [documentation URL].