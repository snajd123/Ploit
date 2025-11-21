import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import PlayersList from './pages/PlayersList';
import PlayerProfile from './pages/PlayerProfile';
import ClaudeChat from './pages/ClaudeChat';
import PreGameStrategy from './pages/PreGameStrategy';
import GTOAnalysis from './pages/GTOAnalysis';
import Settings from './pages/Settings';
import StatsGlossary from './pages/StatsGlossary';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="players" element={<PlayersList />} />
          <Route path="players/:playerName" element={<PlayerProfile />} />
          <Route path="claude" element={<ClaudeChat />} />
          <Route path="strategy" element={<PreGameStrategy />} />
          <Route path="gto" element={<GTOAnalysis />} />
          <Route path="glossary" element={<StatsGlossary />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
