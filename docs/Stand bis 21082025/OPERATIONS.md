# GITTE Operations Runbook

This runbook provides step-by-step procedures for operating and maintaining GITTE in production environments.

## 📋 Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring & Alerting](#monitoring--alerting)
3. [Backup & Recovery](#backup--recovery)
4. [Deployment Procedures](#deployment-procedures)
5. [Incident Response](#incident-response)
6. [Maintenance Windows](#maintenance-windows)
7. [Capacity Planning](#capacity-planning)
8. [Security Operations](#security-operations)

---

## 🌅 Daily Operations

### Morning Health Check (09:00 UTC)

**Objective:** Verify system health and identify any overnight issues.

**Procedure:**
```bash
#!/bin/bash
# Daily health check script

echo "=== GITTE Daily Health Check - $(date) ==="

# 1. Check service status
echo "1. Checking service status..."
docker-compose ps
if [ $? -ne 0 ]; then
    echo "❌ Service status check failed"
    exit 1
fi

# 2. Check application health
echo "2. Checking application health..."
curl -f -s http://localhost:8501/_stcore/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Application is healthy"
else
    echo "❌ Application health check failed"
fi

# 3. Check database connectivity
echo "3. Checking database connectivity..."
docker-compose exec -T postgres pg_isready -U gitte -d kiro_test
if [ $? -eq 0 ]; then
    echo "✅ Database is accessible"
else
    echo "❌ Database connectivity failed"
fi

# 4. Check LLM service
echo "4. Checking LLM service..."
curl -f -s http://localhost:11434/api/tags > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ LLM service is responding"
else
    echo "❌ LLM service check failed"
fi

# 5. Check storage service
echo "5. Checking storage service..."
curl -f -s http://localhost:9000/minio/health/live > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Storage service is healthy"
else
    echo "❌ Storage service check failed"
fi

# 6. Check disk space
echo "6. Checking disk space..."
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✅ Disk usage: ${DISK_USAGE}%"
else
    echo "⚠️ High disk usage: ${DISK_USAGE}%"
fi

# 7. Check memory usage
echo "7. Checking memory usage..."
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEMORY_USAGE -lt 80 ]; then
    echo "✅ Memory usage: ${MEMORY_USAGE}%"
else
    echo "⚠️ High memory usage: ${MEMORY_USAGE}%"
fi

# 8. Check recent errors
echo "8. Checking recent errors..."
ERROR_COUNT=$(docker-compose logs --since=24h | grep -i error | wc -l)
if [ $ERROR_COUNT -lt 10 ]; then
    echo "✅ Error count (24h): $ERROR_COUNT"
else
    echo "⚠️ High error count (24h): $ERROR_COUNT"
fi

echo "=== Health check completed ==="
```

**Expected Results:**
- All services running and healthy
- Disk usage < 80%
- Memory usage < 80%
- Error count < 10 in last 24 hours

**Escalation:** If any check fails, follow the [Incident Response](#incident-response) procedure.

### Evening Metrics Review (18:00 UTC)

**Objective:** Review daily metrics and identify trends.

**Procedure:**
```bash
#!/bin/bash
# Daily metrics collection script

echo "=== GITTE Daily Metrics - $(date) ==="

# 1. User activity metrics
echo "1. User Activity Metrics:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT 
    COUNT(DISTINCT user_id) as active_users,
    COUNT(*) as total_interactions,
    AVG(latency_ms) as avg_response_time
FROM audit_logs 
WHERE created_at >= CURRENT_DATE;
"

# 2. System performance metrics
echo "2. System Performance:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT 
    operation,
    COUNT(*) as count,
    AVG(latency_ms) as avg_latency,
    MAX(latency_ms) as max_latency
FROM audit_logs 
WHERE created_at >= CURRENT_DATE
GROUP BY operation;
"

# 3. Error analysis
echo "3. Error Analysis:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM audit_logs 
WHERE created_at >= CURRENT_DATE
GROUP BY status;
"

# 4. Resource usage
echo "4. Resource Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# 5. Storage usage
echo "5. Storage Usage:"
echo "Generated Images: $(du -sh generated_images/ | cut -f1)"
echo "Database Size:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT pg_size_pretty(pg_database_size('kiro_test')) as database_size;
"

echo "=== Metrics collection completed ==="
```

**Actions:**
- Review metrics for anomalies
- Update capacity planning spreadsheet
- Create alerts for trending issues

---

## 📊 Monitoring & Alerting

### Key Metrics to Monitor

#### Application Metrics
| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Response Time (P95) | >5s | Warning |
| Response Time (P95) | >10s | Critical |
| Error Rate | >1% | Warning |
| Error Rate | >5% | Critical |
| Active Users | <10 (business hours) | Warning |
| Request Rate | >1000/min | Warning |

#### System Metrics
| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| CPU Usage | >80% | Warning |
| CPU Usage | >95% | Critical |
| Memory Usage | >85% | Warning |
| Memory Usage | >95% | Critical |
| Disk Usage | >80% | Warning |
| Disk Usage | >90% | Critical |
| Disk I/O Wait | >20% | Warning |

#### Service Metrics
| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Database Connections | >80% of max | Warning |
| LLM Response Time | >10s | Warning |
| Image Generation Time | >60s | Warning |
| Storage API Errors | >5% | Warning |

### Alert Response Procedures

#### High Error Rate Alert

**Trigger:** Error rate > 1% for 5 minutes

**Response Procedure:**
1. **Immediate (0-5 minutes):**
   ```bash
   # Check recent errors
   docker-compose logs --since=10m | grep -i error | tail -20
   
   # Check service status
   docker-compose ps
   
   # Check system resources
   docker stats --no-stream
   ```

2. **Investigation (5-15 minutes):**
   ```bash
   # Analyze error patterns
   docker-compose exec postgres psql -U gitte -d kiro_test -c "
   SELECT operation, status, COUNT(*) 
   FROM audit_logs 
   WHERE created_at > NOW() - INTERVAL '1 hour' AND status = 'error'
   GROUP BY operation, status
   ORDER BY COUNT(*) DESC;
   "
   
   # Check external service health
   curl -f http://localhost:11434/api/tags
   curl -f http://localhost:9000/minio/health/live
   ```

3. **Mitigation (15-30 minutes):**
   - If database issues: Restart PostgreSQL service
   - If LLM issues: Restart Ollama service
   - If application issues: Restart application service
   - If persistent: Escalate to development team

#### High Response Time Alert

**Trigger:** P95 response time > 5s for 10 minutes

**Response Procedure:**
1. **Check database performance:**
   ```bash
   docker-compose exec postgres psql -U gitte -d kiro_test -c "
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   "
   ```

2. **Check system resources:**
   ```bash
   # CPU and memory usage
   top -n 1
   
   # I/O statistics
   iostat -x 1 5
   
   # Network statistics
   netstat -i
   ```

3. **Optimize if needed:**
   ```bash
   # Restart services to clear memory
   docker-compose restart gitte-app
   
   # Clear database statistics
   docker-compose exec postgres psql -U gitte -d kiro_test -c "
   SELECT pg_stat_statements_reset();
   "
   ```

#### Service Down Alert

**Trigger:** Service health check fails

**Response Procedure:**
1. **Immediate restart:**
   ```bash
   # Restart specific service
   docker-compose restart [service-name]
   
   # Check if service comes back up
   sleep 30
   docker-compose ps
   ```

2. **If restart fails:**
   ```bash
   # Check logs for errors
   docker-compose logs [service-name]
   
   # Check resource constraints
   docker system df
   free -h
   
   # Recreate service if needed
   docker-compose up -d --force-recreate [service-name]
   ```

3. **Escalation:**
   - If service won't start: Check system resources and escalate
   - If data corruption suspected: Initiate backup recovery procedure

---

## 💾 Backup & Recovery

### Automated Backup Procedure

**Schedule:** Daily at 02:00 UTC

**Backup Script:**
```bash
#!/bin/bash
# Automated backup script

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "Starting backup at $(date)"

# 1. Create backup directory
mkdir -p $BACKUP_DIR

# 2. Database backup
echo "Backing up database..."
docker-compose exec -T postgres pg_dump -U gitte kiro_test | gzip > $BACKUP_DIR/database_$DATE.sql.gz
if [ $? -eq 0 ]; then
    echo "✅ Database backup completed"
else
    echo "❌ Database backup failed"
    exit 1
fi

# 3. Generated images backup
echo "Backing up generated images..."
tar -czf $BACKUP_DIR/images_$DATE.tar.gz generated_images/
if [ $? -eq 0 ]; then
    echo "✅ Images backup completed"
else
    echo "❌ Images backup failed"
fi

# 4. MinIO data backup
echo "Backing up MinIO data..."
docker run --rm -v gitte-federated-learning-system_minio_data:/data \
    -v $BACKUP_DIR:/backup alpine \
    tar czf /backup/minio_$DATE.tar.gz /data
if [ $? -eq 0 ]; then
    echo "✅ MinIO backup completed"
else
    echo "❌ MinIO backup failed"
fi

# 5. Configuration backup
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/ .env docker-compose.yml
if [ $? -eq 0 ]; then
    echo "✅ Configuration backup completed"
else
    echo "❌ Configuration backup failed"
fi

# 6. Cleanup old backups
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 7. Verify backup integrity
echo "Verifying backup integrity..."
gunzip -t $BACKUP_DIR/database_$DATE.sql.gz
if [ $? -eq 0 ]; then
    echo "✅ Database backup integrity verified"
else
    echo "❌ Database backup integrity check failed"
fi

echo "Backup completed at $(date)"

# 8. Send notification (optional)
# curl -X POST -H 'Content-type: application/json' \
#     --data '{"text":"GITTE backup completed successfully"}' \
#     $SLACK_WEBHOOK_URL
```

### Recovery Procedures

#### Database Recovery

**Scenario:** Database corruption or data loss

**Procedure:**
```bash
#!/bin/bash
# Database recovery procedure

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

echo "Starting database recovery from $BACKUP_FILE"

# 1. Stop application
echo "Stopping application..."
docker-compose stop gitte-app

# 2. Backup current database (if accessible)
echo "Creating safety backup of current database..."
docker-compose exec -T postgres pg_dump -U gitte kiro_test > current_db_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Drop and recreate database
echo "Recreating database..."
docker-compose exec -T postgres psql -U gitte -c "DROP DATABASE IF EXISTS kiro_test;"
docker-compose exec -T postgres psql -U gitte -c "CREATE DATABASE kiro_test;"

# 4. Restore from backup
echo "Restoring from backup..."
gunzip -c $BACKUP_FILE | docker-compose exec -T postgres psql -U gitte kiro_test
if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully"
else
    echo "❌ Database restore failed"
    exit 1
fi

# 5. Run migrations (if needed)
echo "Running migrations..."
docker-compose exec gitte-app python -m alembic upgrade head

# 6. Restart application
echo "Restarting application..."
docker-compose start gitte-app

# 7. Verify recovery
sleep 30
curl -f http://localhost:8501/_stcore/health
if [ $? -eq 0 ]; then
    echo "✅ Recovery completed successfully"
else
    echo "❌ Recovery verification failed"
fi
```

#### Full System Recovery

**Scenario:** Complete system failure

**Procedure:**
```bash
#!/bin/bash
# Full system recovery procedure

BACKUP_DATE="$1"
if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <backup_date_YYYYMMDD_HHMMSS>"
    exit 1
fi

BACKUP_DIR="/backups"

echo "Starting full system recovery from backups dated $BACKUP_DATE"

# 1. Stop all services
echo "Stopping all services..."
docker-compose down

# 2. Remove all volumes (DESTRUCTIVE!)
echo "Removing all volumes..."
docker volume rm gitte-federated-learning-system_postgres_data
docker volume rm gitte-federated-learning-system_minio_data
docker volume rm gitte-federated-learning-system_ollama_data

# 3. Restore configuration
echo "Restoring configuration..."
tar -xzf $BACKUP_DIR/config_$BACKUP_DATE.tar.gz

# 4. Start database service
echo "Starting database service..."
docker-compose up -d postgres
sleep 30

# 5. Restore database
echo "Restoring database..."
gunzip -c $BACKUP_DIR/database_$BACKUP_DATE.sql.gz | docker-compose exec -T postgres psql -U gitte kiro_test

# 6. Restore MinIO data
echo "Restoring MinIO data..."
docker-compose up -d minio
sleep 30
docker run --rm -v gitte-federated-learning-system_minio_data:/data \
    -v $BACKUP_DIR:/backup alpine \
    tar xzf /backup/minio_$BACKUP_DATE.tar.gz -C /

# 7. Restore generated images
echo "Restoring generated images..."
tar -xzf $BACKUP_DIR/images_$BACKUP_DATE.tar.gz

# 8. Start all services
echo "Starting all services..."
docker-compose up -d

# 9. Verify recovery
echo "Verifying recovery..."
sleep 60
./scripts/health-check.sh

echo "Full system recovery completed"
```

---

## 🚀 Deployment Procedures

### Production Deployment

**Objective:** Deploy new version to production with zero downtime.

**Prerequisites:**
- Code reviewed and approved
- All tests passing
- Staging deployment successful
- Backup completed

**Procedure:**
```bash
#!/bin/bash
# Production deployment script

VERSION="$1"
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Starting production deployment of version $VERSION"

# 1. Pre-deployment backup
echo "Creating pre-deployment backup..."
./scripts/backup.sh

# 2. Pull latest code
echo "Pulling latest code..."
git fetch origin
git checkout $VERSION
if [ $? -ne 0 ]; then
    echo "❌ Failed to checkout version $VERSION"
    exit 1
fi

# 3. Build new images
echo "Building new images..."
docker-compose -f docker-compose.prod.yml build
if [ $? -ne 0 ]; then
    echo "❌ Failed to build images"
    exit 1
fi

# 4. Run database migrations
echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm gitte-app python -m alembic upgrade head
if [ $? -ne 0 ]; then
    echo "❌ Database migration failed"
    exit 1
fi

# 5. Rolling update
echo "Performing rolling update..."
docker-compose -f docker-compose.prod.yml up -d --no-deps gitte-app

# 6. Health check
echo "Waiting for application to be ready..."
sleep 30
for i in {1..12}; do
    curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Application is healthy"
        break
    fi
    if [ $i -eq 12 ]; then
        echo "❌ Application health check failed"
        echo "Rolling back..."
        git checkout -
        docker-compose -f docker-compose.prod.yml up -d --no-deps gitte-app
        exit 1
    fi
    echo "Waiting for application... ($i/12)"
    sleep 10
done

# 7. Smoke tests
echo "Running smoke tests..."
./scripts/smoke-tests.sh
if [ $? -ne 0 ]; then
    echo "❌ Smoke tests failed"
    echo "Rolling back..."
    git checkout -
    docker-compose -f docker-compose.prod.yml up -d --no-deps gitte-app
    exit 1
fi

# 8. Update other services if needed
echo "Updating other services..."
docker-compose -f docker-compose.prod.yml up -d

echo "✅ Deployment completed successfully"

# 9. Post-deployment verification
echo "Running post-deployment verification..."
./scripts/health-check.sh

# 10. Notification
echo "Sending deployment notification..."
# curl -X POST -H 'Content-type: application/json' \
#     --data "{\"text\":\"GITTE version $VERSION deployed successfully\"}" \
#     $SLACK_WEBHOOK_URL
```

### Rollback Procedure

**Scenario:** Deployment issues requiring immediate rollback

**Procedure:**
```bash
#!/bin/bash
# Emergency rollback procedure

PREVIOUS_VERSION="$1"
if [ -z "$PREVIOUS_VERSION" ]; then
    echo "Usage: $0 <previous_version>"
    exit 1
fi

echo "Starting emergency rollback to version $PREVIOUS_VERSION"

# 1. Checkout previous version
echo "Checking out previous version..."
git checkout $PREVIOUS_VERSION

# 2. Rebuild images
echo "Rebuilding images..."
docker-compose -f docker-compose.prod.yml build

# 3. Stop current services
echo "Stopping current services..."
docker-compose -f docker-compose.prod.yml stop gitte-app

# 4. Rollback database (if needed)
echo "Checking if database rollback is needed..."
# This would require careful consideration and testing

# 5. Start services with previous version
echo "Starting services with previous version..."
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify rollback
echo "Verifying rollback..."
sleep 30
curl -f http://localhost:8501/_stcore/health
if [ $? -eq 0 ]; then
    echo "✅ Rollback completed successfully"
else
    echo "❌ Rollback verification failed"
    exit 1
fi

echo "Emergency rollback completed"
```

---

## 🚨 Incident Response

### Incident Classification

#### Severity Levels

**Critical (P0):**
- Complete system outage
- Data loss or corruption
- Security breach
- Response Time: 15 minutes

**High (P1):**
- Major feature unavailable
- Significant performance degradation
- High error rates (>5%)
- Response Time: 1 hour

**Medium (P2):**
- Minor feature issues
- Moderate performance issues
- Error rates 1-5%
- Response Time: 4 hours

**Low (P3):**
- Cosmetic issues
- Documentation problems
- Enhancement requests
- Response Time: 24 hours

### Incident Response Procedure

#### Initial Response (0-15 minutes)

1. **Acknowledge the incident**
   - Update incident status to "Investigating"
   - Assign incident commander
   - Create incident channel/room

2. **Initial assessment**
   ```bash
   # Quick system check
   docker-compose ps
   curl -f http://localhost:8501/_stcore/health
   docker stats --no-stream
   ```

3. **Immediate mitigation**
   - If service down: Restart service
   - If high load: Scale up resources
   - If security issue: Isolate affected systems

#### Investigation Phase (15-60 minutes)

1. **Gather information**
   ```bash
   # Collect logs
   docker-compose logs --since=1h > incident-logs.txt
   
   # System metrics
   docker stats --no-stream > incident-metrics.txt
   
   # Database status
   docker-compose exec postgres psql -U gitte -d kiro_test -c "
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   " > incident-db-status.txt
   ```

2. **Root cause analysis**
   - Review recent changes
   - Analyze error patterns
   - Check external dependencies
   - Review monitoring data

3. **Implement fix**
   - Apply hotfix if available
   - Rollback if necessary
   - Scale resources if needed

#### Resolution Phase (1-4 hours)

1. **Verify fix**
   ```bash
   # Run health checks
   ./scripts/health-check.sh
   
   # Monitor for 30 minutes
   watch -n 60 'curl -f http://localhost:8501/_stcore/health'
   ```

2. **Update stakeholders**
   - Notify users of resolution
   - Update incident status
   - Schedule post-mortem

3. **Document incident**
   - Timeline of events
   - Root cause
   - Resolution steps
   - Lessons learned

### Post-Incident Review

**Objective:** Learn from incidents to prevent recurrence.

**Process:**
1. **Schedule review meeting** (within 48 hours)
2. **Prepare incident report**
3. **Identify action items**
4. **Update runbooks and procedures**
5. **Implement preventive measures**

**Incident Report Template:**
```markdown
# Incident Report: [Title]

**Date:** [Date]
**Duration:** [Start time] - [End time]
**Severity:** [P0/P1/P2/P3]
**Incident Commander:** [Name]

## Summary
Brief description of what happened.

## Timeline
- [Time]: Event 1
- [Time]: Event 2
- [Time]: Resolution

## Root Cause
Detailed analysis of what caused the incident.

## Resolution
Steps taken to resolve the incident.

## Impact
- Users affected: [Number]
- Services affected: [List]
- Revenue impact: [Amount]

## Action Items
- [ ] Action 1 - Owner: [Name] - Due: [Date]
- [ ] Action 2 - Owner: [Name] - Due: [Date]

## Lessons Learned
What we learned and how we can prevent similar incidents.
```

---

## 🔧 Maintenance Windows

### Scheduled Maintenance

**Schedule:** First Sunday of each month, 02:00-06:00 UTC

**Notification:** 7 days advance notice to users

### Maintenance Procedure

#### Pre-Maintenance (T-24 hours)

```bash
#!/bin/bash
# Pre-maintenance checklist

echo "=== Pre-Maintenance Checklist ==="

# 1. Verify backup completion
echo "1. Checking recent backups..."
ls -la /backups/ | tail -5

# 2. Test backup integrity
echo "2. Testing backup integrity..."
gunzip -t /backups/database_*.sql.gz | tail -1

# 3. Prepare maintenance scripts
echo "3. Preparing maintenance scripts..."
chmod +x scripts/maintenance/*.sh

# 4. Notify users
echo "4. User notification sent: $(date)"

# 5. Prepare rollback plan
echo "5. Rollback plan prepared"

echo "Pre-maintenance checklist completed"
```

#### During Maintenance

```bash
#!/bin/bash
# Maintenance execution script

echo "=== Starting Maintenance Window ==="

# 1. Enable maintenance mode
echo "1. Enabling maintenance mode..."
# Display maintenance page to users

# 2. Stop application services
echo "2. Stopping application services..."
docker-compose stop gitte-app

# 3. Perform database maintenance
echo "3. Performing database maintenance..."
docker-compose exec postgres psql -U gitte -d kiro_test -c "VACUUM ANALYZE;"
docker-compose exec postgres psql -U gitte -d kiro_test -c "REINDEX DATABASE kiro_test;"

# 4. Update system packages
echo "4. Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 5. Update Docker images
echo "5. Updating Docker images..."
docker-compose pull

# 6. Clean up old data
echo "6. Cleaning up old data..."
# Remove old logs, temporary files, etc.
find /var/log -name "*.log" -mtime +30 -delete
docker system prune -f

# 7. Restart services
echo "7. Restarting services..."
docker-compose up -d

# 8. Verify system health
echo "8. Verifying system health..."
sleep 60
./scripts/health-check.sh

# 9. Disable maintenance mode
echo "9. Disabling maintenance mode..."
# Remove maintenance page

echo "=== Maintenance Window Completed ==="
```

#### Post-Maintenance

```bash
#!/bin/bash
# Post-maintenance verification

echo "=== Post-Maintenance Verification ==="

# 1. Full system health check
echo "1. Running full health check..."
./scripts/health-check.sh

# 2. Performance verification
echo "2. Verifying performance..."
# Run performance tests

# 3. User acceptance testing
echo "3. Running user acceptance tests..."
# Automated UAT suite

# 4. Monitor for issues
echo "4. Monitoring for issues..."
# Enhanced monitoring for 24 hours

# 5. Notify users
echo "5. Notifying users of completion..."

echo "Post-maintenance verification completed"
```

---

## 📈 Capacity Planning

### Resource Monitoring

**Metrics to Track:**
- CPU utilization trends
- Memory usage patterns
- Disk space growth
- Network bandwidth usage
- Database size growth
- User growth rate

### Capacity Planning Script

```bash
#!/bin/bash
# Capacity planning data collection

echo "=== Capacity Planning Report - $(date) ==="

# 1. Current resource usage
echo "1. Current Resource Usage:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free | awk 'NR==2{printf "%.0f%%", $3*100/$2}')"
echo "Disk: $(df / | awk 'NR==2 {print $5}')"

# 2. Database growth
echo "2. Database Growth:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# 3. User growth
echo "3. User Growth:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT 
    DATE(created_at) as date,
    COUNT(*) as new_users
FROM users 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
"

# 4. Activity trends
echo "4. Activity Trends:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT 
    DATE(created_at) as date,
    COUNT(*) as interactions,
    COUNT(DISTINCT user_id) as active_users
FROM audit_logs 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
"

echo "=== Capacity Planning Report Completed ==="
```

### Scaling Triggers

| Metric | Scale Up Trigger | Scale Down Trigger |
|--------|------------------|-------------------|
| CPU Usage | >70% for 10 minutes | <30% for 30 minutes |
| Memory Usage | >80% for 5 minutes | <40% for 30 minutes |
| Response Time | P95 >3s for 5 minutes | P95 <1s for 30 minutes |
| Queue Length | >100 requests | <10 requests |
| Error Rate | >2% for 5 minutes | <0.5% for 30 minutes |

---

## 🔒 Security Operations

### Security Monitoring

**Daily Security Checks:**
```bash
#!/bin/bash
# Daily security monitoring

echo "=== Daily Security Check - $(date) ==="

# 1. Check for failed login attempts
echo "1. Failed Login Attempts (last 24h):"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT COUNT(*) as failed_logins
FROM audit_logs 
WHERE operation = 'login' 
AND status = 'error' 
AND created_at >= NOW() - INTERVAL '24 hours';
"

# 2. Check for suspicious activity
echo "2. Suspicious Activity:"
docker-compose exec -T postgres psql -U gitte -d kiro_test -c "
SELECT user_id, COUNT(*) as request_count
FROM audit_logs 
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY user_id 
HAVING COUNT(*) > 100
ORDER BY request_count DESC;
"

# 3. Check SSL certificate expiry
echo "3. SSL Certificate Status:"
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# 4. Check for security updates
echo "4. Security Updates Available:"
apt list --upgradable 2>/dev/null | grep -i security | wc -l

echo "=== Security Check Completed ==="
```

### Security Incident Response

**Procedure for Security Incidents:**

1. **Immediate Response (0-15 minutes):**
   - Isolate affected systems
   - Preserve evidence
   - Notify security team

2. **Investigation (15-60 minutes):**
   - Analyze logs for breach indicators
   - Identify scope of compromise
   - Document timeline

3. **Containment (1-4 hours):**
   - Block malicious IPs
   - Reset compromised credentials
   - Apply security patches

4. **Recovery (4-24 hours):**
   - Restore from clean backups
   - Implement additional security measures
   - Monitor for continued threats

5. **Post-Incident (24-72 hours):**
   - Conduct forensic analysis
   - Update security procedures
   - Notify relevant authorities if required

---

**Document Version:** 1.0  
**Last Updated:** December 2024  
**Next Review:** March 2025  
**Owner:** Operations Team