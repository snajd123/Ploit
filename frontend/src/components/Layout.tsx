import { useState, useEffect } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { LayoutDashboard, Upload, Users, MessageSquare, Target, Search, Menu, X, BookOpen, Crosshair, Grid3x3, BarChart2 } from 'lucide-react';
import QuickLookupModal from './QuickLookupModal';
import OnboardingModal, { shouldShowOnboarding } from './OnboardingModal';

interface NavSection {
  label: string;
  items: { to: string; icon: React.ElementType; label: string; tooltip?: string }[];
}

const Layout = () => {
  const [isQuickLookupOpen, setIsQuickLookupOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Check for onboarding on mount
  useEffect(() => {
    if (shouldShowOnboarding()) {
      setShowOnboarding(true);
    }
  }, []);

  const navSections: NavSection[] = [
    {
      label: 'Prepare',
      items: [
        { to: '/strategy', icon: Target, label: 'Strategy', tooltip: 'Pre-game opponent strategy' },
        { to: '/gto-browser', icon: Grid3x3, label: 'GTO Ranges', tooltip: 'Browse GTO opening ranges' },
      ]
    },
    {
      label: 'Review',
      items: [
        { to: '/sessions', icon: BarChart2, label: 'Sessions', tooltip: 'Your session history' },
        { to: '/gto', icon: Crosshair, label: 'GTO Analysis', tooltip: 'Compare play vs GTO' },
        { to: '/claude', icon: MessageSquare, label: 'Claude AI', tooltip: 'AI-powered analysis' },
      ]
    },
    {
      label: 'Research',
      items: [
        { to: '/players', icon: Users, label: 'Players', tooltip: 'Player stats database' },
        { to: '/glossary', icon: BookOpen, label: 'Stats Guide', tooltip: 'Stats glossary' },
      ]
    },
    {
      label: 'Data',
      items: [
        { to: '/upload', icon: Upload, label: 'Upload', tooltip: 'Import hand histories' },
        { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', tooltip: 'Database overview' },
      ]
    },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              {/* Mobile menu button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="lg:hidden text-gray-600 hover:text-gray-900 p-2 -ml-2"
              >
                {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>

              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg sm:text-xl">♠</span>
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold text-gray-900">Poker Analysis</h1>
                <p className="text-xs text-gray-500 hidden sm:block">AI-Powered Strategic Insights</p>
              </div>
            </div>
            <button
              onClick={() => setIsQuickLookupOpen(true)}
              className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Search className="w-4 h-4" />
              <span className="hidden sm:inline">Quick Lookup</span>
            </button>
          </div>
        </div>
      </header>

      {/* Desktop Navigation */}
      <nav className="hidden lg:block bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center">
            {navSections.map((section, sectionIndex) => (
              <div key={section.label} className="flex items-center">
                {/* Section divider (except first) */}
                {sectionIndex > 0 && (
                  <div className="h-6 w-px bg-gray-200 mx-2" />
                )}
                {/* Section label */}
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wider px-2">
                  {section.label}
                </span>
                {/* Section items */}
                {section.items.map(({ to, icon: Icon, label, tooltip }) => (
                  <NavLink
                    key={to}
                    to={to}
                    title={tooltip}
                    className={({ isActive }) =>
                      `flex items-center space-x-1.5 py-4 px-3 border-b-2 font-medium text-sm transition-colors ${
                        isActive
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`
                    }
                  >
                    <Icon size={16} />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            ))}
          </div>
        </div>
      </nav>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <nav className="lg:hidden bg-white border-b border-gray-200 shadow-lg max-h-[70vh] overflow-y-auto">
          <div className="px-4 py-2">
            {navSections.map((section) => (
              <div key={section.label} className="mb-2">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 py-2 border-b border-gray-100">
                  {section.label}
                </div>
                {section.items.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center space-x-3 py-3 px-4 rounded-lg font-medium text-sm transition-colors ${
                        isActive
                          ? 'bg-blue-50 text-blue-600'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`
                    }
                  >
                    <Icon size={20} />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            ))}
          </div>
        </nav>
      )}

      {/* Main content */}
      <main className="flex-1 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            Poker Analysis Platform &copy; {new Date().getFullYear()}
          </p>
        </div>
      </footer>

      {/* Quick Lookup Modal */}
      <QuickLookupModal
        isOpen={isQuickLookupOpen}
        onClose={() => setIsQuickLookupOpen(false)}
      />

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={showOnboarding}
        onClose={() => setShowOnboarding(false)}
      />
    </div>
  );
};

export default Layout;
