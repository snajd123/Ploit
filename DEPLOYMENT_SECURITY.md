# Deployment Security Guide

## 🔒 Important Security Principles

### NEVER Share Your Credentials

**DO NOT share with anyone (including AI assistants):**
- ❌ API keys
- ❌ Database passwords
- ❌ Database connection strings
- ❌ Any credentials or secrets

### How Deployment Actually Works

You handle all credentials yourself through secure web interfaces:

1. **Railway Dashboard** - You paste environment variables into their secure UI
2. **Vercel Dashboard** - You paste environment variables into their secure UI
3. **Local `.env` files** - Only you have access (never committed to git)

**I (or any assistant) only tell you:**
- ✅ WHAT environment variables you need
- ✅ WHERE to put them
- ✅ HOW to configure them

**You do the actual credential management yourself.**

---

## 📋 What You Actually Do

### Step 1: Get Your Credentials (By Yourself)

**Anthropic API Key:**
```bash
1. Visit https://console.anthropic.com
2. Sign up / Log in
3. Click "API Keys" → "Create Key"
4. Copy the key (starts with sk-ant-...)
5. Save it somewhere SECURE (password manager recommended)
```

**Supabase Database:**
```bash
1. Visit https://supabase.com/dashboard
2. Create new project
3. Run backend/database_schema.sql in SQL Editor
4. Settings → Database → Copy "Connection string"
5. Replace [YOUR-PASSWORD] with your actual password
6. Save it somewhere SECURE
```

---

### Step 2: Configure Railway (You Do This)

**In Railway Dashboard (not shared with anyone):**

1. Go to https://railway.app
2. New Project → Deploy from GitHub → Select Ploit
3. Click your service → "Variables" tab
4. Click "Add Variable"
5. **You manually enter these** (Railway dashboard is secure):

```
DATABASE_URL = <paste your Supabase connection string>
ANTHROPIC_API_KEY = <paste your Anthropic key>
ALLOWED_ORIGINS = *
ENVIRONMENT = production
```

6. Railway auto-deploys
7. Copy your Railway URL (e.g., https://xxx.railway.app)

---

### Step 3: Configure Vercel (You Do This)

**In Vercel Dashboard (not shared with anyone):**

1. Go to https://vercel.com
2. Import Ploit repository
3. Root Directory: `frontend`
4. Settings → Environment Variables
5. **You manually enter**:

```
VITE_API_URL = <paste your Railway URL>
```

6. Deploy
7. Copy your Vercel URL (e.g., https://xxx.vercel.app)

---

### Step 4: Update CORS (You Do This)

**Back in Railway Dashboard:**

1. Go to your Railway project
2. Variables tab
3. Edit `ALLOWED_ORIGINS`
4. Change from `*` to your actual Vercel URL
5. Save (auto-redeploys)

---

## 🔐 Local Development (Optional)

If you want to run locally first:

**Backend:**
```bash
cd backend
cp .env.example .env
# Edit .env with your values (YOU do this, not shared)
uvicorn backend.main:app --reload
```

**Frontend:**
```bash
cd frontend
cp .env.example .env
# Edit .env with your values (YOU do this, not shared)
npm run dev
```

---

## ✅ Verification (Without Sharing Credentials)

After deployment, you can share:
- ✅ Your public URLs (https://your-app.vercel.app)
- ✅ Error messages (if you encounter issues)
- ✅ Logs (with credentials redacted)

I can help troubleshoot by:
- ✅ Checking if URLs are accessible
- ✅ Looking at configuration structure
- ✅ Debugging error messages
- ✅ Verifying health check responses

**Without ever seeing your actual credentials.**

---

## 🎯 What I Actually Need From You

**To help you troubleshoot (if needed):**

1. ✅ Your public URLs:
   ```
   Frontend: https://your-app.vercel.app
   Backend: https://your-backend.railway.app
   ```

2. ✅ Error messages (with credentials removed):
   ```
   "Failed to connect to database"  ← OK to share
   DATABASE_URL=postgres://...      ← NOT OK to share
   ```

3. ✅ Confirmation of steps completed:
   ```
   "I've added DATABASE_URL to Railway" ← OK
   "My DATABASE_URL is postgres://..." ← NOT OK
   ```

---

## 🚨 If You Accidentally Expose Credentials

**If you accidentally share an API key or password:**

1. **Immediately rotate it** (generate a new one)
   - Anthropic: Delete old key, create new one
   - Supabase: Reset database password
2. Update your environment variables with new values
3. Redeploy

---

## 🎓 Best Practices

1. **Use a password manager** (1Password, Bitwarden, etc.)
2. **Never commit `.env` files** (already in .gitignore)
3. **Use different credentials for dev/prod**
4. **Rotate keys periodically**
5. **Use platform-specific secrets management**:
   - Railway: Built-in encrypted variables
   - Vercel: Built-in encrypted variables
   - Supabase: Built-in connection pooling

---

## 📖 Summary

**You keep all credentials secure.**
**I guide you on configuration.**
**Platforms handle encryption/security.**

This is the correct and secure way to deploy! 🔒
