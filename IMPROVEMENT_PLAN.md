# Ploit Improvement Plan

## Overview

This plan addresses two categories of improvements:
1. **UX/Usability** — Making the app easier to use for its core purposes
2. **Poker Analysis Depth** — Improving the quality of strategic insights

**Core User Goals:**
- Find strategies against opponents (pre-game prep)
- Analyze own game vs GTO and exploit strategies (post-session review)

---

## Phase 1: User Journey Fixes (Week 1-2)

*Goal: Users can complete core workflows without getting lost*

### 1.1 Post-Upload Flow
**Problem:** After uploading hands, users see success metrics but no guidance.

**Tasks:**
- [ ] Add "What's Next?" card to upload success state with 3 CTAs:
  - "Browse Players" → /players
  - "View Sessions" → /sessions
  - "Generate Strategy" → /strategy
- [ ] Auto-trigger session detection after successful upload
- [ ] Show toast notification: "X sessions detected from your upload"

**Files:** `frontend/src/pages/Upload.tsx`

### 1.2 Strategy Bridge
**Problem:** Can't generate strategy from player profile; must manually type names.

**Tasks:**
- [ ] Add "Generate Strategy" button to PlayerProfile page header
- [ ] Add "Generate Strategy" context menu to Players list rows
- [ ] Add "Generate Strategy for Opponents" button to SessionDetail page
- [ ] Pre-populate strategy form when navigating from these locations

**Files:**
- `frontend/src/pages/PlayerProfile.tsx`
- `frontend/src/pages/PlayersList.tsx`
- `frontend/src/pages/SessionDetail.tsx`
- `frontend/src/pages/PreGameStrategy.tsx`

### 1.3 GTO Analysis Auto-Select
**Problem:** GTO Analysis requires manually selecting yourself to analyze.

**Tasks:**
- [ ] Store "hero name" in localStorage (already done in Strategy page)
- [ ] Auto-select hero on GTO Analysis page load
- [ ] Add "Analyzing: {heroName}" header instead of dropdown
- [ ] Keep dropdown as "Switch Player" option for analyzing opponents

**Files:** `frontend/src/pages/GTOAnalysis.tsx`

### 1.4 Session Detection Visibility
**Problem:** Users don't know sessions exist or how to create them.

**Tasks:**
- [ ] Rename button: "Detect New Sessions" → "Create Sessions from Hands"
- [ ] Add helper text explaining what sessions are
- [ ] Show "Last detected: X ago" timestamp
- [ ] Consider auto-detect on page load if no sessions exist

**Files:** `frontend/src/pages/Sessions.tsx`

---

## Phase 2: Onboarding & Navigation (Week 2-3)

*Goal: First-time users understand the app immediately*

### 2.1 Onboarding Modal
**Problem:** New users don't know where to start.

**Tasks:**
- [ ] Create OnboardingModal component with 3 steps:
  1. "Upload your hand histories from PokerStars"
  2. "Review sessions and player statistics"
  3. "Generate strategies against your opponents"
- [ ] Show modal on first visit (check localStorage flag)
- [ ] Add "Show Tutorial" button to Dashboard for returning users

**Files:**
- `frontend/src/components/OnboardingModal.tsx` (new)
- `frontend/src/pages/Dashboard.tsx`

### 2.2 Navigation Reorganization
**Problem:** 10 nav items with unclear purposes.

**Tasks:**
- [ ] Group navigation into sections:
  ```
  PREPARE
  - Strategy (Pre-Game)
  - GTO Browser (Ranges)

  REVIEW
  - Sessions
  - GTO Analysis
  - Claude AI

  RESEARCH
  - Players
  - Glossary

  DATA
  - Upload
  - Dashboard
  ```
- [ ] Add section headers or visual dividers in nav
- [ ] Add tooltips explaining each section's purpose

**Files:** `frontend/src/components/Layout.tsx`

### 2.3 Dashboard Improvements
**Problem:** Dashboard shows stats but no recommended actions.

**Tasks:**
- [ ] Add "Recommended Next Steps" section based on user state:
  - No hands? → "Upload your first hand history"
  - Hands but no sessions? → "Detect sessions from your data"
  - Sessions exist? → "Generate strategy for your next session"
- [ ] Add "Recent Activity" section (last upload, last session analyzed)
- [ ] Make quick action cards more prominent

**Files:** `frontend/src/pages/Dashboard.tsx`

---

## Phase 3: Claude AI Enhancement (Week 3-4)

*Goal: Users know what to ask and get actionable answers*

### 3.1 Schema Documentation
**Problem:** Users don't know what data Claude can access.

