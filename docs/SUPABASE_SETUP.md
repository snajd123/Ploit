# Supabase Database Setup Guide

Complete guide to setting up the PostgreSQL database for the Poker Analysis App using Supabase.

## Why Supabase?

- Free tier with generous limits
- Cloud-hosted PostgreSQL
- Built-in SQL editor
- Automatic backups
- Good developer experience
- No credit card required for free tier

## Step-by-Step Setup

### 1. Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub, Google, or email
4. Verify your email if required

### 2. Create New Project

1. Click "New Project"
2. Fill in project details:
   - **Name**: `poker-analysis-app` (or your choice)
   - **Database Password**: Generate a strong password and **save it securely**
   - **Region**: Choose closest to your location
   - **Pricing Plan**: Free (sufficient for development)
3. Click "Create new project"
4. Wait 2-3 minutes for database provisioning

### 3. Run Database Schema

1. In your Supabase project dashboard, navigate to:
   - **SQL Editor** (left sidebar)
   - Click "New Query"

2. Copy the entire contents of `backend/database_schema.sql` from this project

3. Paste into the SQL Editor

4. Click "Run" (or press Ctrl/Cmd + Enter)

5. Verify success:
   - You should see a success message
   - The verification query at the end will show 5 tables with their column counts

**Expected Output**:
```
table_name            | column_count
----------------------|-------------
hand_actions          | 14
player_hand_summary   | 61
player_stats          | 64
raw_hands             | 7
upload_sessions       | 10
```

### 4. Verify Tables Created

1. Navigate to **Table Editor** in the left sidebar
2. You should see all 5 tables:
   - `raw_hands`
   - `hand_actions`
   - `player_hand_summary`
   - `player_stats`
   - `upload_sessions`

3. Click on each table to verify schema:
   - Check columns match the schema
   - Verify indexes created (go to table → Indexes tab)

### 5. Get Database Connection String

1. Navigate to **Project Settings** (gear icon in sidebar)
2. Click **Database** in the settings menu
3. Scroll to "Connection string"
4. Select **URI** tab
5. Copy the connection string

**Format**:
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxx.supabase.co:5432/postgres
```

6. **Important**: Replace `[YOUR-PASSWORD]` with the actual password you created in Step 2

**Example**:
```
postgresql://postgres:MySecurePass123!@db.abc123def456.supabase.co:5432/postgres
```

### 6. Configure Backend

1. In your project, navigate to `backend/` directory

2. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and update `DATABASE_URL`:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR-PASSWORD@db.xxxxx.supabase.co:5432/postgres
   ```

4. Save the file

### 7. Test Connection

You can test the database connection using Python:

```python
from sqlalchemy import create_engine

# Replace with your actual connection string
DATABASE_URL = "postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) FROM raw_hands")
        print("✅ Connection successful! Current hands:", result.fetchone()[0])
except Exception as e:
    print("❌ Connection failed:", str(e))
```

## Security Best Practices

### 1. Protect Your Credentials

- ✅ **DO**: Store connection string in `.env` file (gitignored)
- ✅ **DO**: Use environment variables in production
- ❌ **DON'T**: Commit `.env` to Git
- ❌ **DON'T**: Share your database password
- ❌ **DON'T**: Hardcode connection strings in code

### 2. Database Access

Supabase provides multiple connection methods:

1. **Direct PostgreSQL connection** (what we use):
   - Full SQL access
   - Use with SQLAlchemy
   - Best for backend applications

2. **Supabase Client Libraries**:
   - JavaScript/TypeScript client
   - REST API
   - Good for frontend if needed

3. **PostgREST API**:
   - Auto-generated REST API
   - Not used in this project

### 3. Row Level Security (RLS)

For this application:
- RLS is **disabled** (backend has full access)
- Backend API handles all authorization
- Frontend cannot directly access database

## Database Management

### Viewing Data

1. **Table Editor**:
   - Navigate to Table Editor in Supabase
   - Select table to view
   - Browse, filter, and edit data

2. **SQL Editor**:
   - Write custom queries
   - Export results as CSV
   - Save frequently used queries

### Backups

Supabase automatically backs up your database:
- **Free tier**: Daily backups, 7-day retention
- **Pro tier**: Point-in-time recovery

To manually backup:
```sql
-- In SQL Editor, export specific tables
COPY (SELECT * FROM player_stats) TO STDOUT WITH CSV HEADER;
```

### Monitoring

Monitor database health:
1. **Database** → **Usage** (in Settings)
2. Track:
   - Database size
   - Number of tables
   - Active connections
   - Query performance

## Troubleshooting

### Connection Refused

**Problem**: Can't connect to database

**Solutions**:
1. Verify password is correct
2. Check connection string format
3. Ensure database is not paused (free tier auto-pauses after inactivity)
4. Check firewall/network settings

### Table Creation Failed

**Problem**: SQL execution errors

**Solutions**:
1. Ensure project is fully provisioned (wait a few minutes)
2. Check for syntax errors in SQL
3. Verify you're in SQL Editor, not Table Editor
4. Try running each CREATE TABLE statement individually

### Password Issues

**Problem**: Forgot database password

**Solutions**:
1. Go to Project Settings → Database
2. Click "Reset database password"
3. Update `.env` with new password

### Performance Issues

**Problem**: Slow queries

**Solutions**:
1. Verify indexes are created (check Indexes tab)
2. Use `EXPLAIN ANALYZE` to debug queries
3. Upgrade to paid tier if hitting free tier limits

## Free Tier Limits

Supabase free tier includes:
- ✅ 500 MB database space (plenty for thousands of hands)
- ✅ Unlimited API requests
- ✅ 2 GB bandwidth
- ✅ 50,000 monthly active users
- ⚠️ Pauses after 1 week of inactivity (auto-resumes on first request)

For production, consider Pro tier:
- 8 GB database space
- No pausing
- Point-in-time recovery
- Better performance

## Next Steps

After database setup:
1. ✅ Verify all 5 tables exist
2. ✅ Connection string added to `.env`
3. ✅ Test connection successful
4. → Proceed to Phase 2: Hand History Parser

## Useful Supabase SQL Queries

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Count rows in all tables
SELECT
    'raw_hands' as table_name,
    COUNT(*) as row_count
FROM raw_hands
UNION ALL
SELECT 'hand_actions', COUNT(*) FROM hand_actions
UNION ALL
SELECT 'player_hand_summary', COUNT(*) FROM player_hand_summary
UNION ALL
SELECT 'player_stats', COUNT(*) FROM player_stats
UNION ALL
SELECT 'upload_sessions', COUNT(*) FROM upload_sessions;

-- View all indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

## Support

- Supabase Documentation: https://supabase.com/docs
- Supabase Discord: https://discord.supabase.com
- PostgreSQL Documentation: https://www.postgresql.org/docs/
