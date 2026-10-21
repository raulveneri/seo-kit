"""Versioned, persistent evidence store for public-site crawls."""

import hashlib
import json
import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from crawl_privacy import sanitize, redact_text, redact_url, sensitive_url


SCHEMA_VERSION = 3
RULE_VERSION = 2


def now():
    return datetime.now(timezone.utc).isoformat()


def url_key(url, excluded_parameters=()):
    parsed = urlsplit(url)
    excluded = set(excluded_parameters)
    query = urlencode(sorted(((key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key not in excluded), key=lambda item: item[0]))
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", query, ""))


class CrawlStore:
    def __init__(self, path, read_only=False, store_html='both'):
        if store_html not in ('none', 'raw', 'rendered', 'both'):
            raise ValueError('invalid HTML storage policy')
        self.store_html = store_html
        self.path = Path(path).resolve()
        if not read_only:
            # Create privately before SQLite opens the file. Existing modes stay unchanged.
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600) if not self.path.exists() else None
            if descriptor is not None:
                os.close(descriptor)
        self.db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) if read_only else sqlite3.connect(path)
        self._batch = 0
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        if read_only:
            try:
                row = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
                if not row or int(row[0]) != SCHEMA_VERSION:
                    raise ValueError('crawl database requires migration by the live auditor before querying')
            except BaseException:
                self.db.close()
                raise
            return
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row and int(row[0]) not in (1, 2, SCHEMA_VERSION):
            self.db.close()
            raise ValueError(f"unsupported crawl database schema {row[0]}")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS crawls (
              id INTEGER PRIMARY KEY, origin TEXT NOT NULL, start_url TEXT NOT NULL,
              started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
              crawl_limit TEXT NOT NULL, config_json TEXT NOT NULL, robots_text TEXT,
              warnings_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS queue (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), url TEXT NOT NULL,
              depth INTEGER NOT NULL, source TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
              PRIMARY KEY (crawl_id, url)
            );
            CREATE TABLE IF NOT EXISTS pages (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), url TEXT NOT NULL,
              final_url TEXT, status INTEGER, content_type TEXT, headers_json TEXT,
              redirects_json TEXT, raw_html BLOB, rendered_html BLOB,
              raw_sha256 TEXT, rendered_sha256 TEXT, metadata_json TEXT,
              depth INTEGER NOT NULL, fetched_at TEXT NOT NULL, error TEXT,
              PRIMARY KEY (crawl_id, url)
            );
            CREATE TABLE IF NOT EXISTS links (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), source_url TEXT NOT NULL,
              target_url TEXT NOT NULL, anchor_text TEXT, source_kind TEXT NOT NULL,
              PRIMARY KEY (crawl_id, source_url, target_url, source_kind, anchor_text)
            );
            CREATE TABLE IF NOT EXISTS issues (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), url TEXT NOT NULL,
              rule_id TEXT NOT NULL, rule_version INTEGER NOT NULL,
              severity TEXT NOT NULL, state TEXT NOT NULL, evidence_json TEXT NOT NULL,
              source TEXT NOT NULL, PRIMARY KEY (crawl_id, url, rule_id, source)
            );
            CREATE TABLE IF NOT EXISTS external_data (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), url TEXT NOT NULL,
              source TEXT NOT NULL, property TEXT NOT NULL, period TEXT NOT NULL,
              queried_at TEXT NOT NULL, data_json TEXT NOT NULL,
              PRIMARY KEY (crawl_id, url, source, property, period)
            );
            CREATE TABLE IF NOT EXISTS resources (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), url TEXT NOT NULL,
              source_url TEXT NOT NULL, kind TEXT NOT NULL, status INTEGER NOT NULL,
              content_type TEXT, headers_json TEXT NOT NULL, body_sha256 TEXT NOT NULL,
              body_size INTEGER NOT NULL, fetched_at TEXT NOT NULL,
              PRIMARY KEY (crawl_id, url, source_url, kind)
            );
            CREATE INDEX IF NOT EXISTS pages_status ON pages(crawl_id, status);
            CREATE INDEX IF NOT EXISTS issues_filter ON issues(crawl_id, severity, state, rule_id);
            CREATE INDEX IF NOT EXISTS links_target ON links(crawl_id, target_url);
            CREATE INDEX IF NOT EXISTS queue_pending ON queue(crawl_id,state,depth,url);
            CREATE INDEX IF NOT EXISTS pages_type ON pages(crawl_id,content_type,url);
            CREATE INDEX IF NOT EXISTS external_source ON external_data(crawl_id,source,url);
            CREATE TABLE IF NOT EXISTS observations (
              crawl_id INTEGER NOT NULL REFERENCES crawls(id), url TEXT NOT NULL,
              kind TEXT NOT NULL, status TEXT NOT NULL, data_json TEXT NOT NULL,
              observed_at TEXT NOT NULL, PRIMARY KEY(crawl_id,url,kind)
            );
            CREATE TABLE IF NOT EXISTS rule_registry (
              rule_id TEXT NOT NULL, version INTEGER NOT NULL, severity TEXT NOT NULL,
              review_required INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY(rule_id,version)
            );
            CREATE TABLE IF NOT EXISTS api_usage (
              source TEXT NOT NULL, period TEXT NOT NULL, consumed INTEGER NOT NULL,
              PRIMARY KEY(source,period)
            );
        """)
        self.db.execute("INSERT INTO meta(key,value) VALUES ('schema_version', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(SCHEMA_VERSION),))
        self.commit()

    def close(self):
        self.db.close()

    def commit(self):
        if not self._batch:
            self.db.commit()

    @contextmanager
    def batch(self):
        self._batch += 1
        try:
            yield
        except BaseException:
            self._batch -= 1
            self.db.rollback()
            raise
        else:
            self._batch -= 1
            self.commit()

    def start(self, origin, start_url, limit, config, resume=False):
        if sensitive_url(start_url):
            raise ValueError('start URL contains credentials or sensitive parameters. Choose a public URL')
        config = sanitize(config)
        if resume:
            row = self.db.execute("SELECT * FROM crawls WHERE origin=? AND start_url=? AND status!='complete' ORDER BY id DESC LIMIT 1", (origin, start_url)).fetchone()
            if row:
                if json.loads(row['config_json']) != config or row['crawl_limit'] != limit:
                    raise ValueError("resume configuration differs from the stored crawl")
                self.db.execute("UPDATE queue SET state='pending' WHERE crawl_id=? AND state='processing'", (row['id'],))
                # Re-fetch completed HTML pages without retained bodies. Metadata is not HTML evidence.
                self.db.execute("UPDATE queue SET state='pending' WHERE crawl_id=? AND state='done' AND url IN (SELECT url FROM pages WHERE crawl_id=? AND raw_sha256 IS NOT NULL AND raw_html IS NULL AND rendered_html IS NULL)", (row['id'], row['id']))
                self.db.execute("UPDATE crawls SET status='running' WHERE id=?", (row['id'],))
                self.commit()
                return row['id'], True
        cursor = self.db.execute("INSERT INTO crawls(origin,start_url,started_at,status,crawl_limit,config_json) VALUES (?,?,?,?,?,?)", (origin, start_url, now(), 'running', limit, json.dumps(config, sort_keys=True)))
        self.commit()
        return cursor.lastrowid, False

    def enqueue(self, crawl_id, url, depth, source):
        private = sensitive_url(url)
        self.db.execute("INSERT OR IGNORE INTO queue(crawl_id,url,depth,source,state) VALUES (?,?,?,?,?)", (crawl_id, redact_url(url), depth, 'privacy' if private else source, 'excluded' if private else 'pending'))
        self.commit()

    def next_url(self, crawl_id):
        row = self.db.execute("SELECT * FROM queue WHERE crawl_id=? AND state='pending' ORDER BY depth,url LIMIT 1", (crawl_id,)).fetchone()
        if row:
            self.db.execute("UPDATE queue SET state='processing' WHERE crawl_id=? AND url=?", (crawl_id, row['url']))
            self.commit()
        return row

    def mark(self, crawl_id, url, state):
        self.db.execute("UPDATE queue SET state=? WHERE crawl_id=? AND url=?", (state, crawl_id, url))
        self.commit()

    def save_page(self, crawl_id, url, depth, response=None, raw=None, rendered=None, metadata=None, error=None):
        raw_bytes = raw.encode('utf-8') if raw is not None else None
        rendered_bytes = rendered.encode('utf-8') if rendered is not None else None
        saved_raw = redact_text(raw).encode('utf-8') if raw is not None and self.store_html in ('raw', 'both') else None
        saved_rendered = redact_text(rendered).encode('utf-8') if rendered is not None and self.store_html in ('rendered', 'both') else None
        self.db.execute("""INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            crawl_id, redact_url(url), redact_url(response.url) if response else None, response.status if response else None,
            response.headers.get('content-type') if response else None,
            json.dumps(sanitize(response.headers)) if response else None, json.dumps(sanitize(response.redirects)) if response else None,
            saved_raw, saved_rendered, hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None,
            hashlib.sha256(rendered_bytes).hexdigest() if rendered_bytes else None,
            json.dumps(sanitize(metadata), ensure_ascii=False) if metadata else None, depth, now(), redact_text(error) if error else None))
        self.commit()

    def link(self, crawl_id, source, target, anchor, kind='html'):
        self.db.execute("INSERT OR IGNORE INTO links VALUES (?,?,?,?,?)", (crawl_id, redact_url(source), redact_url(target), redact_text(anchor) if anchor is not None else None, kind))
        self.commit()

    def add_references(self, crawl_id, links, targets):
        with self.batch():
            for source, target, anchor, kind in links:
                self.link(crawl_id, source, target, anchor, kind)
            for url, depth, source in targets:
                self.enqueue(crawl_id, url, depth, source)

    def issue(self, crawl_id, url, rule_id, severity, evidence, source='crawler', state='open'):
        self.db.execute('INSERT OR IGNORE INTO rule_registry VALUES (?,?,?,?)',
                        (rule_id, RULE_VERSION, severity, int('candidate' in rule_id or 'review' in rule_id)))
        self.db.execute("INSERT OR REPLACE INTO issues VALUES (?,?,?,?,?,?,?,?)", (crawl_id, redact_url(url), rule_id, RULE_VERSION, severity, state, json.dumps(sanitize(evidence), ensure_ascii=False), source))
        self.commit()

    def observation(self, crawl_id, url, kind, status, data):
        self.db.execute('INSERT OR REPLACE INTO observations VALUES (?,?,?,?,?,?)',
                        (crawl_id, redact_url(url), kind, status, json.dumps(sanitize(data), ensure_ascii=False), now()))
        self.commit()

    def reserve_quota(self, source, period, amount, limit):
        self.db.execute('INSERT OR IGNORE INTO api_usage VALUES (?,?,0)', (source, period))
        changed = self.db.execute('UPDATE api_usage SET consumed=consumed+? WHERE source=? AND period=? AND consumed+?<=?',
                                  (amount, source, period, amount, limit)).rowcount
        self.commit()
        return bool(changed)

    def external(self, crawl_id, url, source, property_name, period, data):
        self.db.execute("INSERT OR REPLACE INTO external_data VALUES (?,?,?,?,?,?,?)", (crawl_id, redact_url(url), source, redact_text(property_name), period, now(), json.dumps(sanitize(data), ensure_ascii=False)))
        self.commit()

    def resource(self, crawl_id, source_url, kind, response):
        self.resource_record(self.resource_values(crawl_id, source_url, kind, response))

    @staticmethod
    def resource_values(crawl_id, source_url, kind, response):
        return (
            crawl_id, redact_url(response.url), redact_url(source_url), kind, response.status,
            response.headers.get('content-type'), json.dumps(sanitize(response.headers)),
            hashlib.sha256(response.body).hexdigest(), len(response.body), now())

    def resource_record(self, values):
        self.db.execute('INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,?,?,?,?,?)', values)
        self.commit()

    def count(self, crawl_id):
        return self.db.execute("SELECT COUNT(*) FROM queue WHERE crawl_id=? AND state IN ('done','error')", (crawl_id,)).fetchone()[0]

    def pending(self, crawl_id):
        return self.db.execute("SELECT COUNT(*) FROM queue WHERE crawl_id=? AND state='pending'", (crawl_id,)).fetchone()[0]

    def bytes_used(self, crawl_id):
        return self.db.execute("SELECT COALESCE(SUM(COALESCE(length(raw_html),0)+COALESCE(length(rendered_html),0)),0) FROM pages WHERE crawl_id=?", (crawl_id,)).fetchone()[0]

    def disk_bytes(self):
        return sum(path.stat().st_size for path in (self.path, Path(str(self.path) + '-wal'), Path(str(self.path) + '-shm')) if path.exists())

    def finish(self, crawl_id, complete, warnings):
        self.db.execute("UPDATE crawls SET status=?, finished_at=?, warnings_json=? WHERE id=?", ('complete' if complete else 'interrupted', now(), json.dumps(sanitize(warnings)), crawl_id))
        self.commit()

    def protect(self, crawl_id, locked):
        if not self.db.execute('SELECT id FROM crawls WHERE id=?', (crawl_id,)).fetchone():
            raise ValueError('crawl not found')
        self.db.execute("INSERT INTO meta(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f'protected:{crawl_id}', str(int(locked))))
        self.commit()

    def retention(self, days, apply=False, reference=None):
        if type(days) is not int or days < 1:
            raise ValueError('retention days must be a positive integer')
        cutoff = ((reference or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()
        selected = [row[0] for row in self.db.execute("SELECT id FROM crawls WHERE status='complete' AND finished_at < ? AND NOT EXISTS (SELECT 1 FROM meta WHERE key='protected:' || crawls.id AND value='1') ORDER BY id", (cutoff,))]
        if apply:
            with self.batch():
                for crawl in selected:
                    for table in ('queue', 'pages', 'links', 'issues', 'external_data', 'resources', 'observations'):
                        self.db.execute(f'DELETE FROM {table} WHERE crawl_id=?', (crawl,))
                    self.db.execute('DELETE FROM crawls WHERE id=?', (crawl,))
                    self.db.execute('DELETE FROM meta WHERE key=?', (f'protected:{crawl}',))
            self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        return {'days': days, 'cutoff': cutoff, 'crawl_ids': selected, 'applied': apply}
