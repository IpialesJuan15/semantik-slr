import json
import sqlite3
from contextlib import contextmanager


@contextmanager
def connect(path):
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, question TEXT NOT NULL,
          inclusion TEXT NOT NULL, exclusion TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL REFERENCES reviews(id),
          identity TEXT NOT NULL, title TEXT NOT NULL, abstract TEXT NOT NULL DEFAULT '',
          doi TEXT NOT NULL DEFAULT '', year INTEGER, authors TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, is_oa INTEGER NOT NULL DEFAULT 0,
          decision TEXT NOT NULL DEFAULT 'pending', reason TEXT NOT NULL DEFAULT '',
          score REAL, analysis TEXT, analyzed_version INTEGER,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
          UNIQUE(review_id, identity));
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL REFERENCES reviews(id),
          kind TEXT NOT NULL, payload TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, review_id INTEGER NOT NULL REFERENCES reviews(id),
          status TEXT NOT NULL, engine TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL REFERENCES reviews(id),
          version INTEGER NOT NULL, snapshot TEXT NOT NULL, sha256 TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
          UNIQUE(review_id, version));
        CREATE TABLE IF NOT EXISTS published_bases (
          review_id INTEGER PRIMARY KEY REFERENCES reviews(id),
          doi TEXT NOT NULL, snapshot TEXT NOT NULL,
          confirmed INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS article_documents (
          article_id INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
          source_type TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '',
          filename TEXT NOT NULL DEFAULT '', sha256 TEXT NOT NULL,
          page_count INTEGER NOT NULL, characters INTEGER NOT NULL,
          truncated INTEGER NOT NULL DEFAULT 0, pages_json TEXT NOT NULL,
          pdf BLOB NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS document_reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
          protocol_version INTEGER NOT NULL, document_sha256 TEXT NOT NULL,
          model TEXT NOT NULL, result_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS base_documents (
          review_id INTEGER PRIMARY KEY REFERENCES reviews(id) ON DELETE CASCADE,
          filename TEXT NOT NULL, sha256 TEXT NOT NULL, page_count INTEGER NOT NULL,
          characters INTEGER NOT NULL, truncated INTEGER NOT NULL DEFAULT 0,
          pages_json TEXT NOT NULL, pdf BLOB NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        CREATE TABLE IF NOT EXISTS base_extractions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
          document_sha256 TEXT NOT NULL, model TEXT NOT NULL, result_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
        ''')
        existing = {row['name'] for row in db.execute('PRAGMA table_info(reviews)')}
        for name, definition in {
            'protocol_version': 'INTEGER NOT NULL DEFAULT 1',
            'base_reference': "TEXT NOT NULL DEFAULT ''",
            'base_text': "TEXT NOT NULL DEFAULT ''",
            'base_filename': "TEXT NOT NULL DEFAULT ''",
            'search_query': "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in existing:
                db.execute(f'ALTER TABLE reviews ADD COLUMN {name} {definition}')
        article_columns = {row['name'] for row in db.execute('PRAGMA table_info(articles)')}
        if 'decision_version' not in article_columns:
            db.execute('ALTER TABLE articles ADD COLUMN decision_version INTEGER')
        db.execute("UPDATE jobs SET status='failed',error='El servidor se reinició. Ejecuta el análisis otra vez.' WHERE status='running'")


def event(db, review_id, kind, payload):
    db.execute('INSERT INTO events (review_id,kind,payload) VALUES (?,?,?)', (review_id, kind, json.dumps(payload, ensure_ascii=False)))


def article_json(row):
    result = dict(row)
    result['is_oa'] = bool(result['is_oa'])
    result['analysis'] = json.loads(result['analysis']) if result['analysis'] else None
    return result
