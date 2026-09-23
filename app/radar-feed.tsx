'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Radar, Search, Bookmark, ArrowUpRight, Code2, SlidersHorizontal, X, Check, Rss, ExternalLink, CircleHelp, CircleAlert } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { filterItems, effectiveDate, type Feed, type Filters, type Item } from '@/lib/feed';

type CommunityItem = {id: string; title: string; url: string; author: string; date: string; tags: string[]};
const initial: Filters = {query: '', kind: 'All', subject: 'All', method: 'All', period: '14', code: false, savedOnly: false};
const subjects = ['Small molecules', 'Peptides', 'Antibodies', 'Protein design', 'Target discovery', 'Other modalities', 'Discovery methods'];
const kinds = ['All', 'Journals', 'Preprints', 'Blogs', 'Code'];
const displayDate = (value: string) => new Date(value + 'T12:00:00Z').toLocaleDateString('en-GB', {day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC'});
const timestamp = (value: string) => new Date(value).toLocaleString('en-GB', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC'}) + ' UTC';

export default function RadarFeed({feed, community}: {feed: Feed; community: CommunityItem[]}) {
  const [filters, setFilters] = useState(initial);
  const [tab, setTab] = useState('research');
  const [saved, setSaved] = useState<string[]>([]);
  const [storageWarning, setStorageWarning] = useState(false);
  const [limit, setLimit] = useState(60);
  const [mobileFilters, setMobileFilters] = useState(false);
  const [asOf, setAsOf] = useState(feed.updated_at);
  const searchRef = useRef<HTMLInputElement>(null);
  const current = useRef({feed, saved, asOf});
  useEffect(() => { current.current = {feed, saved, asOf}; }, [feed, saved, asOf]);
  useEffect(() => {
    type PageContext = {registerTool: (tool: {name: string; description: string; inputSchema: object; annotations: object; execute: (input: unknown) => unknown}, options: {signal: AbortSignal}) => void | Promise<void>};
    const context = (document as Document & {modelContext?: PageContext}).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    const tool = {
      name: 'search_research',
      description: 'Search the research feed and update its visible filters. Returns matching headlines from this snapshot; it does not fetch new papers or change bookmarks.',
      inputSchema: {type:'object', properties:{query:{type:'string',maxLength:300},subject:{type:'string'},kind:{type:'string',enum:kinds},period:{type:'string',enum:['1','7','14','all']}},additionalProperties:false},
      annotations: {readOnlyHint:false,untrustedContentHint:true},
      execute(input: unknown) {
        if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Expected an object');
        const args = input as Record<string, unknown>;
        if (Object.keys(args).some(k => !['query','subject','kind','period'].includes(k))) throw new Error('Unknown search field');
        if (Object.values(args).some(v => typeof v !== 'string')) throw new Error('Search fields must be strings');
        if (args.query && String(args.query).length > 300) throw new Error('Query is too long');
        if (args.subject && !['All',...subjects].includes(String(args.subject))) throw new Error('Unknown subject');
        if (args.kind && !kinds.includes(String(args.kind))) throw new Error('Unknown source type');
        if (args.period && !['1','7','14','all'].includes(String(args.period))) throw new Error('Unknown date range');
        const next = {...initial, ...args} as Filters;
        const state = current.current;
        const result = filterItems(state.feed.items, next, state.saved, state.asOf);
        flushSync(() => {setFilters(next); setTab('research'); setLimit(60);});
        return {count:result.length,filters:next,items:result.slice(0,20).map(({id,title,url,subjects,methods}) => ({id,title,url,subjects,methods}))};
      },
    };
    try { void Promise.resolve(context.registerTool(tool, {signal:lifecycle.signal})).catch(() => {}); } catch { /* Optional browser capability. */ }
    return () => lifecycle.abort();
  }, []);
  useEffect(() => {
    setAsOf(new Date().toISOString());
    try { const value = JSON.parse(localStorage.getItem('discovery-radar:saved') || '[]'); if (Array.isArray(value)) setSaved(value.filter(x => typeof x === 'string')); }
    catch { setStorageWarning(true); }
    const key = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') { event.preventDefault(); searchRef.current?.focus(); }
    };
    document.addEventListener('keydown', key);
    return () => document.removeEventListener('keydown', key);
  }, []);
  function update(patch: Partial<Filters>) { setFilters(current => ({...current, ...patch})); setLimit(60); }
  function bookmark(id: string) {
    const next = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id];
    setSaved(next);
    try { localStorage.setItem('discovery-radar:saved', JSON.stringify(next)); }
    catch { setStorageWarning(true); }
  }
  const matched = useMemo(() => filterItems(feed.items, filters, saved, asOf), [feed.items, filters, saved, asOf]);
  const methods = [...new Set(feed.items.flatMap(i => i.methods))].sort();
  const groups = new Map<string, Item[]>();
  matched.slice(0, limit).forEach(item => { const date = effectiveDate(item); groups.set(date, [...(groups.get(date) || []), item]); });
  const errors = feed.sources.filter(source => source.status === 'error');
  const stale = Date.parse(asOf) - Date.parse(feed.updated_at) > 12 * 3600000;
  const today = asOf.slice(0, 10);
  const yesterday = new Date(Date.parse(today + 'T12:00:00Z') - 86400000).toISOString().slice(0, 10);
  const active = filters.subject !== 'All' || filters.method !== 'All' || filters.code || filters.savedOnly || filters.query || filters.kind !== 'All';
  const reset = () => {setFilters(initial); setLimit(60);};
  return <div className="radar-app">
    <a className="skip-link" href="#feed">Skip to feed</a>
    <header className="masthead">
      <a href="./" className="brand" aria-label="Drug Discovery RSS home"><span className="brand-mark"><Radar size={27} strokeWidth={1.6}/></span><span>drug discovery<span className="brand-light">rss</span><span className="brand-dot">.</span></span></a>
      <div className="search-box"><Search size={17}/><input ref={searchRef} aria-label="Search headlines, sources and tags" placeholder="Search headlines, sources, topics…" value={filters.query} onChange={e => {update({query:e.target.value}); setTab('research');}}/>{filters.query ? <button aria-label="Clear search" onClick={() => update({query:''})}><X size={15}/></button> : <kbd>⌘ K</kbd>}</div>
      <button className={'saved-button ' + (filters.savedOnly ? 'selected' : '')} onClick={() => {setTab('research'); update({savedOnly:!filters.savedOnly, period:'all'});}}><Bookmark size={17}/><span>Saved</span><span className="count">{saved.length}</span></button>
    </header>
    <div className="page-shell">
      <div className="intro-line"><span>DRUG DISCOVERY & CHEMINFORMATICS</span><span className="refresh"><i className={stale ? 'stale-dot' : ''}/>{stale ? 'Snapshot from ' : 'Updated '}{timestamp(feed.updated_at)}</span></div>
      <Tabs value={tab} onValueChange={value => setTab(String(value))}>
        <div className="tab-bar"><TabsList variant="line" className="primary-tabs"><TabsTrigger value="research">Research & tools</TabsTrigger><TabsTrigger value="community">Community links <span className="small-label">CURATED</span></TabsTrigger><TabsTrigger value="sources">Sources <span className="tab-count">{feed.sources.length}</span></TabsTrigger></TabsList></div>
        <TabsContent value="research">
          <div className="research-layout">
            <aside className={'filters ' + (mobileFilters ? 'mobile-open' : '')} aria-label="Research filters">
              <div className="filter-heading"><span>EXPLORE BY SUBJECT</span><button className="mobile-close" aria-label="Close filters" onClick={() => setMobileFilters(false)}><X size={18}/></button></div>
              <div className="subject-list"><button className={filters.subject === 'All' ? 'active' : ''} onClick={() => update({subject:'All'})}><span>All subjects</span><span>{feed.items.length}</span></button>{subjects.map(subject => <button key={subject} className={filters.subject === subject ? 'active' : ''} onClick={() => update({subject})}><span>{subject}</span><span>{feed.items.filter(i => i.subjects.includes(subject)).length}</span></button>)}</div>
              <div className="filter-section"><p className="filter-heading">METHOD & FOCUS</p><div className="method-list"><button className={filters.method === 'All' ? 'active' : ''} onClick={() => update({method:'All'})}>All methods</button>{methods.map(method => <button key={method} className={filters.method === method ? 'active' : ''} onClick={() => update({method})}>{method}</button>)}</div></div>
              <div className="filter-section"><label className="checkbox-label"><Checkbox checked={filters.code} onCheckedChange={checked => update({code: checked === true})}/><Code2 size={16}/> With code</label><p className="filter-hint">Confirmed repository links only.</p></div>
              <div className="sidebar-note" aria-hidden="true" />
            </aside>
            <main className="feed-main" id="feed">
              <div className="feed-title"><div><h1>{filters.savedOnly ? 'Your reading list' : filters.subject !== 'All' ? filters.subject : 'Latest discoveries'}</h1></div><button className="mobile-filter-button" onClick={() => setMobileFilters(!mobileFilters)} aria-expanded={mobileFilters}><SlidersHorizontal size={17}/> Filters</button></div>
              <div className="feed-toolbar"><div className="source-pills" aria-label="Source type">{kinds.map(kind => <button key={kind} aria-pressed={filters.kind === kind} className={filters.kind === kind ? 'active' : ''} onClick={() => update({kind})}>{kind === 'All' ? 'All sources' : kind}</button>)}</div><Select value={filters.period} onValueChange={value => update({period:String(value)})}><SelectTrigger aria-label="Date range" className="date-select"><SelectValue>{({'1':'Today','7':'Last 7 days','14':'Last 14 days','all':'All archives'} as Record<string,string>)[filters.period]}</SelectValue></SelectTrigger><SelectContent>{[['1','Today'],['7','Last 7 days'],['14','Last 14 days'],['all','All archives']].map(([value,label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select></div>
              <div className="results-line"><span aria-live="polite">{matched.length} {matched.length === 1 ? 'item' : 'items'}{filters.method !== 'All' && <> · {filters.method}</>}</span>{active ? <button onClick={reset}>Clear filters <X size={12}/></button> : <span>Newest first</span>}</div>
              {storageWarning && <div className="notice">Bookmarks work for this visit, but this browser is not allowing them to be saved.</div>}
              {stale && <div className="notice"><CircleAlert size={15}/>This snapshot is more than 12 hours old. Check Sources for the last successful collection.</div>}
              {matched.length === 0 && <div className="empty-state"><Search size={25}/><h2>{filters.savedOnly ? 'Nothing saved here yet' : 'No matching headlines'}</h2><p>{filters.savedOnly ? 'Use the bookmark beside a headline to add it to your reading list.' : 'Try a broader topic, another date range, or fewer search words.'}</p><button onClick={reset}>Show latest research</button></div>}
              {[...groups].map(([day, items]) => <section className="day-group" key={day}><div className="day-heading"><h2>{day === today ? 'Today' : day === yesterday ? 'Yesterday' : new Date(day + 'T12:00:00Z').toLocaleDateString('en-GB', {weekday:'long', day:'numeric', month:'short', timeZone:'UTC'})}</h2><span>{displayDate(day)}</span><span className="day-line"/><span>{items.length} {items.length === 1 ? 'item' : 'items'}</span></div>{items.map(item => <article className="headline-row" key={item.id}><span className={'source-dot dot-' + item.kind.toLowerCase()} title={item.kind}/><div className="headline-content"><div className="item-kicker"><span className={'kind-label kind-' + item.kind.toLowerCase()}>{item.event || (item.kind === 'Journals' ? 'Journal' : item.kind === 'Preprints' ? 'Preprint' : item.kind === 'Blogs' ? 'Blog' : 'Code')}</span><span className="source-name">{item.source}</span>{item.code_url && <a href={item.code_url} target="_blank" rel="noopener noreferrer" className="code-link"><Code2 size={13}/> Code</a>}</div><h3><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}<ArrowUpRight size={15} className="headline-arrow"/></a></h3><div className="item-tags">{item.subjects.slice(0,2).map(tag => <button className="subject-tag" key={tag} onClick={() => update({subject:tag})}>{tag}</button>)}{item.methods.slice(0,2).map(tag => <button key={tag} onClick={() => update({method:tag})}>{tag}</button>)}{item.related_url && <a href={item.related_url} target="_blank" rel="noopener noreferrer">Matching title ↗</a>}{(!item.published || item.published > item.first_seen.slice(0,10)) && <span className="date-note" title={item.published ? 'Publisher issue date: ' + item.published : 'Publication date unavailable'}>Date discovered</span>}</div></div><button className={'bookmark ' + (saved.includes(item.id) ? 'is-saved' : '')} aria-label={(saved.includes(item.id) ? 'Unsave ' : 'Save ') + item.title} aria-pressed={saved.includes(item.id)} onClick={() => bookmark(item.id)}><Bookmark size={18} fill={saved.includes(item.id) ? 'currentColor' : 'none'} strokeWidth={1.6}/></button></article>)}</section>)}
              {matched.length > limit && <button className="load-more" onClick={() => setLimit(limit + 60)}>Show more headlines <span>{matched.length - limit} remaining</span></button>}
              <p className="feed-footnote">Dates reflect publication where available. Future issue dates use the discovery date. Preprints have not necessarily been peer reviewed.</p>
            </main>
          </div>
        </TabsContent>
        <TabsContent value="community"><main className="secondary-page"><div className="section-eyebrow">FROM THE COMMUNITY</div><h1>Conversations worth reading</h1><p className="secondary-lead">Manually selected discussions on drug discovery and cheminformatics.</p><div className="notice"><CircleHelp size={17}/>This is a curated collection, not an automated popularity ranking. No paid X access is used.</div>{community.length ? community.map(item => <article className="community-row" key={item.id}><span>{item.author} · {displayDate(item.date)}</span><h2><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title} <ArrowUpRight size={17}/></a></h2><p>{item.tags.join(' · ')}</p></article>) : <div className="empty-state"><Rss size={29}/><h2>A little quieter here, for now.</h2><p>No discussions have been curated yet.<br/>Research and software updates are available in the main feed.</p><button onClick={() => setTab('research')}>Explore research <ArrowUpRight size={15}/></button></div>}</main></TabsContent>
        <TabsContent value="sources"><main className="secondary-page"><div className="section-eyebrow">BEHIND THE FEED</div><h1>Sources & coverage</h1><p className="secondary-lead">Selected public APIs and feeds. Topic rules keep the focus on drug discovery.</p><div className="source-summary"><span><Check size={17}/>{feed.sources.length - errors.length} sources responded</span><span>{errors.length ? `${errors.length} need attention` : 'All sources available'}</span><span>Last run {timestamp(feed.updated_at)}</span></div><div className="source-status-list">{feed.sources.map(source => <article key={source.id}><div><a href={source.url} target="_blank" rel="noopener noreferrer">{source.name}<ExternalLink size={13}/></a><p>{source.last_success ? 'Last success: ' + timestamp(source.last_success) : 'No successful collection yet'}{source.limited && ' · Retrieval limit reached'}</p></div><div className={'status ' + (source.status === 'ok' ? 'ok' : 'error')}>{source.status === 'ok' ? <><Check size={13}/>{source.accepted} relevant / {source.candidates} checked</> : <><CircleAlert size={13}/>{source.status === 'partial' ? 'Partial collection' : 'Temporarily unavailable'}</>}</div></article>)}</div><div className="coverage-notes"><h2>How items are selected</h2><p>Searches combine subject phrases, discovery context, and method terms. Headlines, available abstracts, and feed descriptions are used for filtering; abstracts are not republished. Automated tags can be imperfect.</p><p>The feed uses a rolling 14-day collection window and keeps earlier records. Indexed research can appear after its publication date. Sources have retrieval limits, so this is a selected digest rather than exhaustive coverage.</p><p>Scheduled refreshes run about every four hours once this site is deployed with its GitHub workflow. A local preview is a saved snapshot. If a source fails, its previously collected items remain available.</p><h2>Free by design</h2><p>No paid AI, X API, or server subscription is required. Community discussions are entered manually. Bookmarks stay in your browser and are not synced between devices.</p></div></main></TabsContent>
      </Tabs>
      <footer className="site-footer"><span><Radar size={14}/> Drug Discovery RSS</span><button onClick={() => setTab('sources')}>{errors.length ? `${errors.length} source${errors.length === 1 ? '' : 's'} need attention` : 'Source status'} <ArrowUpRight size={12}/></button></footer>
    </div>
  </div>;
}
