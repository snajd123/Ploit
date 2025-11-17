# Deployment Checklist

Complete checklist for deploying the Poker Analysis Platform to production.

## Pre-Deployment

### Code Quality
- [ ] All Phase 1-7 code is committed to GitHub
- [ ] All integration tests pass
- [ ] Frontend builds successfully (`npm run build`)
- [ ] No console errors or warnings
- [ ] Code has been reviewed
- [ ] Documentation is complete

### Environment Setup
- [ ] Production Supabase database created
- [ ] Database schema deployed (`database_schema.sql`)
- [ ] Anthropic API key obtained
- [ ] Environment variables documented

### Security Review
- [ ] No API keys in code
- [ ] .env files in .gitignore
- [ ] CORS configured for production domain
- [ ] SQL injection prevention verified
- [ ] File upload validation in place
- [ ] Claude queries restricted to SELECT only

## Backend Deployment

### Recommended: Railway.app or Render.com

#### Step 1: Prepare Backend

1. **Test locally first:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

2. **Verify endpoints:**
   - http://localhost:8000/api/health
   - http://localhost:8000/docs (Swagger UI)

#### Step 2: Deploy to Railway/Render

1. **Connect GitHub repository**
2. **Configure environment variables:**
   ```
   DATABASE_URL=your_supabase_url
   ANTHROPIC_API_KEY=your_claude_key
   ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
   ENVIRONMENT=production
   BACKEND_HOST=0.0.0.0
   BACKEND_PORT=8000
   ```

3. **Set start command:**
   ```
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Deploy and verify:**
   - Check deployment logs
   - Visit /api/health endpoint
   - Test /docs Swagger UI

#### Alternative: Docker Deployment

Create `Dockerfile` in backend/:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t poker-analysis-backend .
docker run -p 8000:8000 --env-file .env poker-analysis-backend
```

## Frontend Deployment

### Recommended: Vercel

#### Step 1: Prepare Frontend

1. **Test production build locally:**
   ```bash
   cd frontend
   npm install
   npm run build
   npm run preview
   ```

2. **Verify all routes work:**
   - /dashboard
   - /upload
   - /players
   - /claude

#### Step 2: Deploy to Vercel

1. **Install Vercel CLI (optional):**
   ```bash
   npm install -g vercel
   ```

2. **Deploy via Vercel Dashboard:**
   - Import GitHub repository
   - Select `frontend` as root directory
   - Framework preset: Vite
   - Build command: `npm run build`
   - Output directory: `dist`