**Tasks:**
- [ ] Add collapsible "Available Data" panel to Claude page showing:
  - Tables: player_stats, raw_hands, hand_actions, gto_scenarios, etc.
  - Key columns with descriptions
  - Example queries for each table
- [ ] Add "Query Examples" button that shows categorized examples:
  - Player Analysis: "Who has the highest VPIP?"
  - GTO Comparison: "How does player X compare to GTO opening ranges?"
  - Exploit Finding: "Which players fold too much to 3-bets?"

**Files:**
- `frontend/src/pages/ClaudeChat.tsx`
- `frontend/src/components/ClaudeSchemaPanel.tsx` (new)

### 3.2 Contextual Claude Integration
**Problem:** Claude is isolated from other pages.

**Tasks:**
- [ ] Add "Ask Claude About This Player" on PlayerProfile (already partially done)
- [ ] Add "Ask Claude About This Session" on SessionDetail
- [ ] Pre-populate Claude with context when navigating from these pages
- [ ] Add quick-ask modal that can be triggered from any page

**Files:**
- `frontend/src/pages/PlayerProfile.tsx`
- `frontend/src/pages/SessionDetail.tsx`
- `frontend/src/components/QuickAskModal.tsx` (new)

### 3.3 Claude Tools Enhancement (Backend)
**Problem:** Claude can query data but can't calculate or recommend.

**Tasks:**
- [ ] Add `calculate_mdf` tool (minimum defense frequency)
- [ ] Add `calculate_ev` tool (expected value of exploit)
- [ ] Add `suggest_exploits` tool (prioritized exploit list)
- [ ] Add `compare_to_gto` tool (player vs GTO for specific scenario)

**Files:** `backend/services/claude_service.py`

---

## Phase 4: GTO Browser Integration (Week 4-5)

*Goal: Personal frequency overlay on GTO ranges*

### 4.1 Personal Comparison View
**Problem:** GTO Browser shows theory but not how you compare.

**Tasks:**
- [ ] Add "Compare to My Play" toggle to GTO Browser
- [ ] Fetch user's actual frequencies for selected scenario
- [ ] Overlay user frequency on range grid (color gradient)
- [ ] Show deviation summary: "You open 65% vs GTO 40% (+25%)"

**Files:**
- `frontend/src/pages/GTOBrowser.tsx`
- `frontend/src/components/RangeGridComparison.tsx` (new)
- `backend/api/gto_endpoints.py` (add comparison endpoint)

### 4.2 GTO Progress Tracking
**Problem:** No way to see if you're improving over time.

**Tasks:**
- [ ] Store GTO adherence snapshots when calculated
- [ ] Add "Progress Over Time" chart to GTO Analysis page
- [ ] Show trend: "Your opening adherence improved 12% this month"

**Files:**
- `backend/models/database_models.py` (add gto_adherence_history table)
- `frontend/src/pages/GTOAnalysis.tsx`

---

## Phase 5: Statistical Rigor (Week 5-6)

*Goal: Stats show confidence levels and actionable severity*

### 5.1 Confidence Intervals
**Problem:** All stats treated as equally reliable regardless of sample size.

**Tasks:**
- [ ] Implement Wilson score interval for all percentages
- [ ] Add confidence indicator to stat displays:
  - Green checkmark: 95% confidence (enough samples)
  - Yellow warning: Low confidence (need more hands)
  - Gray: Insufficient data
- [ ] Show sample size next to each stat

**Files:**
- `backend/services/stats_calculator.py`
- `frontend/src/components/StatCard.tsx`

### 5.2 MDF-Adjusted Fold Stats
**Problem:** Raw fold percentages don't show exploitability.

**Tasks:**
- [ ] Calculate MDF for standard bet sizes (33%, 50%, 75%, 100% pot)
- [ ] Show "Folds X% too much vs 75% pot bet" instead of raw %
- [ ] Add exploit EV: "Worth $X per 100 hands to bluff this player"

**Files:**
- `backend/services/stats_calculator.py`
- `backend/services/gto_service.py`

### 5.3 Leak Prioritization
**Problem:** Leaks shown but not prioritized by actual EV impact.

**Tasks:**
- [ ] Calculate EV impact of each leak in bb/100
- [ ] Rank leaks by EV impact, not just deviation percentage
- [ ] Add "Focus Areas" section: "Fix these 3 leaks to gain X bb/100"

**Files:**
- `backend/services/gto_service.py`
- `frontend/src/pages/GTOAnalysis.tsx`

---

## Phase 6: Player Profile Improvements (Week 6-7)

*Goal: Reduce information overload, increase actionability*

### 6.1 Tabbed Interface
**Problem:** 8+ screens of scrolling on player profile.

