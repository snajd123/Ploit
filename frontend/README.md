# Poker Analysis Frontend

React + TypeScript frontend for the Poker Analysis Platform.

## Overview

Modern, responsive web interface for uploading hand histories, browsing player statistics, and querying Claude AI for strategic insights.

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **React Router** - Client-side routing
- **TanStack Query (React Query)** - Data fetching and caching
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **Lucide React** - Icon library
- **React Markdown** - Markdown rendering for Claude responses

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Layout.tsx       # Main layout with navigation
│   │   ├── StatCard.tsx     # Statistics card component
│   │   ├── PlayerBadge.tsx  # Player type badge
│   │   └── MetricChart.tsx  # Radar chart for composite metrics
│   ├── pages/               # Page components
│   │   ├── Dashboard.tsx    # Database overview
│   │   ├── Upload.tsx       # File upload with drag-and-drop
│   │   ├── PlayersList.tsx  # Player browsing with filters
│   │   ├── PlayerProfile.tsx# Detailed player stats and charts
│   │   └── ClaudeChat.tsx   # Claude AI chat interface
│   ├── services/            # API and utilities
│   │   └── api.ts           # API client service
│   ├── types.ts             # TypeScript type definitions
│   ├── App.tsx              # Main app with routing
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles (Tailwind)
├── index.html               # HTML template
├── package.json             # Dependencies
├── tsconfig.json            # TypeScript configuration
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind configuration
└── .env.example             # Environment variables template
```

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm

### Installation

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env if needed (default: http://localhost:8000)
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```

   The app will be available at http://localhost:3000

4. **Build for production:**
   ```bash
   npm run build
   ```

   Output will be in the `dist/` directory.

## Pages

### 1. Dashboard (`/dashboard`)

**Overview page with:**
- Database statistics (total hands, players, date range)
- System health status
- Quick action cards
- Platform information

**Features:**
- Real-time database health monitoring
- Responsive stats grid
- Navigation to other sections

### 2. Upload (`/upload`)

**Hand history file upload with:**
- Drag-and-drop interface
- File validation (.txt only)
- Upload progress tracking
- Detailed upload results

**Features:**
- Validates file type before upload
- Shows progress bar during upload
- Displays parsing results (hands parsed, failed, players updated)
- Helpful instructions for users

### 3. Players List (`/players`)

**Browse all players with:**
- Filterable table (minimum hands, sort by various stats)
- Player type badges
- Key statistics (VPIP%, PFR%, EI)
- Visual exploitability indicators

**Features:**
- Dynamic filtering by minimum hands
- Sort by total hands, exploitability, VPIP%, PFR%
- Click any player to view full profile
- Responsive table layout

### 4. Player Profile (`/players/:playerName`)

**Detailed player analysis with:**
- Player type classification badge
- Exploitability index with visual indicator
- Traditional statistics grid (VPIP%, PFR%, 3-bet%, etc.)
- Composite metrics radar chart
- Advanced metrics cards
- "Ask Claude" button for AI analysis

**Features:**
- Comprehensive stats visualization
- Interactive radar chart for composite metrics
- Direct link to Claude analysis for specific player
- Back navigation to players list

### 5. Claude Chat (`/claude`)

**AI-powered analysis interface with:**
- Natural language query input
- Conversational chat interface
- Markdown-formatted responses
- Example queries for new users
- Conversation history
- Token usage tracking

**Features:**
- Pre-populated query from player profile page
- Conversation context maintained
- Markdown rendering for formatted responses
- Loading states and error handling
- Example queries to get started

## Components

### Layout

Main application layout with:
- Header with branding
- Navigation menu
- Content area (React Router Outlet)
- Footer

### StatCard

Reusable statistics card component:
- Title, value, and subtitle
- Optional icon
- Color variants (blue, green, red, yellow, gray)

### PlayerBadge

Player type classification badge:
- Color-coded by player type
- Hover tooltip with description
- Size variants (sm, md, lg)
- Player types: NIT, TAG, LAG, CALLING_STATION, MANIAC, FISH

### MetricChart

Radar chart for composite metrics:
- Uses Recharts library
- Displays up to 6 metrics on radar plot
- Responsive design
- Interactive tooltips

## API Client Service

Located in `src/services/api.ts`, provides methods for:

- `health()` - Check API health
- `uploadHandHistory(file, onProgress)` - Upload file with progress tracking
- `getPlayers(params)` - Get filtered player list
- `getPlayerProfile(playerName)` - Get complete player stats
- `getDatabaseStats()` - Get database overview
- `queryClaude(request)` - Query Claude AI
- `getDatabaseSchema()` - Get database schema info

**Features:**
- Axios-based HTTP client
- TypeScript types for all requests/responses
- Progress tracking for file uploads
- Centralized error handling

## Styling

**Tailwind CSS** with custom configuration:

- Custom poker-themed colors
- Utility classes for common patterns
- Responsive design utilities
- Custom components classes (btn-primary, btn-secondary, card, input-field)

**Theme:**
- Primary color: Blue (#3B82F6)
- Success: Green
- Warning: Yellow
- Error: Red
- Background: Gray-50

## State Management

**TanStack Query (React Query)** for:
- API data fetching
- Caching and automatic refetching
- Loading and error states
- Optimistic updates

**Configuration:**
- 30-second stale time
- No refetch on window focus
- 1 retry on failure

## TypeScript

Full TypeScript coverage with:
- Interface definitions for all API responses
- Type-safe props for all components
- Strict mode enabled
- No `any` types (except where necessary)

**Key types:**
- `PlayerStats` - Complete player statistics
- `PlayerType` - Player classification enum
- `DatabaseStats` - Database overview
- `UploadResponse` - File upload result
- `ClaudeQueryRequest/Response` - Claude AI interaction

## Routing

**React Router v6** with routes:
- `/` → Redirects to `/dashboard`
- `/dashboard` → Dashboard page
- `/upload` → Upload page
- `/players` → Players list
- `/players/:playerName` → Player profile
- `/claude` → Claude chat interface

## Development

### Running Development Server

```bash
npm run dev
```

Runs on http://localhost:3000 with:
- Hot module replacement (HMR)
- Fast refresh for React components
- Proxy to backend API at http://localhost:8000

### Building for Production

```bash
npm run build
```

Creates optimized production build in `dist/`:
- Minified JavaScript and CSS
- Tree-shaken dependencies
- Optimized assets
- TypeScript type checking

### Linting

```bash
npm run lint
```

Runs ESLint with TypeScript support.

## Environment Variables

Set in `.env` file:

- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)

**Note:** Vite requires `VITE_` prefix for environment variables.

## Deployment

### Recommended: Vercel

1. Push code to GitHub
2. Import project in Vercel
3. Set environment variable: `VITE_API_URL=https://your-backend-url.com`
4. Deploy

### Alternative: Netlify, Cloudflare Pages, or any static host

Build command: `npm run build`
Publish directory: `dist`

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Lazy loading for routes
- Image optimization
- Code splitting
- Gzip compression in production
- React Query caching reduces API calls

## Accessibility

- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Focus management
- Color contrast compliance

## Future Enhancements

Potential improvements:
- Dark mode toggle
- Advanced chart types (trend lines, win rate graphs)
- Export functionality (CSV, PDF)
- Saved queries/filters
- Multi-player comparison view
- Real-time updates via WebSockets
- Mobile app (React Native)
