import { Sun, Moon, BarChart3, CarFront } from 'lucide-react';

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
    <header className="fixed left-0 top-0 z-50 h-16 w-full bg-[#111414]/95 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.4)]">
      <div className="mx-auto flex h-full w-full items-center justify-between px-4 md:px-8">
      <div className="flex items-center gap-8">
      <div className="flex cursor-pointer select-none items-center gap-2" onClick={onLogoClick}>
        <div className="flex h-7 w-7 items-center justify-center rounded bg-[#e86d10]">
          <CarFront size={18} className="text-[#491c00]" />
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-base font-semibold tracking-tight text-[#e1e3e2]">RideCompare</span>
          <span className="mt-1 text-[9px] font-bold uppercase tracking-[0.12em] text-[#b8aaa2]">Compare Rides. Save More.</span>
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
          className="px-3 py-2 text-sm text-[#dfc0b1] transition-colors hover:text-[#e1e3e2]"
        >
          Home
        </button>
        <button
          onClick={onLogoClick}
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${!showAdmin && !showSurgeTracker && !showFareIntelligence ? 'bg-[#282a2a] text-[#e1e3e2]' : 'text-[#dfc0b1] hover:text-[#e1e3e2]'}`}
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
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${showFareIntelligence ? 'bg-[#282a2a] text-[#e1e3e2]' : 'text-[#dfc0b1] hover:text-[#e1e3e2]'}`}
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
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${currentPath.startsWith('/routes') ? 'bg-[#282a2a] text-[#e1e3e2]' : 'text-[#dfc0b1] hover:text-[#e1e3e2]'}`}
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
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${currentPath.startsWith('/blog') ? 'bg-[#282a2a] text-[#e1e3e2]' : 'text-[#dfc0b1] hover:text-[#e1e3e2]'}`}
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
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${showAbout ? 'bg-[#282a2a] text-[#e1e3e2]' : 'text-[#dfc0b1] hover:text-[#e1e3e2]'}`}
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
          className="md:hidden p-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-primary)]"
          title="Fare Intelligence"
        >
          <BarChart3 size={16} />
        </button>

        <button
          onClick={toggleDarkMode}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[#282a2a] text-[#e1e3e2]"
          aria-label="Toggle dark/light mode"
        >
          {darkMode ? <Sun size={16} className="text-[#ffb68e]" /> : <Moon size={16} className="text-slate-600" />}
        </button>
      </div>
      </div>
    </header>
  );
};
export default Navbar;
