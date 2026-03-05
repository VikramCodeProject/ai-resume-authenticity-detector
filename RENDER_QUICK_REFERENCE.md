# Render Deployment - Quick Reference

## Files Created/Updated for Render Deployment

### Core Configuration
- ✅ **render.yaml** - Blueprint configuration for all 4 services
- ✅ **Procfile** - Updated with gunicorn for production
- ✅ **backend/requirements.txt** - Added gunicorn
- ✅ **.env.render.production** - Template for production environment

### Documentation
- ✅ **RENDER_DEPLOYMENT_GUIDE.md** - Complete 60+ step guide
- ✅ **RENDER_DEPLOYMENT_CHECKLIST.md** - Pre/post deployment checklist
- ✅ **RENDER_DEPLOYMENT_READY.md** - Quick summary and overview

### Infrastructure
- ✅ **docker/Dockerfile.postgres** - PostgreSQL container (optional)
- ✅ **docker/Dockerfile.redis** - Redis container (optional)

### Helper Scripts
- ✅ **render-setup.sh** - Linux/Mac validation script
- ✅ **render-setup.bat** - Windows validation script

---

## Deployment in 4 Steps

### 1️⃣ Push to GitHub
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2️⃣ Create Render Blueprint
1. Go to https://dashboard.render.com
2. Click "New+" → "Blueprint"
3. Connect GitHub account
4. Select your repository
5. Click "Create Blueprint"

### 3️⃣ Wait for Build (5-10 minutes)
- Services will build and deploy automatically
- Status: Check dashboard

### 4️⃣ Set Environment Variables
Dashboard → Backend Service → Environment

**Required Variables**:
```
JWT_SECRET=<generate-random-32-char-string>
GITHUB_API_KEY=<your-token>
LINKEDIN_API_KEY=<your-token>
AWS_S3_BUCKET=<your-bucket>
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

**Optional (for blockchain)**:
```
SMART_CONTRACT_ADDRESS=<your-contract>
PRIVATE_KEY=<your-wallet-key>
```

---

## Services Deployed

| Service | Runtime | Port | Status |
|---------|---------|------|--------|
| Backend | Python 3.11 | 8000 | Web Service |
| Frontend | Node 18 | 3000 | Web Service |
| PostgreSQL | 15-alpine | 5432 | Managed DB |
| Redis | 7-alpine | 6379 | Managed Cache |

---

## Testing After Deployment

✅ **Backend API**: https://your-backend.onrender.com/docs
✅ **Frontend**: https://your-frontend.onrender.com
✅ **Health Check**: https://your-backend.onrender.com/api/health
✅ **Database**: Connected through PostgreSQL service
✅ **Cache**: Connected through Redis service

---

## Environment Variables Auto-Linked

These are automatically set by Render:
```
DATABASE_URL     ← From PostgreSQL service
REDIS_URL        ← From Redis service
FRONTEND_URL     ← From Frontend service URL
VITE_API_URL     ← From Backend service URL
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails | Check logs: Dashboard → Service → Logs |
| Services won't start | Verify env variables are set |
| Connection timeout | Ensure Database is healthy status |
| Slow performance | Upgrade to Starter tier |
| CORS errors | Check FRONTEND_URL is set correctly |

---

## Important Notes

⚠️ **Ephemeral File System**
- Render's file system resets on deploy
- Use AWS S3 for file storage, NOT local disk
- Configure `AWS_S3_BUCKET` environment variables

⚠️ **Cold Boots** (Free/Starter tiers)
- Services spin down after 15 min inactivity
- Upgrade to Standard tier to avoid

⚠️ **Secrets Management**
- Never commit .env files with real credentials
- Set secrets in Render Dashboard
- Use `sync: false` in render.yaml for sensitive vars

---

## Useful Links

- **Dashboard**: https://dashboard.render.com
- **Docs**: https://render.com/docs
- **Support**: support@render.com
- **Status**: https://status.render.com

---

## Database Management

### Backups (Render PostgreSQL)
- Automated daily backups
- 30-day retention
- Admin dashboard to browse backups

### Connection
- Automatically linked to backend service
- No external access by default (secure)
- Use connection string provided

### Upgrades
- Free tier: 500MB
- Paid tier: Unlimited storage

---

## Cost Summary

| Tier | Free | Starter |
|------|------|---------|
| Backend | $0* | $7/month |
| Frontend | $0* | $7/month |
| Database | Free 500MB | $15/month |
| Redis | Free 100MB | $15/month |
| **Total** | **$0** | **$44/month** |

*Free tier has limitations: cold boots, shared resources, limited compute

---

## File Size & Limits

- Max build time: 45 minutes
- Max deploy size: 1 GB
- Max request size: 100 MB
- Max response size: 100 MB
- Max concurrent requests: Limited by tier

---

## Monitoring

### View Logs
```
Dashboard → Service Name → Logs
```

### Health Status
- All services show green checkmark when healthy
- Failed services show red X
- Auto-restart on health check failure

### Metrics (Optional)
- Response times
- Error rates
- Resource usage
- Uptime percentage

---

## Custom Domain Setup

1. Purchase domain from registrar
2. Dashboard → Frontend → Settings → Add Custom Domain
3. Update DNS records (CNAME to onrender.com domain)
4. Wait for SSL certificate (auto-generated)
5. Access via custom domain

---

## Auto-Deployment Configuration

Changes to GitHub auto-trigger deployment:
```yaml
autoDeploy: true
```

- Push to branch → Automatic deployment
- No manual trigger needed
- ~7-15 min deployment time
- Zero downtime (blue-green deployment)

---

## Scaling Configuration (Future)

When your app grows:

1. **Increase Compute**
   - Upgrade service plan tier
   - Add more gunicorn workers

2. **Database Scaling**
   - Upgrade PostgreSQL tier
   - Add read replicas

3. **Caching**
   - Increase Redis tier
   - Configure cache invalidation

4. **CDN** (Paid feature)
   - Global content delivery
   - Reduced latency

---

## Post-Deployment Checklist

- [ ] All services showing "Live" status
- [ ] Backend `/docs` page accessible
- [ ] Frontend page loads without CSS/JS errors
- [ ] Can upload and verify resumes
- [ ] Database persists data across restarts
- [ ] Redis cache is functioning
- [ ] No errors in service logs
- [ ] Response time < 2 seconds
- [ ] HTTPS working on all services
- [ ] Monitoring/alerts configured (optional)

---

**Ready to Deploy?** 
→ Go to RENDER_DEPLOYMENT_GUIDE.md for step-by-step instructions
→ Use RENDER_DEPLOYMENT_CHECKLIST.md to verify everything before/after

**Questions?**
→ Check RENDER_DEPLOYMENT_READY.md for detailed info
→ Visit https://render.com/docs for official documentation
