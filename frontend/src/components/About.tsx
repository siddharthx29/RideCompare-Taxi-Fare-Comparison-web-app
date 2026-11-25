import { MapPin, Route, ShieldCheck, Users } from 'lucide-react';

export function About() {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 animate-fade-in">
      <section className="glass-panel rounded-2xl p-6 md:p-8">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-color)] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          <MapPin size={12} /> Made in Goa, India
        </span>
        <h1 className="mt-4 text-3xl font-bold text-[var(--text-primary)]">About RideCompare</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
          RideCompare helps people compare taxi options and fares across providers for the routes they travel.
          It brings location search, route information, provider options, and community fare observations into one straightforward experience.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
          <Route size={20} className="text-[var(--accent-color)]" />
          <h2 className="mt-3 text-sm font-bold">Route-focused</h2>
          <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">
            Search pickup and destination locations and compare available ride categories for the selected route.
          </p>
        </section>
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
          <ShieldCheck size={20} className="text-emerald-500" />
          <h2 className="mt-3 text-sm font-bold">Clear price sources</h2>
          <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">
            Live provider quotes, estimates, and community reports are displayed separately so users know what they are seeing.
          </p>
        </section>
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5">
          <Users size={20} className="text-[var(--accent-blue)]" />
          <h2 className="mt-3 text-sm font-bold">Community-powered</h2>
          <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">
            Users can contribute fares and vote on observations without needing to create an account.
          </p>
        </section>
      </div>

      <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5 md:p-6">
        <h2 className="text-base font-bold">Designed and developed in Goa</h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
          RideCompare is made by a developer from Goa, India, with the goal of making taxi fare comparisons easier,
          more transparent, and accessible around the world.
        </p>
        <p className="mt-3 text-xs text-[var(--text-secondary)]">
          Provider availability and prices vary by city and region. Always confirm the final fare in the relevant provider app.
        </p>
      </section>
    </div>
  );
}
