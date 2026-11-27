import { useState, useCallback } from 'react';
import { RefreshCw, Upload, CheckCircle2, AlertTriangle, Globe, Search, Sparkles } from 'lucide-react';
import { apiFetch } from '../utils/api';

interface SeoPageRow {
  page_id: string;
  slug: string;
  page_type: string;
  target_keyword: string;
  location: string | null;
  seo_title: string;
  meta_description: string;
  status: string;
  quality_score: number;
  quality_issues: string[];
  canonical_url: string;
  impressions: number;
  clicks: number;
  ctr: number;
}

interface SeoKeywordRow {
  id: number;
  keyword: string;
  category: string;
  intent: string;
  location: string | null;
  search_volume: number | null;
  impressions: number;
  clicks: number;
  mapped_page_slug: string | null;
  opportunity_score: number;
  data_source: string;
}

interface SeoOverviewResponse {
  summary: {
    total_pages: number;
    published_pages: number;
    draft_or_flagged_pages: number;
    total_keywords: number;
    unmapped_keywords: number;
  };
  integrations: {
    google_search_console: { configured: boolean; required_env: string[] };
    bing_webmaster_tools: { configured: boolean; required_env: string[] };
    google_analytics_4: { configured: boolean; required_env: string[] };
  };
  pages: SeoPageRow[];
  keywords: SeoKeywordRow[];
  audit_logs: { id: number; run_type: string; status: string; summary: string; created_at: string }[];
}

