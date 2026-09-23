# Drug Discovery RSS

A compact, free research feed covering drug discovery and cheminformatics: small molecules, peptides, antibodies, protein design, targets, and emerging therapeutic modalities.

## What is included

- Real research metadata collected from Europe PMC, arXiv, Crossref, selected blogs, and GitHub.
- Date-grouped headlines, source filters, subject and method tags, search, date ranges, confirmed code links, and browser-local bookmarks.
- A source-status page with last successful collection, result counts, and retrieval-limit notices.
- A manually curated community feed. **No automatic X collection or popularity ranking is enabled.**
- A GitHub Actions workflow that collects every four hours and publishes a static GitHub Pages site.

The supplied snapshot was fetched from public sources. It is not demo or invented content. View Sources in the preview for its collection timestamp. Publication metadata may include future journal issue dates; those records are displayed under their discovery date.

## Run locally

Requirements: Node.js 24, npm, Python 3.10 or newer, and network access for collection. Python collection uses only the standard library.

```sh
npm ci
npm run dev
```

Open the local address printed by the development server. This preview reads the saved research snapshot. To refresh it:

```sh
npm run collect
```

No API key is required. An optional `GITHUB_TOKEN` increases GitHub's API allowance; GitHub Actions supplies its own free token automatically. Do not put tokens into website code, configuration files, or committed files.

## Publish on GitHub Pages

1. Create a **public** repository, with `main` as its default branch. Upload this project's contents to the repository root, including `.github/workflows/refresh-and-deploy.yml`. Do not upload `node_modules`, `dist`, or local environment files.
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source.
3. In **Actions**, enable workflows if asked. Run **Refresh research and publish** using **Run workflow**. Depending on account or organization restrictions, an owner may need to allow the workflow's contents-write and Pages permissions.
4. The workflow's deployment step provides the public URL. It supports both `username.github.io` and project sites such as `username.github.io/discovery-radar/`; the base path is obtained from GitHub Pages configuration.

The workflow also runs on pushes to `main` and at minute 17 every four hours UTC. Schedules can be delayed, and GitHub can disable scheduled workflows in inactive public repositories. Check Actions if updates stop; re-enable or run the workflow manually as needed.

Research history is saved in the dedicated **radar-data** branch. This contains only public normalized headline records and source status. Do not delete that branch unless you intend to reset the archive. The workflow restores this history before collection and updates it with a normal, non-forced push. It does not rely on expiring Actions caches for persistent data. Workflows are serialized to prevent overlapping archive writes.

The site is ready to publish but is **not already deployed**. A GitHub account/repository and Pages activation are still required.

## Edit sources and topics

- `config/sources.json`: source URLs, queries, journal ISSNs, GitHub repositories, and retrieval caps. Set `enabled` to `false` to disable a source.
- `config/topics.json`: subject tags, method tags, direct relevance phrases, contextual terms, and exclusions. Expressions use Python regular-expression syntax.
- `config/community.json`: manually selected discussion links.

A community entry has this shape:

```json
{
  "id": "unique-discussion-id",
  "title": "Your neutral description of the discussion",
  "url": "https://x.com/account/status/POST_ID",
  "author": "@account",
  "date": "2026-09-23",
  "tags": ["Protein design", "Benchmarks"]
}
```

Replace the example with an actual verified link; do not add it as sample content. Add entries to the existing JSON array. Community links are displayed in the order entered, newest first by convention. No engagement numbers are fabricated.

## Filtering and coverage

The collector first queries known sources, then applies two gates. The relevance gate requires direct drug-discovery/cheminformatics language or both discovery context and an applicable method. The editorial gate favors specialist journals and reusable contributions such as methods, models, benchmarks, datasets, software, platforms, and meaningful design or target-discovery approaches. Routine application papers are excluded from broad journals when docking, pathway, extract, animal-study, or similar language is incidental. The configured excluded-journal list is explicit and editable; it is a feed policy, not a claim about a publisher's editorial quality. Titles and available abstracts/feed descriptions inform tags; third-party abstracts and full text are not included in public output.

This is a configurable research digest, **not exhaustive indexing or a scientific quality assessment**. Tagging can be imperfect, particularly when only a title is available. Database and source limits bound each run; Sources marks when a limit was reached. bioRxiv and other biomedical preprints are covered through Europe PMC where indexed; arXiv and ChemRxiv have separate adapters. Some blogs do not publish in every collection window.

- Journals and preprints retain distinct status.
- DOI normalization and canonical IDs prevent repeated entries.
- Exact matching titles with different DOIs are linked as **matching titles**, not asserted to be verified publication versions.
- New repository discovery and software release monitoring are distinct from ordinary commits.
- GitHub URLs explicitly present in source descriptions/abstracts can supply “With code” links.
- Publication date and first discovery date are stored separately.
- Records persist when a source fails. If every source fails, the collector exits with an error and leaves the saved feed untouched.
- The collector uses a 14-day overlapping window. Europe PMC also checks first-indexed dates to find late-indexed material. Other feeds may expose only their latest entries.

## Checks and static export

```sh
npm test
npm run typecheck
npm run build
python3 collector/validate_export.py dist/client
```

To verify a project-site path locally:

```sh
PAGES_BASE_PATH=/discovery-radar npm run build
```

Publish **only `dist/client`**. The build also produces server intermediates, but GitHub Pages does not use them. The project requires no hosted backend, database, paid AI, analytics, or tracking service.

The client supports an optional browser `search_research` tool for agents when WebMCP is available; ordinary browsing does not require it. Bookmarks use browser storage and do not sync across devices.

## Costs and maintenance

The default public-repository setup uses public data sources and GitHub's free public-repository Pages/Actions features. No paid APIs or subscriptions are configured. Account-specific GitHub limits still apply. Keep the repository public for the intended free setup; check your account's allowance before changing visibility or runner types.

Inspect Sources and failed workflow runs periodically. If an endpoint changes, update its adapter or disable that source. API outages and rate limiting do not indicate an absence of new research.
