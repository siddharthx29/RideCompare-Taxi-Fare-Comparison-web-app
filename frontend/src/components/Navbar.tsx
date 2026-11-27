import { BarChart3, CarFront } from 'lucide-react';

interface NavbarProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
  showAdmin: boolean;
  setShowAdmin: (show: boolean) => void;
  showSurgeTracker: boolean;
  setShowSurgeTracker: (show: boolean) => void;
  showFareIntelligence: boolean;
  setShowFareIntelligence: (show: boolean) => void;
  showAbout: boolean;
  setShowAbout: (show: boolean) => void;
  currentPath: string;
  onNavigate: (path: string) => void;
  onLogoClick: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  darkMode,
  toggleDarkMode,
  showAdmin,
  setShowAdmin,
  showSurgeTracker,
  setShowSurgeTracker,
  showFareIntelligence,
  setShowFareIntelligence,
  showAbout,
  setShowAbout,
  currentPath,
  onNavigate,
  onLogoClick,
}) => {
  return (
    <header className="fixed left-0 top-0 z-50 h-16 w-full border-b border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-2xl shadow-[var(--shadow-md)]">
      <div className="mx-auto flex h-full w-full items-center justify-between px-4 md:px-8">
        <div className="flex items-center gap-8">
          <div className="flex cursor-pointer select-none items-center gap-2" onClick={onLogoClick}>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#e86d10] shadow-sm">
              <CarFront size={18} className="text-[#491c00]" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-base font-semibold tracking-tight text-[var(--text-primary)]">RideCompare</span>
              <span className="mt-1 text-[9px] font-bold uppercase tracking-[0.12em] text-[var(--text-secondary)]">Compare Rides. Save More.</span>
            </div>
          </div>

          <nav className="hidden items-center gap-1 text-sm lg:flex">
            <button
              onClick={() => {
                setShowAdmin(false);
                setShowSurgeTracker(false);
                setShowFareIntelligence(false);
                setShowAbout(false);
              }}
              className="rounded-lg px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)] cursor-pointer"
            >
              Home
            </button>
            <button
              onClick={onLogoClick}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${!showAdmin && !showSurgeTracker && !showFareIntelligence && !showAbout && currentPath === '/' ? 'bg-[var(--bg-secondary)] border border-[var(--glass-border)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
            >
              Compare Rides
            </button>
            <button
              onClick={() => {
                setShowAdmin(false);
                setShowSurgeTracker(false);
                setShowFareIntelligence(true);
                setShowAbout(false);
              }}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${showFareIntelligence ? 'bg-[var(--bg-secondary)] border border-[var(--glass-border)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
            >
              Fare Intelligence
            </button>
            <button
              onClick={() => {
                setShowAdmin(false);
                setShowSurgeTracker(false);
                setShowFareIntelligence(false);
                setShowAbout(false);
                onNavigate('/routes');
              }}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${currentPath.startsWith('/routes') ? 'bg-[var(--bg-secondary)] border border-[var(--glass-border)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
            >
              Route Fares
            </button>
            <button
              onClick={() => {
                setShowAdmin(false);
                setShowSurgeTracker(false);
                setShowFareIntelligence(false);
                setShowAbout(false);
                onNavigate('/blog');
              }}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${currentPath.startsWith('/blog') ? 'bg-[var(--bg-secondary)] border border-[var(--glass-border)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
            >
              Guides
            </button>
            <button
              onClick={() => {
                setShowAdmin(false);
                setShowSurgeTracker(false);
                setShowFareIntelligence(false);
                setShowAbout(true);
                onNavigate('/');
              }}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${showAbout ? 'bg-[var(--bg-secondary)] border border-[var(--glass-border)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
            >
              About
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Toggle View button for mobile/tablet */}
          <button
            onClick={() => {
              setShowAdmin(false);
              setShowSurgeTracker(false);
              setShowFareIntelligence(true);
            }}
            className="md:hidden p-2 rounded-xl border border-[var(--glass-border)] bg-[var(--bg-secondary)] text-[var(--text-primary)]"
            title="Fare Intelligence"
          >
            <BarChart3 size={16} />
          </button>

          <button
            onClick={toggleDarkMode}
            role="switch"
            aria-checked={!darkMode}
            aria-label="Toggle day and night mode"
            title={darkMode ? 'Switch to Day mode' : 'Switch to Night mode'}
            className="relative flex h-9 w-[72px] items-center justify-between rounded-full border border-[var(--glass-border)] bg-[var(--bg-secondary)] px-2 transition-colors cursor-pointer"
          >
            <span
              className={`absolute top-1 left-1 h-7 w-7 rounded-full shadow-sm transition-transform duration-300 ${
                darkMode
                  ? 'translate-x-0 bg-[#282a2a]'
                  : 'translate-x-[34px] bg-[#ff8055]'
              }`}
            />
            {/* Vector Moon Icon (Night) */}
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`relative z-10 h-4 w-4 transition-colors ${darkMode ? 'text-[#ffb68e]' : 'text-[var(--text-secondary)]'}`}
            >
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
            {/* Vector Sun Icon (Day) */}
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`relative z-10 h-4 w-4 transition-colors ${!darkMode ? 'text-white' : 'text-[var(--text-secondary)]'}`}
            >
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
};
export default Navbar;