**Tasks:**
- [ ] Convert PlayerProfile sections to tabs:
  - Summary (key stats + player type + top exploits)
  - Preflop (VPIP, PFR, 3-bet, position stats)
  - Postflop (c-bet, fold to c-bet, check-raise)
  - Advanced (composite metrics, heatmaps)
- [ ] Add sticky header with player name, type, and quick stats

**Files:** `frontend/src/pages/PlayerProfile.tsx`

### 6.2 Actionable Recommendations
**Problem:** Stats shown but no specific actions recommended.

**Tasks:**
- [ ] Add "How to Exploit" section with specific recommendations:
  - "3-bet this player 15% more than normal from BTN"
  - "Never bluff river vs this player"
  - "Value bet thinner - they call too much"
- [ ] Link recommendations to specific hands where applicable

**Files:**
- `backend/services/exploit_service.py` (new)
- `frontend/src/components/ExploitRecommendations.tsx` (new)

---

## Phase 7: Hand History Viewer (Week 7-8)

*Goal: Review specific hands with GTO comparison*

### 7.1 Hand Timeline
**Problem:** Hand history shows cards/profit but not action sequence.

**Tasks:**
- [ ] Create HandTimeline component showing:
  - Each street (preflop, flop, turn, river)
  - Each action with player, action type, amount
  - Pot size progression
  - Board cards as they're dealt
- [ ] Add expand/collapse for each hand

**Files:**
- `frontend/src/components/HandTimeline.tsx` (new)
- `frontend/src/pages/SessionDetail.tsx`

### 7.2 Hand-Level GTO Comparison
**Problem:** Can't see GTO recommendation for specific hands.

**Tasks:**
- [ ] Add "GTO Says" overlay showing optimal action for each decision
- [ ] Highlight deviations: "You called, GTO folds 70%"
- [ ] Calculate EV loss for each deviation

**Files:**
- `backend/api/hand_analysis_endpoints.py` (new)
- `frontend/src/components/HandGTOComparison.tsx` (new)

---

## Phase 8: Advanced Poker Analysis (Week 8-10)

*Goal: Deeper strategic insights*

### 8.1 Multi-Street Patterns
**Problem:** No analysis of bet-bet-check vs check-bet-bet lines.

**Tasks:**
- [ ] Track action sequences across streets
- [ ] Identify patterns: "Gives up turn after c-betting 60%"
- [ ] Add "Multi-Street Tendencies" section to player profile

**Files:**
- `backend/services/pattern_analyzer.py` (new)
- `backend/models/database_models.py` (add pattern tracking)

### 8.2 Board Texture Adjustments
**Problem:** Same strategy recommended regardless of board texture.

**Tasks:**
- [ ] Expand board categorization to include:
  - Wet/dry boards
  - Monotone/two-tone/rainbow
  - Paired/unpaired
  - High/medium/low card boards
- [ ] Adjust c-bet recommendations by texture
- [ ] Show texture-specific stats in player profiles

**Files:**
- `backend/services/board_categorizer.py`
- `backend/services/gto_service.py`

### 8.3 Postflop GTO Scenarios
**Problem:** Only 5 flop boards in GTO database.

**Tasks:**
- [ ] Expand GTO scenarios to cover:
  - 50+ strategically distinct flop textures
  - Turn continuation scenarios
  - River completion scenarios
- [ ] Integrate with TexasSolver for custom solutions
- [ ] Add postflop adherence to GTO Analysis

**Files:**
- `backend/services/gto_service.py`
- `solver/` integration

---

## Implementation Priority

### Must Have (Weeks 1-3)
- Post-upload flow improvements
- Strategy bridge from player profiles
- GTO Analysis auto-select
- Onboarding modal
- Claude schema documentation

### Should Have (Weeks 4-6)
- Navigation reorganization
- GTO Browser personal comparison
- Confidence intervals
- Player profile tabs

### Nice to Have (Weeks 7-10)
- Hand timeline viewer
- Multi-street pattern analysis
- Expanded postflop GTO
- Historical progress tracking

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Clicks to generate strategy from upload | 5+ | 2 |
| Users who find session detection | ~30% | 90% |
| Users who discover Claude capabilities | ~20% | 70% |
| Time to first useful insight | 10+ min | 3 min |

---

## Technical Debt to Address

- [ ] Remove "AI Analysis Coming Soon" placeholder from SessionDetail
- [ ] Fix GTO Analysis dark theme inconsistency
- [ ] Clean up unused GTOBoardMatch component (already deleted)
- [ ] Add error boundaries to prevent white screens
- [ ] Add loading states to all data-fetching components

---

## Notes

- Each phase can be deployed independently
- Backend changes should include API tests
- Frontend changes should be responsive (mobile-friendly)
- All new features should include loading/error states
