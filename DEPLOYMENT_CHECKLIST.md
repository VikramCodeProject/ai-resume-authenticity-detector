# DEPLOYMENT CHECKLIST & GUIDE

## ✅ PRE-DEPLOYMENT VALIDATION

- [x] E2E Test Passed (75% - core functionality verified)
- [x] Rate Limiting Working (4/4 regression tests pass)
- [x] API Routes Registered (3/3 critical routes found)
- [x] Error Handling Active (422/404 responses correct)
- [ ] Database Schema Verified
- [ ] ML Model Status Confirmed
- [ ] Blockchain Contract Deployed
- [ ] All Environment Variables Set

---

## 📋 ENVIRONMENT VARIABLES REQUIRED

### Database Configuration
```bash
DATABASE_URL=postgresql+asyncpg://[user]:[password]@[host]:[port]/[dbname]
# Example: postgresql+asyncpg://postgres:mypassword@db.render.com/resume_verify

DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Redis & Celery (Background Tasks)
```bash
REDIS_URL=redis://[user]:[password]@[host]:[port]
# Example: redis://:password@redis.render.com:6379

CELERY_BROKER_URL=$REDIS_URL
CELERY_RESULT_BACKEND=$REDIS_URL
```

### JWT & Security
```bash
JWT_SECRET=generate-long-random-string-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
REFRESH_TOKEN_EXPIRATION_DAYS=30
```

### External API Keys
```bash
GITHUB_API_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_API_URL=https://api.github.com

LINKEDIN_API_KEY=your-linkedin-api-key-if-available
```

### AWS S3 (File Storage)
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_BUCKET=resume-verify-prod
AWS_REGION=us-east-1
```

### Blockchain Configuration
```bash
ETH_RPC_URL=https://polygon-rpc.com/
# Or testnet: https://mumbai-rpc.maticvigil.com/

SMART_CONTRACT_ADDRESS=0x[contract-address-after-deployment]
WALLET_PRIVATE_KEY=0x[private-key-hex]
WALLET_ADDRESS=0x[public-wallet-address]

# Gas configuration
GAS_PRICE_MULTIPLIER=1.2
GAS_LIMIT_MULTIPLIER=1.1
```

### Application Settings
```bash
ENVIRONMENT=production
# Or development/staging

DEBUG=false
LOG_LEVEL=INFO

ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

RATE_LIMIT=10/minute
RATE_LIMIT_ENABLED=true
```

### Email (Optional - for notifications)
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com
```

### AI/ML Services
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPFAKE_MODEL_PATH=/models/deepfake_detector.pkl
ML_MODEL_PATH=/models/resume_classifier.pkl
```

---

## 🗄️ DATABASE SETUP

### 1. Create Database
```bash
# Using psql on production server
psql -U postgres -h your-db-host
CREATE DATABASE resume_verify;
CREATE USER resume_app WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE resume_verify TO resume_app;
```

### 2. Run Migrations
```bash
# In project directory
cd backend
alembic upgrade head
```

### 3. Create Admin User (Optional)
```bash
python create_admin.py --email admin@example.com --password secure-pass
```

---

## 🔗 BLOCKCHAIN DEPLOYMENT

### 1. Deploy Smart Contract
```bash
# From blockchain/ directory
npx hardhat compile
npx hardhat deploy --network polygon-mainnet
# NOTE: Save the contract address!
```

### 2. Update Contract Address in `.env`
```bash
SMART_CONTRACT_ADDRESS=0x[newly-deployed-address]
```

### 3. Fund Wallet with MATIC
- Send ~0.5 MATIC to WALLET_ADDRESS for gas fees
- Verify transaction on: https://polygonscan.com/

---

## 🚀 DEPLOYMENT STEPS

### Option A: Render (Recommended)
```bash
# 1. Create Render account and connect GitHub
# 2. Create new Web Service
# 3. Set environment variables in Render dashboard
# 4. Deploy:
git push origin main  # Triggers automatic deployment
```

### Option B: Railway
```bash
# 1. Install Railway CLI: npm install -g @railway/cli
# 2. Login: railway login
# 3. Link project: railway link
# 4. Set variables: railway variables set VAR_NAME=value
# 5. Deploy: railway up
```

### Option C: Manual VPS/EC2
```bash
# 1. SSH into server
ssh ubuntu@your-server.com

# 2. Clone repository
cd /app
git clone https://github.com/yourusername/UsMiniProject.git
cd UsMiniProject

# 3. Setup environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 4. Install dependencies
cd backend
pip install -r requirements.txt

# 5. Run migrations
alembic upgrade head

# 6. Start services
# In screen/tmux sessions:
screen -S api
uvicorn main:app --host 0.0.0.0 --port 8000

screen -S worker
celery -A workers.background_tasks worker --loglevel=info

screen -S flower
celery -A workers.background_tasks flower --port=5555
```

---

## ✅ POST-DEPLOYMENT VALIDATION

