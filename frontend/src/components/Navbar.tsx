import { useEffect, useRef, useState } from 'react';
import { Sun, Moon, BarChart3, CarFront, UserCircle, ChevronDown } from 'lucide-react';

interface NavbarProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
  showAdmin: boolean;
  setShowAdmin: (show: boolean) => void;
  showSurgeTracker: boolean;
  setShowSurgeTracker: (show: boolean) => void;
  showFareIntelligence: boolean;
  setShowFareIntelligence: (show: boolean) => void;
  onUserMenuAction: (action: 'profile' | 'submissions' | 'fare-intelligence' | 'saved-routes' | 'settings' | 'logout') => void;
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
  onUserMenuAction,
  onLogoClick,
}) => {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeMenu = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) setUserMenuOpen(false);
    };
    document.addEventListener('mousedown', closeMenu);
    return () => document.removeEventListener('mousedown', closeMenu);
  }, []);

  const menuItems = [
    ['profile', 'My Profile'],
    ['submissions', 'My Fare Submissions'],
    ['fare-intelligence', 'Fare Intelligence'],
    ['saved-routes', 'Saved Routes'],
    ['settings', 'Settings'],
    ['logout', 'Logout'],
  ] as const;

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
          onClick={onLogoClick}
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
          }}
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${showFareIntelligence ? 'bg-[#282a2a] text-[#e1e3e2]' : 'text-[#dfc0b1] hover:text-[#e1e3e2]'}`}
        >
          Fare Intelligence
        </button>
        <a href="#about" className="px-3 py-2 text-sm text-[#dfc0b1] transition-colors hover:text-[#e1e3e2]">About</a>
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
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen((open) => !open)}
            className="flex items-center gap-1 rounded-full bg-[#282a2a] px-2 py-1.5 text-[#e1e3e2]"
            aria-label="Open user menu"
            aria-expanded={userMenuOpen}
          >
            <UserCircle size={19} />
            <ChevronDown size={13} className={userMenuOpen ? 'rotate-180 transition-transform' : 'transition-transform'} />
          </button>
          {userMenuOpen && (
            <div className="absolute right-0 top-12 w-56 rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-2 shadow-2xl">
              <p className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Local profile</p>
              {menuItems.map(([action, label]) => (
                <button
                  key={action}
                  onClick={() => {
                    setUserMenuOpen(false);
                    onUserMenuAction(action);
                  }}
                  className={`w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition-colors hover:bg-[var(--bg-primary)] ${action === 'fare-intelligence' ? 'text-[var(--accent-color)]' : 'text-[var(--text-primary)]'}`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      </div>
    </header>
  );
};
export default Navbar;
