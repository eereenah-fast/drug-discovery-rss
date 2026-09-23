#!/usr/bin/env python3
"""Free, incremental research collection. Standard library only; no paid services."""
import argparse
import concurrent.futures
import datetime as dt
import email.utils
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime.now(UTC)
STAMP = NOW.isoformat(timespec="seconds")
UA = "DiscoveryRadar/1.0 (public research metadata aggregator)"


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(value or "")))).strip()


def date(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        try:
            return email.utils.parsedate_to_datetime(value).date().isoformat()
        except (TypeError, ValueError):
            return value[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value[:10]) else None


def request(url, json_result=True, github=False):
    headers = {"User-Agent": UA, "Accept": "application/json" if json_result else "application/xml,text/xml,*/*"}
    if github and os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    for attempt in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                raw = r.read(15_000_000)
            return json.loads(raw) if json_result else raw
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt:
                raise
        time.sleep(2)


def url_query(base, params):
    return base + "?" + urllib.parse.urlencode(params)


def doi_id(doi):
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi or "", flags=re.I).strip().lower()


def record(title, url, published, source, kind, abstract="", doi="", **extra):
    if not title or not url.startswith(("https://", "http://")):
        return None
    doi = doi_id(doi)
    key = "doi:" + doi if doi else re.sub(r"[?#].*$", "", url).rstrip("/")
    code_match = re.search(r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", html.unescape(abstract))
    if code_match and "code_url" not in extra:
        extra["code_url"] = "https://github.com/" + code_match[1].rstrip(".")
    return {"id": key, "title": clean(title), "url": url, "published": date(published),
            "source": source, "kind": kind, "doi": doi or None, "_text": clean(abstract), **extra}


def classify(item, config):
    title = item["title"].lower()
    text = title + " " + item.get("_text", "").lower()
    direct = any(re.search(p, text) for p in config["direct_relevance"])
    context = any(re.search(p, text) for p in config["discovery_context"])
    methods = [k for k, patterns in config["methods"].items() if any(re.search(p, text) for p in patterns)]
    if not direct and not (context and methods):
        return None
    # Materials/energy methods need an explicit therapeutic application.
    if any(re.search(p, title) for p in config["excluded_title_context"]) and not context:
        return None
    if not quality_gate(item, config):
        return None
    subjects = [k for k, patterns in config["subjects"].items() if any(re.search(p, text) for p in patterns)]
    if not subjects:
        subjects = ["Discovery methods"]
    if not methods:
        methods = ["Discovery research"]
    item["subjects"], item["methods"] = subjects, methods
    item["relevance"] = min(100, 45 + 20 * direct + 10 * context + 5 * len(methods))
    item.pop("_text", None)  # Do not republish abstracts or third-party full text.
    return item


def quality_gate(item, config):
    """Keep reusable discovery contributions; reject incidental docking/pharmacology."""
    title = item["title"].lower()
    text = title + " " + item.get("_text", "").lower()
    source = item.get("source", "").lower()
    if any(re.search(pattern, source) for pattern in config.get("excluded_journals", [])):
        return False
    if item.get("kind") in ("Blogs", "Code"):
        return True
    if any(re.search(pattern, text) for pattern in ("cheminformatics", "chemoinformatics", "\\brdkit\\b", "molecular glue", "engineering")):
        return True
    if any(re.search(pattern, text) for pattern in config.get("contribution_terms", [])):
        return True
    if any(re.search(pattern, title) for pattern in config.get("routine_application_titles", [])):
        return any(re.search(pattern, source) for pattern in config.get("preferred_journals", []))
    return any(re.search(pattern, source) for pattern in config.get("preferred_journals", []))


def europe(source, since, until):
    items, cursor = [], "*"
    query = f'({source["query"]}) AND (FIRST_IDATE:[{since} TO {until}] OR FIRST_PDATE:[{since} TO {until}]) sort_date:y'
    for _ in range(source.get("pages", 3)):
        search_url = url_query("https://www.ebi.ac.uk/europepmc/webservices/rest/search", {
            "query": query, "format": "json", "resultType": "core", "pageSize": 100, "cursorMark": cursor,
            })
        data = request(search_url)
        if "resultList" not in data or "hitCount" not in data:
            time.sleep(2)
            data = request(search_url)
        if "resultList" not in data or "hitCount" not in data:
            if items:
                source["warning"] = "Pagination interrupted; earlier pages were retained."
                break
            raise ValueError("Europe PMC returned an invalid search response")
        rows = data.get("resultList", {}).get("result", [])
        for row in rows:
            doi = row.get("doi", "")
            url = "https://doi.org/" + doi if doi else f'https://europepmc.org/article/{row.get("source", "MED")}/{row["id"]}'
            journal = row.get("journalInfo", {}).get("journal", {}).get("title", "Europe PMC")
            preprint = row.get("source") == "PPR" or "preprint" in str(row.get("pubTypeList", {})).lower()
            items.append(record(row.get("title"), url, row.get("firstPublicationDate"),
                                journal or "Europe PMC", "Preprints" if preprint else "Journals",
                                row.get("abstractText", ""), doi, collected_from=source["id"]))
        source["limited"] = len(items) < data.get("hitCount", 0)
        new_cursor = data.get("nextCursorMark")
        if not rows or not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor
        time.sleep(.4)
    return items


def crossref(source, since, until):
    # Index-date updates can bury new papers beneath bulk updates to old records.
    filters = f"from-pub-date:{since},until-pub-date:{until}"
    if source.get("prefix"):
        endpoint = "https://api.crossref.org/prefixes/" + source["prefix"] + "/works"
    else:
        endpoint = "https://api.crossref.org/journals/" + source["issn"] + "/works"
    data = request(url_query(endpoint, {"filter": filters, "rows": 100, "sort": "published", "order": "desc"}))
    items = []
    if "items" not in data.get("message", {}):
        raise ValueError("Crossref returned an invalid metadata response")
    source["limited"] = data["message"].get("total-results", 0) > 100
    for row in data.get("message", {}).get("items", []):
        parts = row.get("published", {}).get("date-parts", [[]])[0]
        published = "-".join(str(x).zfill(2) for x in parts) if len(parts) == 3 else None
        title = " ".join(row.get("title", []))
        item = record(title, "https://doi.org/" + row["DOI"], published, source["name"],
                      source.get("kind", "Journals"), row.get("abstract", ""), row["DOI"], collected_from=source["id"])
        if item:
            # Index changes are not necessarily new publications. Keep the initial sample current.
            if not published or published >= since:
                items.append(item)
    return items


def rss(source, since, until):
    root = ET.fromstring(request(source["url"], False))
    items = []
    def value(node, names):
        for child in node:
            if child.tag.split("}")[-1] in names:
                return "".join(child.itertext()).strip()
        return ""
    for row in root.iter():
        if row.tag.split("}")[-1] not in ("item", "entry"):
            continue
        title = value(row, ["title"])
        link = value(row, ["link"])
        if not link:
            link = next((c.attrib.get("href", "") for c in row if c.tag.split("}")[-1] == "link" and c.attrib.get("rel", "alternate") == "alternate"), "")
        published = date(value(row, ["pubDate", "published", "date", "updated"]))
        if published and (published < since or published > until):
            continue
        items.append(record(title, link, published, source["name"], source.get("kind", "Blogs"),
                            value(row, ["description", "summary", "content", "encoded"]), collected_from=source["id"]))
    return items


def arxiv(source, since, until):
    query = f'({source["query"]}) AND submittedDate:[{since.replace("-", "")}0000 TO {until.replace("-", "")}2359]'
    url = url_query("https://export.arxiv.org/api/query", {"search_query": query, "start": 0, "max_results": 100,
                      "sortBy": "submittedDate", "sortOrder": "descending"})
    source = dict(source, url=url, kind="Preprints")
    items = rss(source, since, until)
    source["limited"] = len(items) >= 100
    for item in items:
        if item:
            item["id"] = re.sub(r"v\d+$", "", item["url"].replace("http://", "https://"))
            item["url"] = item["url"].replace("http://", "https://")
    return items


def github(source, since, until):
    items = []
    # Separate discovery from release monitoring: routine pushes are never feed items.
    for query in source.get("queries", []):
        data = request(url_query("https://api.github.com/search/repositories", {
            "q": query + f" created:>={since} fork:false", "per_page": 30, "sort": "stars"}), github=True)
        source["limited"] = source.get("limited", False) or data.get("total_count", 0) > 30 or data.get("incomplete_results", False)
        for row in data.get("items", []):
            items.append(record(row["full_name"], row["html_url"], row["created_at"], "GitHub", "Code",
                        " ".join([row.get("description") or "", " ".join(row.get("topics", []))]),
                        code_url=row["html_url"], event="New repository", stars=row["stargazers_count"], collected_from=source["id"]))
        time.sleep(2)
    for repo in source.get("repositories", []):
        rows = request("https://api.github.com/repos/" + repo + "/releases?per_page=3", github=True)
        for row in rows:
            published = date(row.get("published_at"))
            if row.get("draft") or row.get("prerelease") or not published or published < since:
                continue
            items.append(record(repo + " · " + (row.get("name") or row["tag_name"]), row["html_url"], published,
                                "GitHub", "Code", "cheminformatics drug discovery software " + clean(row.get("body", "")),
                                code_url="https://github.com/" + repo, event="Software release", collected_from=source["id"]))
    return items


def normalized_title(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def merge(previous, incoming):
    records = {x["id"]: dict(x) for x in previous}
    for item in records.values():
        item["title"] = clean(item["title"])
    title_index = {normalized_title(x["title"]): x["id"] for x in previous if x["kind"] in ("Journals", "Preprints")}
    for item in incoming:
        key = item["id"]
        old = records.get(key)
        # Exact normalized title is useful for duplicate source records; different DOI versions remain linked.
        other_key = title_index.get(normalized_title(item["title"])) if item["kind"] in ("Journals", "Preprints") else None
        if not old and other_key and other_key != key:
            other = records[other_key]
            if item.get("doi") and other.get("doi") and item["doi"] != other["doi"]:
                item["related_url"] = other["url"]
                other["related_url"] = item["url"]
            elif item["kind"] == other["kind"]:
                continue
        item["first_seen"] = old.get("first_seen", STAMP) if old else STAMP
        item["last_seen"] = STAMP
        records[key] = item
        title_index[normalized_title(item["title"])] = key
    return sorted(records.values(), key=lambda x: (x.get("published") or x["first_seen"][:10], x.get("relevance", 0), x["title"]), reverse=True)


def run(args):
    config = json.loads((ROOT / "config/topics.json").read_text())
    sources = json.loads((ROOT / "config/sources.json").read_text())
    output = ROOT / args.output
    previous = json.loads(output.read_text()) if output.exists() and not getattr(args, "rebuild", False) else {"items": [], "sources": []}
    since = (NOW.date() - dt.timedelta(days=args.days)).isoformat()
    until = NOW.date().isoformat()
    accepted, statuses = [], []
    adapters = {"europepmc": europe, "crossref": crossref, "rss": rss, "arxiv": arxiv, "github": github}
    def fetch(source):
        prior = next((s for s in previous.get("sources", []) if s["id"] == source["id"]), {})
        status = {"id": source["id"], "name": source["name"], "url": source.get("homepage", source.get("url", "")),
                  "checked_at": STAMP, "last_success": prior.get("last_success"), "status": "ok", "candidates": 0, "accepted": 0}
        try:
            rows = [r for r in adapters[source["type"]](source, since, until) if r]
            status["candidates"] = len(rows)
            rows = [r for r in (classify(r, config) for r in rows) if r]
            status.update(last_success=STAMP, accepted=len(rows), limited=source.get("limited", False))
            if source.get("warning"):
                status.update(status="partial", message=source["warning"])
            return rows, status
        except Exception as e:
            status.update(status="error", message=f"{type(e).__name__}: {str(e)[:180]}")
            return [], status
    enabled = [s for s in sources if s.get("enabled", True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for rows, status in pool.map(fetch, enabled):
            accepted.extend(rows)
            statuses.append(status)
            print(f'{status["name"]}: {status["status"]}, {status["accepted"]}/{status["candidates"]} relevant', flush=True)
    if not any(s["status"] == "ok" for s in statuses):
        print("All sources failed; leaving last successful feed untouched.", file=sys.stderr)
        return 1
    # Re-apply current editorial policy to the archive so tightening rules removes
    # stale low-value records on the next successful run.
    retained = [item for item in previous["items"] if quality_gate(item, config)]
    merged = merge(retained, accepted)
    result = {"schema_version": 1, "updated_at": STAMP, "window_start": since,
              "items": merged, "sources": statuses,
              "coverage": "Selected public sources; indexing delays and source outages may affect coverage."}
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(output)
    print(f"Saved {len(merged)} unique records to {output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Overlapping lookback window")
    parser.add_argument("--output", default="public/data/feed.json")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the feed from the current collection window")
    sys.exit(run(parser.parse_args()))