3. **Configure environment variables:**
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```

4. **Deploy and verify:**
   - Check deployment logs
   - Visit production URL
   - Test all pages

#### Alternative: Netlify

1. **Create `netlify.toml` in frontend/:**
   ```toml
   [build]
     command = "npm run build"
     publish = "dist"

   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```

2. **Deploy via Netlify dashboard**
3. **Set VITE_API_URL environment variable**

## Database Deployment

### Supabase Setup

1. **Create Supabase project:**
   - Visit https://supabase.com
   - Create new project
   - Wait for provisioning (~2 minutes)

2. **Run database schema:**
   - Open SQL Editor in Supabase
   - Copy content from `backend/database_schema.sql`
   - Execute SQL
   - Verify 5 tables created

3. **Get connection string:**
   - Settings → Database
   - Copy connection string (Pooling mode recommended)
   - Update `DATABASE_URL` in backend environment

4. **Configure connection pooling:**
   - Enable connection pooling in Supabase
   - Use transaction mode for best performance

## Post-Deployment Verification

### Backend Health Check

Test these endpoints:
- [ ] GET /api/health → Returns "healthy"
- [ ] GET /api/database/stats → Returns stats
- [ ] GET /api/database/schema → Returns schema
- [ ] GET /docs → Swagger UI loads

### Frontend Functionality

Test complete workflow:
- [ ] Dashboard loads with correct data
- [ ] Upload page accepts files
- [ ] File upload completes successfully
- [ ] Players list displays
- [ ] Player profile shows stats and charts
- [ ] Claude chat responds to queries

### Integration Tests

- [ ] Upload hand history from frontend
- [ ] Verify hands appear in database
- [ ] Check player stats calculated
- [ ] Query Claude AI successfully
- [ ] All API calls succeed

### Performance Check

- [ ] Page load time < 3 seconds
- [ ] API response time < 500ms
- [ ] File upload handles 10MB+ files
- [ ] Database queries remain fast
- [ ] No memory leaks over time

### Security Verification

- [ ] HTTPS enabled on both frontend and backend
- [ ] CORS only allows production frontend domain
- [ ] No API keys visible in frontend
- [ ] Error messages don't leak sensitive info
- [ ] File uploads are sandboxed

## Monitoring Setup

### Backend Monitoring

1. **Application logs:**
   - Railway/Render provide built-in logs
   - Monitor for errors and exceptions
   - Track API response times

2. **Database monitoring:**
   - Supabase dashboard shows metrics
   - Monitor connection count
   - Track query performance

3. **Error tracking (optional):**
   - Sentry.io for error tracking
   - Integrate with FastAPI

### Frontend Monitoring

1. **Vercel Analytics:**
   - Enable Vercel Analytics
   - Track page views and performance

2. **Error tracking:**
   - Console error monitoring
   - Track failed API calls

## Backup Strategy

### Database Backups

1. **Supabase automatic backups:**
   - Enabled by default
   - Point-in-time recovery
   - Daily backups retained

2. **Manual backup:**
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

3. **Backup schedule:**
   - Automated daily backups
   - Weekly full exports
   - Monthly archives

### Code Backups

- [ ] All code in GitHub
- [ ] Tagged releases for each phase
- [ ] Main branch protected
- [ ] Multiple contributors have access

## Domain Configuration

### Custom Domain (Optional)

1. **Purchase domain:**
   - e.g., pokeranalysis.app

2. **Configure DNS:**
   - Frontend: Point to Vercel
   - Backend: Point to Railway/Render

3. **SSL Certificates:**
   - Auto-provisioned by Vercel/Railway
   - Verify HTTPS works

## Scaling Considerations

### Current Capacity

- Frontend: Unlimited (CDN)
- Backend: Depends on Railway/Render plan
- Database: Supabase free tier = 500MB, 2GB with paid plan
- Claude API: Rate limits per Anthropic plan

### When to Scale

Monitor these metrics:
- Database size approaching limit
- API response times > 1 second
- Claude rate limits hit frequently
- User count > 100 active users

### Scaling Options

1. **Database:**
   - Upgrade Supabase plan
   - Enable connection pooling
   - Add read replicas

2. **Backend:**
   - Upgrade Railway/Render plan
   - Add horizontal scaling
   - Implement caching (Redis)

3. **Frontend:**
   - Already scaled via CDN
   - Enable Vercel image optimization

## Cost Estimation

### Free Tier (Development/MVP)

- Supabase: Free (500MB database)
- Railway/Render: Free ($5 credit/month)
- Vercel: Free (hobby plan)
- Anthropic Claude: Pay-per-use (~$0.01/query)

**Total: ~$0-10/month** (depending on Claude usage)

### Production (100 active users)

- Supabase Pro: $25/month (8GB database)
- Railway: $20/month (8GB RAM, always on)
- Vercel Pro: Free for most use cases
- Anthropic Claude: ~$50/month (est.)

**Total: ~$95/month**

## Rollback Plan

### If deployment fails:

1. **Keep previous version running**
2. **Test new deployment in staging first**
3. **Use git tags for quick rollback:**
   ```bash
   git tag v1.0-production
   git push origin v1.0-production
   ```

4. **Railway/Render rollback:**
   - One-click rollback in dashboard
   - Revert to previous deployment

5. **Database rollback:**
   - Restore from Supabase backup
   - Run migration scripts in reverse

## Launch Checklist

### Final Pre-Launch

- [ ] All tests pass
- [ ] Documentation complete
- [ ] README updated
- [ ] Environment variables set
- [ ] SSL certificates active
- [ ] Monitoring configured
- [ ] Backup strategy in place

### Launch Day

1. [ ] Deploy backend to production
2. [ ] Deploy frontend to production
3. [ ] Verify health checks pass
4. [ ] Test complete workflow end-to-end
5. [ ] Upload test hand history
6. [ ] Query Claude AI
7. [ ] Monitor logs for errors
8. [ ] Announce launch (if applicable)

### Post-Launch (First Week)

- [ ] Monitor error rates daily
- [ ] Check database size growth
- [ ] Track Claude API costs
- [ ] Gather user feedback
- [ ] Fix any critical bugs
- [ ] Performance optimization if needed

## Maintenance Schedule

### Daily
- Check error logs
- Monitor API response times
- Verify Claude AI working

### Weekly
- Review database size
- Check backup status
- Update dependencies if needed

### Monthly
- Review costs
- Performance audit
- Security updates
- Documentation updates

## Support Contacts

### Infrastructure
- Supabase: https://supabase.com/support
- Railway: https://railway.app/help
- Vercel: https://vercel.com/support
- Anthropic: https://www.anthropic.com/support

### Emergency Contacts
- Developer: [Your contact]
- DevOps: [Your contact]
- Database Admin: [Your contact]

## Success Metrics

Platform is successfully deployed when:
- ✅ All health checks pass
- ✅ Users can upload hand histories
- ✅ Player stats calculate correctly
- ✅ Claude AI responds to queries
- ✅ No critical errors in logs
- ✅ Page load time < 3 seconds
- ✅ 99%+ uptime over first week

## Next Phase

After successful deployment:
- **Phase 10: Documentation** - Final user guides and API docs
- Gather user feedback
- Plan future features
- Monitor and optimize