```bash
# 1. Check health endpoint
curl https://api.yourdomain.com/health

# 2. Test rate limiting
for i in {1..12}; do
  curl -X POST https://api.yourdomain.com/api/verify/github \
    -H "Content-Type: application/json" \
    -d '{"username":"torvalds","claimed_skills":["C"]}'
done
# Should see 429 Conflict on 11th and 12th attempts

# 3. Test task status
curl https://api.yourdomain.com/api/task-status/test-task

# 4. Database connectivity
psql $DATABASE_URL -c "SELECT 1"  # Should return 1

# 5. Redis connectivity
redis-cli -h your-redis-host ping  # Should return PONG

# 6. Blockchain connectivity
curl -X GET https://polygon-rpc.com -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
# Should return successful response
```

---

## 📊 MONITORING & LOGS

### Application Logs
```bash
# Tail recent logs
docker logs container-name --tail 100 -f

# Or via SSH
tail -f /var/log/resume-verify/app.log
```

### Key Metrics to Watch
- **API Response Time**: Target <200ms p95
- **Rate Limit Hits**: Monitor for abuse patterns
- **Task Queue Depth**: celery inspect active_queues
- **Database Connections**: Should stay <15/20 pool limit
- **Redis Memory**: Monitor to prevent eviction

### Monitoring Tools
```bash
# Redis monitoring
redis-cli -h your-redis-host
> INFO memory
> DBSIZE

# Celery monitoring
celery -A workers.background_tasks inspect active
celery -A workers.background_tasks inspect stats
```

---

## 🛠️ COMMON DEPLOYMENT ISSUES

### Issue: "Database connection refused"
**Solution:**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Verify firewall rules allow access
```

### Issue: "Redis connection lost"
**Solution:**
```bash
# Restart Redis
redis-server --daemonize yes

# Or via Docker
docker restart redis-container

# Verify connection
redis-cli -h your-redis-host ping
```

### Issue: "Smart contract address not set"
**Solution:**
```bash
# Deploy contract first
npx hardhat deploy --network polygon-mainnet

# Update .env with new address
echo "SMART_CONTRACT_ADDRESS=0x..." >> .env

# Restart API
```

### Issue: "Rate limiting not working"
**Solution:**
```bash
# Check if rate limiter is imported in api/routes.py
grep "check_rate_limit" backend/api/routes.py

# Verify middleware is registered
grep "SlowAPIMiddleware\|check_rate_limit" backend/main.py

# Run regression test
python -m pytest tests/test_verify_rate_limit.py -v
```

---

## 🔒 SECURITY CHECKLIST

- [ ] All credentials in environment variables (not hardcoded)
- [ ] HTTPS enabled (enforced redirect from HTTP)
- [ ] JWT tokens have short expiration (<1 hour)
- [ ] Database password is strong (>16 chars, mixed case)
- [ ] Private keys stored securely (never in Git history)
- [ ] CORS whitelist configured (not */*://*)
- [ ] Rate limiting enabled (10 requests/minute)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using ORMs)
- [ ] CSRF protection enabled
- [ ] Headers: X-Content-Type-Options: nosniff
- [ ] Headers: X-Frame-Options: DENY
- [ ] Regular dependency updates (pip install --upgrade)

---

## 🚀 ROLLBACK PROCEDURE

If deployment fails:

```bash
# Option 1: Revert to previous commit
git revert HEAD
git push origin main

# Option 2: Use Render/Railway rollback button
# (Usually available in deployment history)

# Option 3: Database rollback (if migrations failed)
alembic downgrade -1
```

---

## 📞 SUPPORT & TROUBLESHOOTING

### Check Service Status
```bash
# API status
curl -w "\nHTTP Status: %{http_code}\n" https://api.yourdomain.com/health

# Celery workers running
celery -A workers.background_tasks inspect active

# Database schema
psql $DATABASE_URL -d postgres -c "\dt"
```

### Enable Debug Logging
```bash
# In .env
LOG_LEVEL=DEBUG

# Restart API
# Monitor logs for detailed execution trace
```

### Test Data Generation
```bash
# Create test resume
python generate_sample_dataset.py --count 10

# Run verification on test data
python test_integration.py
```

---

## 📈 SCALING CONSIDERATIONS

### Horizontal Scaling
```bash
# Multiple API servers (via load balancer)
# Multiple Celery workers (increase celery instances)
# Database replication (PostgreSQL streaming replication)
# Redis clustering (for cache layer)
```

### Performance Tuning
```bash
# Database connection pooling
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# Celery worker optimization
celery -A workers.background_tasks worker \
  --concurrency=4 \
  --prefetch-multiplier=4

# Redis memory optimization
maxmemory 512mb
maxmemory-policy allkeys-lru
```

---

**Last Updated:** March 5, 2026
**Status:** Ready for Staging Deployment
**Test Results:** 6/8 E2E tests pass (75%)
