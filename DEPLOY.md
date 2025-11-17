# Quick Deployment Guide

Get your Poker Analysis Platform live in production in ~30 minutes.

## Prerequisites

- GitHub account (you already have this!)
- Supabase account (free): https://supabase.com
- Railway account (free): https://railway.app
- Vercel account (free): https://vercel.com
- Anthropic API key: https://console.anthropic.com

## Step-by-Step Deployment

### 1. Database (Supabase) - 5 minutes

1. **Create Project**
   - Go to https://supabase.com/dashboard
   - Click "New Project"
   - Name: `poker-analysis`
   - Database Password: (create strong password)
   - Region: Choose closest to you
   - Wait ~2 minutes for provisioning

2. **Run Database Schema**
   - Click "SQL Editor" in sidebar
   - Click "New Query"
   - Copy entire contents of `backend/database_schema.sql`
   - Paste and click "Run"
   - Verify 5 tables created

3. **Get Connection String**
   - Click "Settings" → "Database"
   - Copy "Connection string" (Pooling mode)
   - Format: `postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres`
   - **Save this** - you'll need it for backend!

✅ Database ready!

---

### 2. Backend (Railway) - 10 minutes

1. **Connect GitHub**
   - Go to https://railway.app
   - Click "Login" → "Login with GitHub"
   - Authorize Railway

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Search and select `Ploit`
   - Railway auto-detects `railway.json` and `Dockerfile`

3. **Add Environment Variables**
   - Click your service → "Variables" tab
   - Add these variables:

   ```
   DATABASE_URL=<your-supabase-connection-string>
   ANTHROPIC_API_KEY=<your-anthropic-key>
   ALLOWED_ORIGINS=*
   ENVIRONMENT=production
   ```

   **Important**: For `DATABASE_URL`, use the connection string from Step 1.3

4. **Deploy**
   - Click "Deploy"
   - Wait ~3-5 minutes for build
   - Click "Deployments" to see logs

5. **Get Backend URL**
   - Click "Settings" → "Networking"
   - Click "Generate Domain"
   - Copy your URL (e.g., `https://your-app.up.railway.app`)
   - **Save this** - you'll need it for frontend!

6. **Verify Deployment**
   - Visit `https://your-app.up.railway.app/api/health`
   - Should see: `{"status":"healthy","database":"connected"}`
   - Visit `https://your-app.up.railway.app/docs`
   - Should see Swagger API documentation

✅ Backend deployed!

---

### 3. Frontend (Vercel) - 10 minutes

1. **Connect GitHub**
   - Go to https://vercel.com
   - Click "Login" → "Continue with GitHub"
   - Authorize Vercel

2. **Import Project**
   - Click "Add New" → "Project"
   - Find and select `Ploit` repository
   - Click "Import"

3. **Configure Project**
   - Framework Preset: **Vite**
   - Root Directory: **frontend** (very important!)
   - Build Command: `npm run build`
   - Output Directory: `dist`

4. **Add Environment Variable**
   - Expand "Environment Variables"
   - Add:
     ```
     VITE_API_URL=<your-railway-backend-url>
     ```
   - Use the URL from Step 2.5 (without trailing slash)

5. **Deploy**
   - Click "Deploy"
   - Wait ~2-3 minutes for build
   - Vercel will show you the live URL

6. **Get Frontend URL**
   - Copy your Vercel URL (e.g., `https://poker-analysis.vercel.app`)

✅ Frontend deployed!

---

### 4. Final Configuration - 5 minutes

1. **Update CORS**
   - Go back to Railway
   - Click your service → "Variables"
   - Update `ALLOWED_ORIGINS` to your Vercel URL:
     ```
     ALLOWED_ORIGINS=https://your-app.vercel.app
     ```
   - Railway will auto-redeploy (~1 minute)

2. **Test Everything**
   - Visit your Vercel URL
   - Dashboard should load with stats showing 0
   - Click "Upload" - page should load
   - Try uploading a test .txt file (if you have one)

✅ Full deployment complete!

---

## Verification Checklist

Use the automated health check:

```bash
./healthcheck.sh
```

Or manually verify:

- [ ] Backend health: `https://your-backend.railway.app/api/health`
- [ ] Backend docs: `https://your-backend.railway.app/docs`
- [ ] Frontend loads: `https://your-frontend.vercel.app`
- [ ] Dashboard shows stats (0 initially)
- [ ] Upload page accessible
- [ ] Players page accessible
- [ ] Claude chat page accessible

## Your Live URLs

Once deployed, bookmark these:

- **Frontend**: https://your-app.vercel.app
- **Backend API**: https://your-app.up.railway.app
- **API Docs**: https://your-app.up.railway.app/docs
- **Supabase Dashboard**: https://supabase.com/dashboard/project/your-project

## Common Issues

### "Database connection failed"

- Check `DATABASE_URL` is correct in Railway
- Verify Supabase project is running
- Test connection string with `psql`

### "CORS error" in browser console

- Update `ALLOWED_ORIGINS` in Railway to match your Vercel URL exactly
- No trailing slash in URL
- Wait for Railway to redeploy

### "Claude API error"

- Verify `ANTHROPIC_API_KEY` is set in Railway
- Check key is valid at https://console.anthropic.com
- Ensure you have API credits

### Frontend shows "Failed to fetch"

- Check `VITE_API_URL` in Vercel is correct
- Verify backend is running (visit `/api/health`)
- Check browser console for specific errors

## Next Steps

1. **Upload hand histories** - Test with your PokerStars .txt files
2. **Verify stats calculate** - Check player profiles
3. **Test Claude AI** - Ask strategic questions
4. **Monitor costs**:
   - Supabase Free: 500MB database (upgrade if needed)
   - Railway Free: $5/month credit
   - Vercel Free: Unlimited for hobby projects
   - Anthropic: Pay per use (~$0.01/query)

5. **Set up monitoring**:
   - Railway: Built-in metrics
   - Vercel: Built-in analytics
   - Supabase: Database metrics

## Scaling

When you hit limits:

- **Database full**: Upgrade Supabase plan ($25/month for 8GB)
- **Backend slow**: Upgrade Railway plan ($20/month)
- **Too many users**: Add Redis caching, connection pooling

## Support

- Railway: https://railway.app/help
- Vercel: https://vercel.com/support
- Supabase: https://supabase.com/support
- Project issues: https://github.com/your-username/Ploit/issues

## Deployment Scripts

- `./deploy.sh` - Interactive deployment helper
- `./healthcheck.sh` - Post-deployment verification
- `docs/DEPLOYMENT_CHECKLIST.md` - Detailed checklist

---

**You're live! 🎉**

Your poker analysis platform is now running in production on:
- ⚡ Railway (Backend)
- 🎨 Vercel (Frontend)
- 🗄️ Supabase (Database)
- 🤖 Anthropic Claude (AI)

Time to analyze some poker hands!
