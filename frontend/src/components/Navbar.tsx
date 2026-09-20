import { Sun, Moon, BarChart3, Search } from 'lucide-react';

interface NavbarProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
  showAdmin: boolean;
  setShowAdmin: (show: boolean) => void;
  onLogoClick: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  darkMode,
  toggleDarkMode,
  showAdmin,
  setShowAdmin,
  onLogoClick,
}) => {
  return (
    <header className="sticky top-0 z-50 w-full glass-panel border-b border-[var(--glass-border)] py-2 md:py-3 px-4 md:px-12 flex justify-between items-center transition-all duration-300">
      {/* Branding Logo */}
      <div className="flex items-center cursor-pointer select-none" onClick={onLogoClick}>
        <img 
          src="/logo.png" 
          alt="RideCompare Logo" 
          className="h-16 md:h-24 object-contain hover:scale-[1.05] transition-transform" 
        />
      </div>

      {/* Main Pages Navigation (Only core pages) */}
      <nav className="hidden md:flex items-center gap-8 text-xs font-bold text-[var(--text-secondary)]">
        <button 
          onClick={() => setShowAdmin(false)}
          className={`hover:text-[var(--text-primary)] transition-colors ${!showAdmin ? 'text-indigo-600 dark:text-indigo-400 font-extrabold' : ''}`}
        >
          Compare Rides
        </button>
        <button 
          onClick={() => setShowAdmin(true)}
          className={`hover:text-[var(--text-primary)] transition-colors ${showAdmin ? 'text-indigo-600 dark:text-indigo-400 font-extrabold' : ''}`}
        >
          Analytics Dashboard
        </button>
      </nav>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Toggle View button for mobile/tablet */}
        <button
          onClick={() => setShowAdmin(!showAdmin)}
          className="md:hidden p-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-primary)]"
          title={showAdmin ? "Compare Rides" : "Analytics"}
        >
          {showAdmin ? <Search size={16} /> : <BarChart3 size={16} />}
        </button>

        {/* Theme Toggler */}
        <button
          onClick={toggleDarkMode}
          className="p-2.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-primary)] hover:bg-[var(--bg-primary)] hover:scale-105 transition-all duration-200"
          aria-label="Toggle dark/light mode"
        >
          {darkMode ? <Sun size={16} className="text-yellow-400" /> : <Moon size={16} className="text-slate-600" />}
        </button>
      </div>
    </header>
  );
};
export default Navbar;
