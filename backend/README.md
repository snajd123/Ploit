# Poker Analysis App - Backend

FastAPI backend for the Poker Analysis application.

## Structure

```
backend/
├── parser/              # PokerStars hand history parser
├── services/            # Business logic (database, stats, Claude)
├── models/              # SQLAlchemy ORM models
├── tests/               # Test files
├── main.py             # FastAPI application entry point
├── config.py           # Configuration management
├── database.py         # Database connection and session handling
├── database_schema.sql # PostgreSQL schema (run in Supabase)
└── requirements.txt    # Python dependencies
```

## Database Setup (Supabase)

1. **Create Supabase Project**:
   - Go to [supabase.com](https://supabase.com)
   - Create new project
   - Note your database password

2. **Run Schema**:
   - Open Supabase SQL Editor
   - Copy contents of `database_schema.sql`
   - Execute the SQL
   - Verify all 5 tables created

3. **Get Connection String**:
   - Go to Project Settings → Database
   - Copy "Connection string" → "URI"
   - Format: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`
   - Add to `.env` as `DATABASE_URL`

## Environment Variables

Create a `.env` file based on `.env.example`:

```env
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
ANTHROPIC_API_KEY=sk-ant-xxxxx
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify database connection
python -c "from backend.database import check_db_connection; check_db_connection()"
```

## Running the Application

```bash
# Development mode
uvicorn backend.main:app --reload --port 8000

# Production mode
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

Once implemented, the API will provide:

- `POST /api/upload` - Upload hand history files
- `GET /api/players` - List all players
- `GET /api/players/{player_name}` - Get player profile
- `POST /api/query/claude` - Query Claude AI
- `GET /api/database/stats` - Database overview
- `GET /api/health` - Health check

API documentation available at: `http://localhost:8000/docs`

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html
```

## Development Status

- [x] Database models created
- [x] Configuration management
- [x] Database connection setup
- [ ] Hand history parser
- [ ] Database service layer
- [ ] Statistical calculator
- [ ] FastAPI endpoints
- [ ] Claude integration
