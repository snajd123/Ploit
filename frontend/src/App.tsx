import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import PlayersList from './pages/PlayersList';
import PlayerProfile from './pages/PlayerProfile';
import ClaudeChat from './pages/ClaudeChat';
import PreGame from './pages/PreGame';
// GTOAnalysis moved to player profiles - redirect /gto to /players
import GTOBrowser from './pages/GTOBrowser';
import Sessions from './pages/Sessions';
import SessionDetail from './pages/SessionDetail';
import SessionGroupAnalysis from './pages/SessionGroupAnalysis';
import Settings from './pages/Settings';
import StatsGlossary from './pages/StatsGlossary';
import MyGame from './pages/MyGame';
import Pools from './pages/Pools';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/my-game" replace />} />
          <Route path="my-game" element={<MyGame />} />
          <Route path="pools" element={<Pools />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="players" element={<PlayersList />} />
          <Route path="players/:playerName" element={<PlayerProfile />} />
          <Route path="claude" element={<ClaudeChat />} />
          <Route path="pre-game" element={<PreGame />} />
          <Route path="strategy" element={<Navigate to="/pre-game" replace />} />
          <Route path="gto" element={<Navigate to="/players" replace />} />
          <Route path="gto-browser" element={<GTOBrowser />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="sessions/analysis" element={<SessionGroupAnalysis />} />
          <Route path="sessions/:sessionId" element={<SessionDetail />} />
          <Route path="glossary" element={<StatsGlossary />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
