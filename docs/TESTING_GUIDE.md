# Testing Guide - Poker Analysis Platform

Complete guide for testing the poker analysis platform across all components.

## Overview

This platform consists of three major components that must work together:
1. **Backend API** (FastAPI + PostgreSQL)
2. **Frontend** (React + TypeScript)
3. **Claude AI Integration** (Anthropic API)

## Prerequisites

Before testing, ensure you have:
- Python 3.11+ installed
- Node.js 18+ and npm installed
- PostgreSQL database (Supabase) configured
- Anthropic API key
- Sample PokerStars hand history files

## Backend Testing

### Setup Test Environment

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-cov httpx
```

### Unit Tests

Run parser unit tests:
```bash
pytest backend/tests/test_parser.py -v
```

Expected output:
- All parser tests should pass
- 3 sample hands should parse successfully
- 60+ boolean flags should be calculated correctly

### Integration Tests

Run full integration tests:
```bash
pytest backend/tests/test_integration.py -v
```

Tests cover:
- Health check endpoint
- File upload workflow
- Player statistics calculation
- Database queries
- Claude AI integration
- Error handling

### Coverage Report

Generate test coverage:
```bash
pytest --cov=backend --cov-report=html
```

View report: `open htmlcov/index.html`

Target coverage: 80%+

## Frontend Testing

### Setup

```bash
cd frontend
npm install
```

### Development Server

Start frontend:
```bash
npm run dev
```

Runs on: http://localhost:3000

### Manual Testing Checklist

#### Dashboard Page
- [ ] Database stats display correctly
- [ ] Health status shows "connected"
- [ ] Quick action cards are clickable
- [ ] Navigation links work
- [ ] Responsive on mobile/tablet/desktop

#### Upload Page
- [ ] Drag-and-drop area is visible
- [ ] File selection dialog works
- [ ] Only .txt files are accepted
- [ ] Upload progress bar shows during upload
- [ ] Success message displays with stats
- [ ] Error handling for invalid files
- [ ] Can upload multiple files sequentially

#### Players List Page
- [ ] Table displays all players
- [ ] Minimum hands filter works
- [ ] Sort dropdown changes order
- [ ] Player type badges display correctly
- [ ] Exploitability bars render properly
- [ ] Clicking player navigates to profile
- [ ] Empty state shows when no players

#### Player Profile Page
- [ ] Player name and type display
- [ ] All traditional stats render
- [ ] Radar chart visualizes composite metrics
- [ ] Advanced metrics cards show data
- [ ] "Ask Claude" button works
- [ ] Back button returns to player list

#### Claude Chat Page
- [ ] Example queries display
- [ ] Input field accepts text
- [ ] Send button submits query
- [ ] Loading state shows while processing
- [ ] Claude response displays with markdown
- [ ] Conversation history maintained
- [ ] Error messages show on failure
- [ ] Token usage displayed

### Build Test

Test production build:
```bash
npm run build
npm run preview
```

Verify:
- Build completes without errors
- Preview serves correctly
- All routes work
- Assets load properly

## End-to-End Testing Scenarios

### Scenario 1: New User Workflow

1. **Start with empty database**
   - Visit dashboard
   - Verify all stats show 0
   - Database status shows "connected"

2. **Upload first hand history**
   - Navigate to Upload page
   - Drop a .txt file
   - Click "Upload & Parse"
   - Verify success message
   - Check hands parsed count > 0

3. **View players**
   - Navigate to Players page
   - Verify table shows players
   - Check player type badges display
   - Click a player with 100+ hands

4. **Analyze player**
   - View player profile
   - Verify all stats display
   - Check radar chart renders
   - Click "Ask Claude"

5. **Query Claude**
   - Enter: "Analyze this player and tell me how to exploit them"
   - Verify Claude responds
   - Check response includes strategic recommendations
   - Ask follow-up question

### Scenario 2: Multiple File Upload

1. **Upload multiple files**
   - Upload file A
   - Upload file B (same players)
   - Upload file C (different players)

2. **Verify aggregation**
   - Check player list grows
   - Verify stats update for existing players
   - Total hands increases correctly

### Scenario 3: Filtering and Analysis

1. **Filter players**
   - Set min hands to 500
   - Sort by exploitability index (descending)
   - View most exploitable player

2. **Deep dive analysis**
   - View player profile
   - Note composite metrics
   - Ask Claude: "Find similar players to [name]"
   - Ask Claude: "What's the best strategy against [player type]?"

### Scenario 4: Error Handling

1. **Invalid file upload**
   - Try uploading .pdf file
   - Verify error message displays

2. **Backend offline**
   - Stop backend server
   - Try uploading file
   - Verify graceful error handling
   - Try querying Claude
   - Check error message

3. **Non-existent player**
   - Navigate to /players/FakePlayer123
   - Verify 404 handling

## Claude AI Integration Testing

### Test Database Queries

Ask Claude these questions and verify correct responses:

1. **Basic query:**
   ```
   "Who are the most exploitable players?"
   ```
   Expected: List of players with high EI, sorted by exploitability

2. **Filtered query:**
   ```
   "Show me all TAGs with at least 500 hands"
   ```
   Expected: Players where player_type='TAG' and total_hands >= 500

3. **Complex analysis:**
   ```
   "Which players fold too much to 3-bets from the button?"
   ```
   Expected: Analysis of fold_to_three_bet_pct by position

4. **Strategic recommendations:**
   ```
   "How should I play against calling stations?"
   ```
   Expected: Strategic advice about value betting, avoiding bluffs

### Verify Tool Usage

In Claude responses, check for:
- Tool calls are logged in browser console
- SQL queries are executed
- Results are correctly interpreted
- Strategic analysis is relevant

## Performance Testing

### Backend Performance

Test with large hand history file (10,000+ hands):
- Upload time should be < 60 seconds
- Player stats calculation should complete
- No memory leaks
- Database queries remain fast

### Frontend Performance

- Page load time < 2 seconds
- Smooth scrolling in players table
- No lag in Claude chat interface
- Radar charts render quickly

## Database Integrity Tests

### Verify Data Consistency

1. **Check hand counts:**
   ```sql
   SELECT COUNT(*) FROM raw_hands;
   SELECT SUM(total_hands) FROM player_stats;
   ```
   Should match (roughly, accounting for multi-way pots)

2. **Verify player stats:**
   ```sql
   SELECT player_name, total_hands, vpip_pct, pfr_pct
   FROM player_stats
   WHERE total_hands > 100;
   ```
   All percentages should be between 0-100

3. **Check composite metrics:**
   ```sql
   SELECT player_name, exploitability_index, player_type
   FROM player_stats
   WHERE exploitability_index IS NOT NULL;
   ```
   EI should be 0-100, player_type should be valid

## Security Testing

### API Security

- [ ] CORS is configured correctly
- [ ] File upload validates file types
- [ ] SQL injection prevention (parameterized queries)
- [ ] Claude only executes SELECT queries
- [ ] No sensitive data in error messages

### Environment Variables

- [ ] API keys not in code
- [ ] .env file in .gitignore
- [ ] .env.example provided

## Browser Compatibility

Test frontend in:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Mobile Chrome (Android)

## Accessibility Testing

- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Color contrast meets WCAG standards
- [ ] Form labels are present
- [ ] Error messages are clear

## Regression Testing

After any code changes, run:
1. Backend integration tests
2. Frontend build
3. End-to-end scenario 1
4. Claude AI test query

## Known Issues and Limitations

### Sample Size Requirements

Composite metrics require minimum data:
- VPIP/PFR: 50+ hands
- 3-bet stats: 100+ hands
- C-bet stats: 50+ hands
- Exploitability Index: 100+ hands

Players with insufficient data show "N/A" or null values.

### File Format Compatibility

- Only PokerStars .txt format supported
- Other poker sites not supported
- Hand history must be complete (not partial)

### Claude AI Limitations

- Requires valid Anthropic API key
- Rate limits apply
- Response time varies (2-10 seconds)
- Token costs apply

## Troubleshooting

### Backend won't start

1. Check Python version: `python --version` (need 3.11+)
2. Check dependencies: `pip list`
3. Verify DATABASE_URL in .env
4. Test database connection: `psql $DATABASE_URL`

### Frontend won't start

1. Check Node version: `node --version` (need 18+)
2. Clear node_modules: `rm -rf node_modules && npm install`
3. Check for port conflicts (3000)

### Upload fails

1. Check file is valid PokerStars .txt
2. Verify backend is running
3. Check network tab for error details
4. Review backend logs

### Claude not responding

1. Verify ANTHROPIC_API_KEY in .env
2. Check API key is valid
3. Review Claude service logs
4. Test with simple query first

## Test Data

### Sample Queries for Claude

Use these to test Claude functionality:
- "Who are the 5 most exploitable players?"
- "Show me all players with VPIP over 40%"
- "Which TAGs have the best win rate?"
- "Find players who fold too much to continuation bets"
- "Analyze PlayerName and recommend a strategy"

### Sample Hand Histories

Located in: `backend/tests/data/sample_hands.txt`

Contains:
- 3 complete hands
- Various player actions
- Different board textures
- Multiple player types

## Continuous Integration

Recommended CI/CD pipeline:
1. Run backend tests (pytest)
2. Run frontend build (npm run build)
3. Check code coverage (80%+)
4. Lint code (eslint, flake8)
5. Deploy if all pass

## Success Criteria

Platform is ready for deployment when:
- [x] All backend tests pass
- [x] Frontend builds without errors
- [x] End-to-end scenario completes successfully
- [x] Claude AI responds to queries
- [x] Database integrity verified
- [x] No critical security issues
- [x] Cross-browser compatibility confirmed
- [x] Documentation complete

## Next Steps

After testing passes:
- Phase 9: Deployment
- Phase 10: Final Documentation
