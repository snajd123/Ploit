# Poker Analysis App

A cloud-based poker analysis platform that parses PokerStars hand histories, calculates advanced statistical models, and integrates Claude AI for natural language strategic analysis.

## Overview

This application is a comprehensive poker research and analysis tool that:
- Parses PokerStars `.txt` hand history files
- Stores hand data in PostgreSQL with 5 normalized tables
- Calculates 12 advanced composite statistical models for exploitative strategy
- Integrates Claude AI with direct database access for natural language queries
- Provides a React web interface for visualization and analysis

**Key Principle**: This is a research platform, not a real-time tool. Users can ask Claude ANY question about their poker database and receive sophisticated statistical analysis and strategic recommendations.

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy
- **AI Integration**: Anthropic Claude API

### Frontend
- **Framework**: React 18+ with Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Hosting**: Vercel (planned)

## Project Structure

```
poker-analysis-app/
├── backend/
│   ├── parser/              # PokerStars hand history parser
│   ├── services/            # Business logic and statistics
│   ├── models/              # SQLAlchemy database models
│   ├── tests/               # Unit and integration tests
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration management
│   ├── database.py         # Database connection
│   └── requirements.txt    # Python dependencies
├── frontend/
│   └── src/
│       ├── components/     # React components
│       ├── pages/          # Page components
│       └── services/       # API client
├── docs/                   # Documentation
└── README.md
```

## Database Schema

The application uses 5 PostgreSQL tables:

1. **raw_hands**: Complete hand history text
2. **hand_actions**: Every action in every hand
3. **player_hand_summary**: Boolean flags for each player/hand
4. **player_stats**: Pre-calculated traditional and composite statistics
5. **upload_sessions**: Upload tracking and audit trail

## 12 Composite Statistical Models

1. **Exploitability Index (EI)**: Overall exploitability measure (0-100)
2. **Pressure Vulnerability Score (PVS)**: Fold frequency under pressure
3. **Aggression Consistency Ratio (ACR)**: Give-up tendency across streets
4. **Positional Awareness Index (PAI)**: Position-specific play quality
5. **Blind Defense Efficiency (BDE)**: Quality of blind defense
6. **Value-Bluff Imbalance Ratio (VBIR)**: Showdown value vs bluff balance
7. **Range Polarization Factor (RPF)**: Bet sizing and range construction
8. **Street-by-Street Fold Gradient (SFG)**: Folding pattern changes
9. **Delayed Aggression Coefficient (DAC)**: Check-raise and trap frequency
10. **Quick Exploit Matrix (QEM)**: Player type classification
11. **Multi-Street Persistence Score (MPS)**: Commitment across streets
12. **Optimal Stake Threshold**: Skill vs stake mismatch detection

See [POKER_APP_PROJECT_PLAN.md](POKER_APP_PROJECT_PLAN.md) for detailed formulas and interpretations.

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL database (Supabase account)
- Anthropic API key

### Backend Setup

1. **Configure environment variables**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your actual values
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database**:
   - Create a Supabase project
   - Run the SQL from `backend/database_schema.sql` in Supabase SQL Editor
   - Update `DATABASE_URL` in `.env`

4. **Run the backend**:
   ```bash
   uvicorn backend.main:app --reload
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Update VITE_API_URL if needed
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

## Development Phases

- [x] Phase 1: Database Setup
- [ ] Phase 2: Hand History Parser
- [ ] Phase 3: Database Service
- [ ] Phase 4: Statistical Calculator
- [ ] Phase 5: FastAPI Backend
- [ ] Phase 6: Claude Integration
- [ ] Phase 7: Frontend Development
- [ ] Phase 8: Integration & Testing
- [ ] Phase 9: Deployment
- [ ] Phase 10: Documentation

## Documentation

- [Project Plan](POKER_APP_PROJECT_PLAN.md) - Complete technical specification
- [Development Rules](RULES.md) - Development guidelines and workflow
- Database Schema - See `backend/database_schema.sql`

## License

Proprietary - All rights reserved

## Support

For questions or issues, refer to the project documentation or contact the development team.
