export type Item = {
  id: string; title: string; url: string; published: string | null;
  source: string; kind: string; subjects: string[]; methods: string[];
  first_seen: string; last_seen: string; relevance: number;
  code_url?: string; event?: string; related_url?: string;
};
export type Source = {
  id: string; name: string; url: string; checked_at: string;
  last_success: string | null; status: string; accepted: number; candidates: number; limited?: boolean;
};
export type Feed = {updated_at: string; items: Item[]; sources: Source[]; window_start: string};
export type Filters = {query: string; kind: string; subject: string; method: string; period: string; code: boolean; savedOnly: boolean};
export function effectiveDate(item: Item): string {
  const seen = item.first_seen.slice(0, 10);
  return item.published && item.published <= seen ? item.published : seen;
}
export function filterItems(items: Item[], filters: Filters, saved: string[], now: string): Item[] {
  const words = filters.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const cutoff = filters.period === 'all' ? '' : new Date(Date.parse(now.slice(0, 10) + 'T00:00:00Z') - (Number(filters.period) - 1) * 86400000).toISOString().slice(0, 10);
  return items.filter(item => {
    const text = [item.title, item.source, ...item.subjects, ...item.methods].join(' ').toLowerCase();
    return words.every(w => text.includes(w)) &&
      (filters.kind === 'All' || item.kind === filters.kind) &&
      (filters.subject === 'All' || item.subjects.includes(filters.subject)) &&
      (filters.method === 'All' || item.methods.includes(filters.method)) &&
      (!filters.code || Boolean(item.code_url)) &&
      (!filters.savedOnly || saved.includes(item.id)) && effectiveDate(item) >= cutoff;
  }).sort((a,b) => effectiveDate(b).localeCompare(effectiveDate(a)) || b.relevance - a.relevance || a.title.localeCompare(b.title));
}