export function SeoAdminDashboard() {
  const [adminKey, setAdminKey] = useState('');
  const [overview, setOverview] = useState<SeoOverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [csvText, setCsvText] = useState('');
  const [previewPage, setPreviewPage] = useState<SeoPageRow | null>(null);

  const headers = useCallback(
    () => ({
      'Content-Type': 'application/json',
      ...(adminKey.trim() ? { 'X-Admin-Key': adminKey.trim() } : {}),
    }),
    [adminKey]
  );

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await apiFetch('/api/seo/admin/overview', { headers: headers() });
      const data = (await res.json()) as SeoOverviewResponse;
      setOverview(data);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to load SEO overview.');
    } finally {
      setLoading(false);
    }
  }, [headers]);

  const handleSyncCatalog = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await apiFetch('/api/seo/admin/sync-catalog', { method: 'POST', headers: headers() });
      const data = await res.json();
      setMessage(`Catalog synced: ${data.pages_created} created, ${data.pages_updated} updated, ${data.keywords_seeded} keywords seeded.`);
      await loadOverview();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Catalog sync failed.');
      setLoading(false);
    }
  };

  const handleRunMaintenance = async (cadence: 'daily' | 'weekly' | 'monthly') => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await apiFetch(`/api/seo/admin/maintenance/run?cadence=${cadence}`, {
        method: 'POST',
        headers: headers(),
      });
      const data = await res.json();
      setMessage(data.summary);
      await loadOverview();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Maintenance run failed.');
      setLoading(false);
    }
  };

  const handleImportCsv = async () => {
    if (!csvText.trim()) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await apiFetch('/api/seo/admin/keywords/import-csv', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ csv_text: csvText, source: 'csv_import' }),
      });
      const data = await res.json();
      setMessage(`CSV imported: ${data.imported} new keywords, ${data.updated_duplicates} duplicates updated.`);
      setCsvText('');
      await loadOverview();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'CSV import failed.');
      setLoading(false);
    }
  };

  const togglePageStatus = async (page: SeoPageRow) => {
    const nextStatus = page.status === 'published' ? 'draft' : 'published';
    try {
      await apiFetch(`/api/seo/admin/pages/${page.page_id}/status`, {
        method: 'PATCH',
        headers: headers(),
        body: JSON.stringify({ status: nextStatus }),
      });
      await loadOverview();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to update page status.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Sparkles size={18} className="text-[var(--accent-color)]" /> Automated Programmatic SEO Engine
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            Manage keyword opportunities, metadata previews, page quality validation, Search Console / Bing sync, and scheduled audits.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Admin Key (if prod)"
            className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-1.5 text-xs"
          />
          <button
            onClick={loadOverview}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent-color)] px-3 py-1.5 text-xs font-bold text-white cursor-pointer"
          >
            <RefreshCw size={13} /> Load Engine
          </button>
          <button
            onClick={handleSyncCatalog}
            disabled={loading}
            className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-1.5 text-xs font-bold cursor-pointer"
          >
            Sync Cities &amp; Services
          </button>
          <button
            onClick={() => handleRunMaintenance('weekly')}
            disabled={loading}
            className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-1.5 text-xs font-bold cursor-pointer"
          >
            Run Weekly Audit
          </button>
        </div>
      </div>

      {message && (
        <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-2.5 text-xs">
          {message}
        </div>
      )}

      {overview && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
              <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">Published Pages</span>
              <p className="mt-1 text-2xl font-bold">{overview.summary.published_pages} / {overview.summary.total_pages}</p>
            </div>
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
              <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">Tracked Keywords</span>
              <p className="mt-1 text-2xl font-bold">{overview.summary.total_keywords}</p>
            </div>
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
              <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">GSC / Bing Status</span>
              <p className="mt-1 text-xs font-bold">
                GSC: {overview.integrations.google_search_console.configured ? 'Connected' : 'Pending Env'} · Bing:{' '}
                {overview.integrations.bing_webmaster_tools.configured ? 'Connected' : 'Pending Env'}
              </p>
            </div>
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
              <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">Dynamic Sitemap</span>
              <a href="/api/seo/sitemap.xml" target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-[var(--accent-color)]">
                <Globe size={13} /> /api/seo/sitemap.xml
              </a>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 space-y-2">
            <h3 className="text-xs font-bold uppercase text-[var(--text-secondary)] flex items-center gap-1.5">
              <Upload size={13} /> Import Keyword Research / Search Console CSV
            </h3>
            <textarea
              rows={3}
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              placeholder="keyword,search_volume,keyword_difficulty,impressions,clicks,position&#10;kochi airport taxi fare,480,18,120,6,9.2"
              className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-primary)] p-2.5 text-xs font-mono"
            />
            <button
              onClick={handleImportCsv}
              disabled={loading || !csvText.trim()}
              className="rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white cursor-pointer disabled:opacity-50"
            >
              Import &amp; Map Keywords
            </button>
          </div>

          {previewPage && (
            <div className="rounded-xl border border-[var(--accent-color)] bg-[var(--bg-secondary)] p-4 space-y-1.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[var(--accent-color)]">Metadata Preview — {previewPage.slug}</span>
                <button onClick={() => setPreviewPage(null)} className="text-[var(--text-secondary)] hover:underline cursor-pointer">Close</button>
              </div>
              <p><strong>Title:</strong> {previewPage.seo_title}</p>
              <p><strong>Description:</strong> {previewPage.meta_description}</p>
              <p><strong>Canonical:</strong> {previewPage.canonical_url}</p>
              <p><strong>Quality Score:</strong> {previewPage.quality_score}/100 {previewPage.quality_issues.length ? `(${previewPage.quality_issues.join(', ')})` : ''}</p>
            </div>
          )}

          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 overflow-x-auto">
            <h3 className="text-xs font-bold uppercase text-[var(--text-secondary)] mb-3">Generated SEO Pages ({overview.pages.length})</h3>
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                  <th className="py-2 pr-3">Slug</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">Quality</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]">
                {overview.pages.slice(0, 25).map((p) => (
                  <tr key={p.page_id}>
                    <td className="py-2 pr-3 font-mono">{p.slug}</td>
                    <td className="py-2 pr-3">{p.page_type}</td>
                    <td className="py-2 pr-3">
                      {p.quality_score >= 100 ? (
                        <span className="inline-flex items-center gap-1 text-emerald-500"><CheckCircle2 size={12} /> 100</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-amber-500"><AlertTriangle size={12} /> {p.quality_score}</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">{p.status}</td>
                    <td className="py-2 flex gap-2">
                      <button onClick={() => setPreviewPage(p)} className="text-[var(--accent-color)] hover:underline cursor-pointer">Preview</button>
                      <button onClick={() => togglePageStatus(p)} className="text-[var(--text-secondary)] hover:underline cursor-pointer">
                        {p.status === 'published' ? 'Unpublish' : 'Publish'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 overflow-x-auto">
            <h3 className="text-xs font-bold uppercase text-[var(--text-secondary)] mb-3 flex items-center gap-1.5">
              <Search size={13} /> Top Keyword Opportunities
            </h3>
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                  <th className="py-2 pr-3">Keyword</th>
                  <th className="py-2 pr-3">Category</th>
                  <th className="py-2 pr-3">Intent</th>
                  <th className="py-2 pr-3">Mapped Page</th>
                  <th className="py-2 pr-3">Volume</th>
                  <th className="py-2">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]">
                {overview.keywords.slice(0, 20).map((k) => (
                  <tr key={k.id}>
                    <td className="py-2 pr-3 font-semibold">{k.keyword}</td>
                    <td className="py-2 pr-3">{k.category}</td>
                    <td className="py-2 pr-3">{k.intent}</td>
                    <td className="py-2 pr-3 font-mono">{k.mapped_page_slug || '— unmapped —'}</td>
                    <td className="py-2 pr-3">{k.search_volume ?? 'N/A'}</td>
                    <td className="py-2 font-bold text-[var(--accent-color)]">{k.opportunity_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
