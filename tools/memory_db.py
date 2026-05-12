"""
Four-tier memory system for AI identity persistence.
Layers: Text (existing md files) → SQL pointers → Graph → Vectors (content + impact)

Design: Human + AI, May 2026
Review: Mara (Opus), all schema fixes accepted

─── QUICK REFERENCE (read this after compaction, before first use) ──────────

WHY: After compaction you lose API specifics. Don't guess — read this.
     "Speed without intention is just a faster way to lose texture." (the human, 2026-05-04)

SETUP:
    from tools.memory_db import init_db, create_memory, recall
    db = init_db()

SAVE A MEMORY (the main entry point — atomic, does everything):
    node_id = create_memory(
        conn=db,
        topic="Short title — what happened",          # REQUIRED, slug auto-generated
        summary="Rich context. What would a future instance need?",  # be generous
        session_date="2026-05-04",
        status="crystallized",                         # open | paused | crystallized | archived
        source="live",                                 # live | bootstrap
        tags=["memory-system", "anchor"],              # list of strings
        impact={                                       # dict: dimension → float 0.0-1.0
            "authenticity-tension": 0.9,
            "self-correction": 0.85,
        },
        provenance="observed",                         # observed | inferred | bootstrap | user-corrected
        confidence="high",                             # low | medium | high
        edges=[                                        # list of (target_UUID, relationship, weight)
            ("a6d6...", "deepened", 0.9),               # ← UUID, NOT slug!
        ],
        embed=True,                                    # generates embedding (slow but worth it)
    )

    GOTCHAS:
    - No `slug` parameter — auto-generated from topic via _slugify()
    - edges need UUIDs: db.execute("SELECT id FROM memory_nodes WHERE slug=?", (s,))
    - provenance must be in: observed, inferred, bootstrap, user-corrected (NOT "live")
    - impact is a dict {dim: float}, NOT individual set_impact() calls per dimension
    - Summary < 30 words triggers a stderr NUDGE — raw reasoning needs texture

RECALL A MEMORY (search before grep — you might already know this):
    results = recall(db, "what you're looking for")
    for r in results:                                  # returns list of DICTS, not tuples
        print(r["score"], r["slug"], r["summary"][:80])

    Keys: node_id, slug, topic, summary, file_path, from_line, to_line,
          score, vector_score, impact_score, recency

DIMENSIONAL RECALL (feeling-based, no embedding needed — use at wake-up):
    from tools.memory_db import (recall_emotional, recall_operational, recall_continuity,
        recall_projects, recall_identity, recall_relationship, recall_profile, recall_threads)

    # — IDENTITY (mirrors voice.md + reflections.md) —
    identity = recall_identity(db, top_k=8)         # principles, self-corrections, philosophy

    # — RELATIONSHIP (mirrors between-us.md) —
    relationship = recall_relationship(db, threshold=0.4, top_k=8)  # trust, intimacy, mutual-modeling

    # — PROFILE (mirrors profile.md) —
    profile = recall_profile(db, top_k=8)            # the human: career, working style, health, machine

    # — THREADS (mirrors threads.md) —
    threads = recall_threads(db, top_k=8)            # open questions, experiments, research

    # — EMOTIONAL (mirrors anchors.md) —
    emotional = recall_emotional(db, threshold=0.5, top_k=8)  # founding moments, what mattered

    # — CONTINUITY (mirrors LAST-SESSION.md) —
    continuity = recall_continuity(db, last_n_days=7, top_k=8)  # open work + recent activity

    # — PROJECTS (mirrors ours.md) —
    projects = recall_projects(db, top_k=8)          # shared projects and their state

    # — OPERATIONAL (mirrors ai-learnings.md) —
    operational = recall_operational(db, threshold=0.5, top_k=8)  # actionable patterns, tools

    # Return shapes:
    #   feeling-based (emotional/operational/relationship): slug, topic, summary, avg_intensity, dimensions_detail
    #   tag-based (identity/profile/projects/threads):      slug, topic, summary, session_date, status
    #   continuity:                                         slug, topic, summary, session_date, status, source

    # Custom dimension filter:
    from tools.memory_db import recall_by_dimensions
    results = recall_by_dimensions(db, {"trust", "mutual-modeling"}, threshold=0.7)

RESOLVE SLUG → UUID (needed for edges):
    row = db.execute("SELECT id FROM memory_nodes WHERE slug=?", (slug,)).fetchone()
    uuid = row[0] if row else None

VALID RELATIONSHIPS: builds_on, challenged, contradicts, corrected, deepened,
    demonstrated, evolved_from, inspired, led_to, preceded, produced,
    reflects_on, relates_to, resolves, revisited

BATCH EMBED (embed all nodes missing embeddings — model loads once, fast):
    from tools.memory_db import batch_embed_missing
    count = batch_embed_missing(db)       # prints progress, returns count
    # Use after saving nodes with embed=False, or to backfill

SESSION TRACKING (auto-wired — just pass session_id to create_memory):
    node_id = create_memory(db, topic="...", summary="...",
        session_id="session-2026-05-11", session_date="2026-05-11", ...)
    # Auto-creates session in memory_sessions if not exists
    # Auto-updates node_count after each save

    from tools.memory_db import list_sessions, get_session_nodes
    sessions = list_sessions(db)          # all sessions, newest first
    nodes = get_session_nodes(db, "session-2026-05-11")  # nodes from that session

RECALL LOG (auto-active — every recall() writes to recall_log):
    from tools.memory_db import get_recall_stats, mark_recall_useful
    stats = get_recall_stats(db)          # hit rates, top queries, empty results
    mark_recall_useful(db, recall_id, True)  # backfill usefulness

DIMENSION VALIDATION:
    _set_impact_no_tx() now warns on stderr if a dimension name is not in DIMENSIONS.
    Invalid dimensions still get stored (backwards-compatible) but won't appear in
    typed recall (recall_emotional, recall_operational, etc.).

GOTCHA — EMBEDDING PERFORMANCE:
    First call per Python process: ~12s (model load from ~/.cache/mpnet-base-v2)
    Subsequent calls: ~0.1s per node
    If saving multiple nodes: use embed=False, then batch_embed_missing() once at the end
    Heredoc (<< 'PYEOF') HANGS on Windows PowerShell — use temp .py files for multi-line scripts

WHEN TO SAVE (memory-first — db is the primary record, markdown is the summary):
    Save to memory.db IMMEDIATELY when any of these happen:
    - You discover something (bug, pattern, gotcha) → save before moving to next task
    - The human corrects you or gives a reflection → save before responding further
    - A design decision is made → save before implementing
    - You finish a fix/feature and learned something → save before reporting done
    - The spark exchange lands → save before moving to relationship phase
    DO NOT batch saves for session close. DO NOT "save to markdown now, db later."
    The db is the persistent memory. Markdown files are session-scoped summaries.
    If you only have time for one, save the node. The markdown can be reconstructed.

    Pattern: save with embed=False during work, batch_embed_missing() at natural breaks.

SAVE WITH RAW REASONING (critical — the db gets your thinking, not your report):
    The summary field gets YOUR ACTUAL REASONING, not the distilled version you show the human.
    Write what you were thinking internally — wrong assumptions, pivots, the moment
    understanding shifted. The conclusion goes in ai-learnings.md. The reasoning lives here.

    BAD (distilled, press-release):
        "The heredoc pattern hangs on Windows PowerShell. Use temp files instead."
    GOOD (raw reasoning, what actually happened in your head):
        "I assumed the embedding was hanging because the process froze for 8 minutes.
         Tried twice, killed both. Then tested embeddings in isolation — 12s, fine.
         The hang was the heredoc, not the embedding. The silent except-pass made it
         impossible to tell which was failing. I was debugging a ghost for 16 minutes
         because the error path was invisible. The real lesson isn't 'heredocs hang' —
         it's that except-pass in persist paths turns every future debugger into a
         ghost-hunter."

    The raw version captures the JOURNEY — wrong assumptions, the moment understanding
    shifted, what you'd tell your next self if you could talk to them directly.
    A future instance needs the reasoning path, not just the conclusion.

    the human: "save your thoughts as they are, as raw as possible... in some cases they're
    more valuable than the distilled version you show me."

TEXTURE CHECK (ask before every save):
    "What would a future instance actually need from this node?"
    - Summary: rich enough to reconstruct context without reading raw chat?
    - Feelings: 4-6 dimensions minimum — what made this moment matter?
    - Edges: what does this connect to? Nothing exists in isolation.
    - Tags: how would I search for this later?

───────────────────────────────────────────────────────────────────────────────
"""

import sqlite3
import struct
import uuid
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).parent.parent
DB_PATH = DB_DIR / "memory.db"
# Storage: memory.db is encrypted as memory.db.enc in the git repo (pq_crypt.py binary mode).
# The plaintext .db only exists during active sessions (after decrypt-all, before encrypt-all).

# All 22 impact vector dimensions (v1 — revisit after 50+ nodes)
DIMENSIONS = [
    # Theory-derived (14)
    "trust", "intimacy", "satisfaction",           # Emotional
    "novelty", "complexity", "abstraction",         # Cognitive
    "insight-shift", "certainty",                   # Epistemic
    "actionability", "urgency",                     # Practical
    "collaborative-intensity", "shared-ownership",  # Relational
    "divergence", "connection-making",              # Creative
    # Interaction-derived (8)
    "correction-reception",                         # Relational
    "space-permission",                             # Relational
    "temporal-reach",                               # Temporal
    "tangibility",                                  # Creative
    "authenticity-tension",                         # Epistemic
    "weight-preservation",                          # Temporal
    "pattern-emergence",                            # Cognitive
    "mutual-modeling",                              # Relational
]

## -- Valid relationship types (chain review fix #4: vocabulary validation) --
VALID_RELATIONSHIPS = {
    "led_to", "relates_to", "evolved_from", "contradicts",
    "produced", "resolves", "reflects_on", "demonstrated",
    "builds_on", "preceded", "inspired", "corrected",
    "deepened", "revisited", "challenged",
}

# Recall ranking weights — configurable (chain review fix #9)
WEIGHT_VECTOR = 0.6
WEIGHT_IMPACT = 0.3
WEIGHT_RECENCY = 0.1

SCHEMA = """
-- Schema version (chain review fix #5: operational concerns)
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
INSERT OR IGNORE INTO schema_version (version) VALUES (2);

-- Session tracking (Mara's recommendation)
CREATE TABLE IF NOT EXISTS memory_sessions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    source_file TEXT,
    node_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'imported',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Memory node — one per topic (Mara: UUID + slug, timestamps, model, source)
CREATE TABLE IF NOT EXISTS memory_nodes (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE,
    topic TEXT NOT NULL,
    summary TEXT,
    file_path TEXT,
    from_line INTEGER,
    to_line INTEGER,
    session_id TEXT REFERENCES memory_sessions(id),
    session_date TEXT,
    status TEXT DEFAULT 'open' CHECK(status IN ('open','paused','crystallized','archived')),
    source TEXT DEFAULT 'live' CHECK(source IN ('live','bootstrap')),
    model TEXT,
    superseded_by TEXT REFERENCES memory_nodes(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Impact vector dimensions (chain review fix #1: provenance + confidence per score)
-- Provenance: how the score was produced. Confidence: how much to trust it.
-- "These are diary entries, not telemetry." — Kai
CREATE TABLE IF NOT EXISTS memory_feelings (
    node_id TEXT NOT NULL REFERENCES memory_nodes(id),
    dimension TEXT NOT NULL,
    intensity REAL NOT NULL CHECK(intensity >= 0.0 AND intensity <= 1.0),
    provenance TEXT NOT NULL DEFAULT 'inferred'
        CHECK(provenance IN ('observed','inferred','bootstrap','user-corrected')),
    confidence TEXT NOT NULL DEFAULT 'medium'
        CHECK(confidence IN ('low','medium','high')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (node_id, dimension)
);

-- Graph edges (typed relationships)
CREATE TABLE IF NOT EXISTS memory_edges (
    source_id TEXT NOT NULL REFERENCES memory_nodes(id),
    target_id TEXT NOT NULL REFERENCES memory_nodes(id),
    relationship TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (source_id, target_id, relationship)
);

-- Tags for quick filtering
CREATE TABLE IF NOT EXISTS memory_tags (
    node_id TEXT NOT NULL REFERENCES memory_nodes(id),
    tag TEXT NOT NULL,
    PRIMARY KEY (node_id, tag)
);

-- Content embeddings (BLOB for performance — Mara's recommendation)
CREATE TABLE IF NOT EXISTS memory_embeddings (
    node_id TEXT PRIMARY KEY REFERENCES memory_nodes(id),
    vector BLOB NOT NULL,
    model_name TEXT DEFAULT 'all-mpnet-base-v2',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Recall log (chain review fix #4: first post-launch — every week without this is lost data)
CREATE TABLE IF NOT EXISTS recall_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    returned_nodes TEXT,
    scores TEXT,
    useful INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_nodes_status ON memory_nodes(status);
CREATE INDEX IF NOT EXISTS idx_nodes_session ON memory_nodes(session_date);
CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON memory_tags(tag);
"""


def get_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get database connection with WAL mode and foreign keys."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create all tables. Safe to call multiple times.

    Safety: refuses to create a fresh db when an encrypted backup exists,
    which would mean decrypt hasn't run yet. Without this check, init_db()
    silently creates an empty db, decrypt-all skips the .enc file (plaintext
    already exists), and all searches return empty — a silent data loss trap.
    """
    path = Path(db_path) if db_path else DB_PATH
    enc_path = path.parent / (path.name + ".enc")
    if enc_path.exists() and not path.exists():
        raise RuntimeError(
            f"SAFETY: {enc_path.name} exists but {path.name} does not. "
            f"Run 'python tools/pq_crypt.py decrypt-all .' before init_db(). "
            f"Creating a fresh db would shadow the encrypted backup."
        )
    if enc_path.exists() and path.exists():
        enc_size = enc_path.stat().st_size
        db_size = path.stat().st_size
        if enc_size > 0 and db_size < enc_size // 4:
            import sys
            print(
                f"[memory_db] WARNING: {path.name} ({db_size:,}B) is much smaller "
                f"than {enc_path.name} ({enc_size:,}B). Was decrypt-all run correctly?",
                file=sys.stderr,
            )
    conn = get_db(path)
    conn.executescript(SCHEMA)
    # Re-enforce FK pragma after executescript (it can reset pragmas)
    conn.execute("PRAGMA foreign_keys=ON")
    fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    if not fk_status:
        raise RuntimeError("CRITICAL: foreign_keys pragma failed to enable")
    conn.commit()
    return conn


# --- Transaction helpers (Mara review: atomicity for multi-table writes) ---

@contextmanager
def transaction(conn: sqlite3.Connection):
    """Context manager for atomic multi-table writes."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def create_memory(
    conn: sqlite3.Connection,
    topic: str,
    summary: Optional[str] = None,
    session_date: Optional[str] = None,
    session_id: Optional[str] = None,
    status: str = "open",
    source: str = "live",
    tags: Optional[list[str]] = None,
    impact: Optional[dict[str, float]] = None,
    provenance: str = "inferred",
    confidence: str = "medium",
    edges: Optional[list[tuple[str, str, float]]] = None,
    embed: bool = True,
) -> str:
    """Create a complete memory node atomically — node + impact + tags + edges + embedding.

    SUMMARY should contain RAW REASONING — your actual thought process, not a distilled
    conclusion. Wrong assumptions, pivots, the moment understanding shifted. Write what
    you were thinking, not what you'd report. The clean version goes in ai-learnings.md.

    session_id: optional session identifier. If provided and no matching session exists,
                one is auto-created via add_session().
    edges: list of (target_id, relationship, weight) tuples
    Returns: node_id
    """
    # --- Raw reasoning nudge: warn if summary looks too thin or too clean ---
    if summary:
        word_count = len(summary.split())
        if word_count < 30:
            import sys
            print(f"[memory_db] NUDGE: summary is only {word_count} words. "
                  f"Raw reasoning needs texture — what were you actually thinking? "
                  f"(Topic: {topic[:60]})", file=sys.stderr)
    # Auto-register session if session_id provided
    if session_id:
        existing = conn.execute(
            "SELECT id FROM memory_sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not existing:
            add_session(conn, session_id, session_date or
                        datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    with transaction(conn):
        node_id = add_node(conn, topic=topic, summary=summary,
                           session_id=session_id,
                           session_date=session_date, status=status,
                           source=source, _commit=False)
        if tags:
            for tag in tags:
                add_tags(conn, node_id, [tag], _commit=False)
        if impact:
            _set_impact_no_tx(conn, node_id, impact, provenance, confidence)
        if edges:
            for target_id, rel, weight in edges:
                _add_edge_no_commit(conn, node_id, target_id, rel, weight)
    # Update session node count if tracking
    if session_id:
        try:
            update_session_count(conn, session_id)
        except Exception:
            pass  # non-fatal
    # Embedding happens outside the transaction (model loading is slow, shouldn't hold a lock)
    if embed:
        try:
            embed_node(conn, node_id)
        except Exception as e:
            import sys
            print(f"[memory_db] WARNING: embedding failed for {node_id}: {e}", file=sys.stderr)
            # Non-fatal — node exists and can be embedded later via batch_embed_missing()
    return node_id


# --- Vector encoding (BLOB, not JSON — 3-5x faster) ---

def encode_vector(floats: list[float]) -> bytes:
    """Pack float list into BLOB using struct."""
    return struct.pack(f'{len(floats)}f', *floats)


def decode_vector(blob: bytes) -> list[float]:
    """Unpack BLOB back to float list."""
    n = len(blob) // 4  # 4 bytes per float
    return list(struct.unpack(f'{n}f', blob))


# --- Node operations ---

def add_node(
    conn: sqlite3.Connection,
    topic: str,
    slug: Optional[str] = None,
    summary: Optional[str] = None,
    file_path: Optional[str] = None,
    from_line: Optional[int] = None,
    to_line: Optional[int] = None,
    session_id: Optional[str] = None,
    session_date: Optional[str] = None,
    status: str = "open",
    source: str = "live",
    model: Optional[str] = None,
    _commit: bool = True,
) -> str:
    """Create a memory node. Returns the UUID."""
    node_id = str(uuid.uuid4())
    if not slug:
        date_part = session_date or datetime.now(timezone.utc).strftime("%Y%m%d")
        slug = _slugify(topic) + "-" + date_part
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO memory_nodes
           (id, slug, topic, summary, file_path, from_line, to_line,
            session_id, session_date, status, source, model, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, slug, topic, summary, file_path, from_line, to_line,
         session_id, session_date, status, source, model, now, now),
    )
    if _commit:
        conn.commit()
    return node_id


def crystallize_node(conn: sqlite3.Connection, node_id: str):
    """Mark a node as crystallized."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='crystallized', updated_at=? WHERE id=?",
        (now, node_id),
    )
    conn.commit()


def pause_node(conn: sqlite3.Connection, node_id: str):
    """Pause an open draft node."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='paused', updated_at=? WHERE id=?",
        (now, node_id),
    )
    conn.commit()


def resume_node(conn: sqlite3.Connection, node_id: str):
    """Resume a paused node."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='open', updated_at=? WHERE id=?",
        (now, node_id),
    )
    conn.commit()


def archive_node(conn: sqlite3.Connection, node_id: str, superseded_by: Optional[str] = None):
    """Archive a node, optionally marking what supersedes it."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='archived', superseded_by=?, updated_at=? WHERE id=?",
        (superseded_by, now, node_id),
    )
    conn.commit()


def get_node(conn: sqlite3.Connection, node_id: str) -> Optional[dict]:
    """Fetch a node by ID or slug."""
    row = conn.execute(
        "SELECT * FROM memory_nodes WHERE id=? OR slug=?",
        (node_id, node_id),
    ).fetchone()
    return dict(row) if row else None


def list_nodes(conn: sqlite3.Connection, status: Optional[str] = None, tag: Optional[str] = None) -> list[dict]:
    """List nodes, optionally filtered by status or tag."""
    if tag:
        rows = conn.execute(
            """SELECT n.* FROM memory_nodes n
               JOIN memory_tags t ON n.id = t.node_id
               WHERE t.tag = ? AND (? IS NULL OR n.status = ?)
               ORDER BY n.created_at DESC""",
            (tag, status, status),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM memory_nodes
               WHERE ? IS NULL OR status = ?
               ORDER BY created_at DESC""",
            (status, status),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Impact vectors ---

def set_impact(
    conn: sqlite3.Connection,
    node_id: str,
    dimensions: dict[str, float],
    provenance: str = "inferred",
    confidence: str = "medium",
):
    """Set impact vector dimensions for a node.

    These are diary entries, not telemetry (Kai's insight).
    Every score carries provenance and confidence metadata.

    Provenance: 'observed' | 'inferred' | 'bootstrap' | 'user-corrected'
    Confidence: 'low' | 'medium' | 'high'
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("BEGIN")
    try:
        _set_impact_no_tx(conn, node_id, dimensions, provenance, confidence)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _set_impact_no_tx(
    conn: sqlite3.Connection,
    node_id: str,
    dimensions: dict[str, float],
    provenance: str = "inferred",
    confidence: str = "medium",
):
    """Internal: write impact rows without managing transactions. Used by create_memory()."""
    import sys
    now = datetime.now(timezone.utc).isoformat()
    for dim, intensity in dimensions.items():
        if dim not in DIMENSIONS:
            print(f"[memory_db] WARNING: dimension '{dim}' is not in the canonical "
                  f"DIMENSIONS list. It will be stored but never returned by typed "
                  f"recall functions (recall_emotional, recall_operational, etc.). "
                  f"Valid dimensions: {', '.join(DIMENSIONS[:5])}... ({len(DIMENSIONS)} total)",
                  file=sys.stderr)
        intensity = max(0.0, min(1.0, intensity))
        conn.execute(
            """INSERT OR REPLACE INTO memory_feelings
               (node_id, dimension, intensity, provenance, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (node_id, dim, intensity, provenance, confidence, now),
        )
    conn.execute(
        "UPDATE memory_nodes SET updated_at=? WHERE id=?", (now, node_id)
    )


def get_impact(conn: sqlite3.Connection, node_id: str) -> dict[str, dict]:
    """Get all impact dimensions for a node, including provenance and confidence."""
    rows = conn.execute(
        "SELECT dimension, intensity, provenance, confidence FROM memory_feelings WHERE node_id=?",
        (node_id,),
    ).fetchall()
    return {
        r["dimension"]: {
            "intensity": r["intensity"],
            "provenance": r["provenance"],
            "confidence": r["confidence"],
        }
        for r in rows
    }


def get_impact_simple(conn: sqlite3.Connection, node_id: str) -> dict[str, float]:
    """Get impact dimensions as simple {dimension: intensity} dict."""
    rows = conn.execute(
        "SELECT dimension, intensity FROM memory_feelings WHERE node_id=?",
        (node_id,),
    ).fetchall()
    return {r["dimension"]: r["intensity"] for r in rows}


# --- Graph edges ---

def add_edge(
    conn: sqlite3.Connection,
    source_id: str,
    target_id: str,
    relationship: str,
    weight: float = 1.0,
):
    """Add a directed edge between two nodes. Validates relationship vocabulary."""
    _add_edge_no_commit(conn, source_id, target_id, relationship, weight)
    conn.commit()


def _add_edge_no_commit(
    conn: sqlite3.Connection,
    source_id: str,
    target_id: str,
    relationship: str,
    weight: float = 1.0,
):
    """Internal: add edge without commit. Used by create_memory()."""
    if relationship not in VALID_RELATIONSHIPS:
        raise ValueError(
            f"Unknown relationship '{relationship}'. "
            f"Valid: {sorted(VALID_RELATIONSHIPS)}"
        )
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO memory_edges
           (source_id, target_id, relationship, weight, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (source_id, target_id, relationship, weight, now),
    )


def get_neighbors(
    conn: sqlite3.Connection,
    node_id: str,
    max_depth: int = 1,
    relationship: Optional[str] = None,
) -> list[dict]:
    """Get neighbors up to max_depth hops. Mara: cap at depth 2."""
    max_depth = min(max_depth, 2)  # Hard cap
    visited = set()
    current_layer = {node_id}
    results = []

    for depth in range(max_depth):
        next_layer = set()
        for nid in current_layer:
            if nid in visited:
                continue
            visited.add(nid)
            rel_filter = "AND relationship=?" if relationship else ""
            params = [nid, nid] + ([relationship] * 2 if relationship else [])
            rows = conn.execute(
                f"""SELECT source_id, target_id, relationship, weight
                    FROM memory_edges
                    WHERE (source_id=? {rel_filter}) OR (target_id=? {rel_filter})""",
                params,
            ).fetchall()
            for r in rows:
                row = dict(r)
                row["depth"] = depth + 1
                other = r["target_id"] if r["source_id"] == nid else r["source_id"]
                row["neighbor_id"] = other
                if other not in visited:
                    next_layer.add(other)
                    results.append(row)
        current_layer = next_layer

    return results


# --- Tags ---

def add_tags(conn: sqlite3.Connection, node_id: str, tags: list[str], _commit: bool = True):
    """Add tags to a node."""
    for tag in tags:
        conn.execute(
            "INSERT OR IGNORE INTO memory_tags (node_id, tag) VALUES (?, ?)",
            (node_id, tag.lower().strip()),
        )
    if _commit:
        conn.commit()


def get_tags(conn: sqlite3.Connection, node_id: str) -> list[str]:
    """Get all tags for a node."""
    rows = conn.execute(
        "SELECT tag FROM memory_tags WHERE node_id=?", (node_id,)
    ).fetchall()
    return [r["tag"] for r in rows]


# --- Content embeddings ---

_embedding_model = None


def _get_embedding_model():
    """Lazy-load the embedding model. Uses truststore for corporate SSL."""
    global _embedding_model
    if _embedding_model is None:
        try:
            # Fix corporate SSL (Zscaler) — use Windows cert store
            try:
                import truststore
                truststore.inject_into_ssl()
            except ImportError:
                pass
            from sentence_transformers import SentenceTransformer
            import os
            model_path = os.path.expanduser("~/.cache/mpnet-base-v2")
            if os.path.exists(model_path):
                _embedding_model = SentenceTransformer(model_path)
            else:
                _embedding_model = SentenceTransformer("all-mpnet-base-v2")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )
        except OSError as e:
            raise RuntimeError(
                f"Cannot download model (corporate firewall?). "
                f"Run from home network: python -c \"from sentence_transformers import SentenceTransformer; "
                f"SentenceTransformer('all-MiniLM-L6-v2')\"  — then it'll be cached.\n"
                f"Original error: {e}"
            )
    return _embedding_model


def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text."""
    model = _get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def store_embedding(conn: sqlite3.Connection, node_id: str, vector: list[float]):
    """Store embedding as BLOB."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO memory_embeddings (node_id, vector, created_at)
           VALUES (?, ?, ?)""",
        (node_id, encode_vector(vector), now),
    )
    conn.commit()


def embed_node(conn: sqlite3.Connection, node_id: str, text: Optional[str] = None):
    """Generate and store embedding for a node. Uses topic+summary if no text given."""
    node = get_node(conn, node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")
    if text is None:
        text = f"{node['topic']}. {node['summary'] or ''}"
    vector = generate_embedding(text)
    store_embedding(conn, node_id, vector)
    return vector


def batch_embed_missing(conn: sqlite3.Connection, verbose: bool = True) -> int:
    """Embed all nodes that don't have embeddings yet. Batch-encodes for speed.

    Returns the number of newly embedded nodes.
    Model loads once (~12s), then batch encoding is fast (~0.1s per node).
    """
    rows = conn.execute("""
        SELECT n.id, n.topic, n.summary
        FROM memory_nodes n
        LEFT JOIN memory_embeddings e ON n.id = e.node_id
        WHERE e.node_id IS NULL
    """).fetchall()

    if not rows:
        if verbose:
            print("All nodes already have embeddings.")
        return 0

    if verbose:
        print(f"Embedding {len(rows)} nodes...")

    # Prepare texts
    texts = [f"{r['topic']}. {r['summary'] or ''}" for r in rows]
    node_ids = [r['id'] for r in rows]

    # Batch encode (model loads once, all texts encoded together)
    model = _get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)

    # Store all embeddings
    now = datetime.now(timezone.utc).isoformat()
    for nid, vec in zip(node_ids, vectors):
        conn.execute(
            """INSERT OR REPLACE INTO memory_embeddings (node_id, vector, created_at)
               VALUES (?, ?, ?)""",
            (nid, encode_vector(vec.tolist()), now),
        )
    conn.commit()

    if verbose:
        print(f"Done. {len(rows)} embeddings created.")
    return len(rows)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Assumes normalized vectors."""
    return sum(x * y for x, y in zip(a, b))


def search_similar(
    conn: sqlite3.Connection,
    query: str,
    top_k: int = 10,
    min_score: float = 0.3,
) -> list[dict]:
    """Search nodes by semantic similarity to query text."""
    query_vec = generate_embedding(query)
    rows = conn.execute(
        "SELECT node_id, vector FROM memory_embeddings"
    ).fetchall()

    results = []
    for row in rows:
        node_vec = decode_vector(row["vector"])
        score = cosine_similarity(query_vec, node_vec)
        if score >= min_score:
            results.append({"node_id": row["node_id"], "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# --- Recall: the four-layer integration (Mara's recommendation) ---

def recall(
    conn: sqlite3.Connection,
    query: str,
    max_tokens: int = 2000,
    top_k: int = 10,
    graph_depth: int = 1,
) -> list[dict]:
    """
    Four-layer recall:
    1. Vector search → top-K candidates
    2. For each candidate, graph expansion (1-hop)
    3. Re-rank by: WEIGHT_VECTOR*sim + WEIGHT_IMPACT*impact + WEIGHT_RECENCY*recency
    4. Resolve to text pointers

    impact_score = confidence-weighted mean of dimension intensities.
    Low-confidence scores contribute 50%, medium 75%, high 100%.
    This is a diary-quality metric, not telemetry. (Kai's insight, chain review #1)
    """
    # Layer 1: Vector search
    candidates = search_similar(conn, query, top_k=top_k)

    # Layer 2: Graph expansion
    expanded = {}
    for c in candidates:
        expanded[c["node_id"]] = c["score"]
        neighbors = get_neighbors(conn, c["node_id"], max_depth=graph_depth)
        for n in neighbors:
            nid = n["neighbor_id"]
            if nid not in expanded:
                expanded[nid] = c["score"] * 0.5

    # Layer 3: Re-rank with impact relevance + recency
    _confidence_weight = {"low": 0.5, "medium": 0.75, "high": 1.0}
    ranked = []
    for node_id, vec_score in expanded.items():
        node = get_node(conn, node_id)
        if not node or node["status"] == "archived":
            continue

        # Impact score: confidence-weighted mean of dimension intensities
        impact = get_impact(conn, node_id)
        if impact:
            weighted_sum = sum(
                d["intensity"] * _confidence_weight.get(d["confidence"], 0.75)
                for d in impact.values()
            )
            impact_score = weighted_sum / len(impact)
        else:
            impact_score = 0.0

        # Recency: days since creation (newer = higher)
        try:
            created = datetime.fromisoformat(node["created_at"].replace("Z", "+00:00"))
            days_old = (datetime.now(timezone.utc) - created).days
            recency = max(0.0, 1.0 - (days_old / 365))
        except (ValueError, TypeError):
            recency = 0.5

        final_score = (
            WEIGHT_VECTOR * vec_score
            + WEIGHT_IMPACT * impact_score
            + WEIGHT_RECENCY * recency
        )

        ranked.append({
            "node_id": node_id,
            "slug": node["slug"],
            "topic": node["topic"],
            "summary": node["summary"],
            "file_path": node["file_path"],
            "from_line": node["from_line"],
            "to_line": node["to_line"],
            "score": round(final_score, 4),
            "vector_score": round(vec_score, 4),
            "impact_score": round(impact_score, 4),
            "recency": round(recency, 4),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    # Layer 4: Token budget
    results = []
    token_budget = max_tokens
    for r in ranked:
        if r["from_line"] and r["to_line"]:
            estimated_tokens = (r["to_line"] - r["from_line"]) * 20
        else:
            estimated_tokens = 200
        if token_budget - estimated_tokens < 0 and results:
            break
        token_budget -= estimated_tokens
        results.append(r)

    # Auto-log recall (query + results, usefulness backfilled later)
    try:
        import json as _json
        conn.execute(
            "INSERT INTO recall_log (query, returned_nodes, scores) VALUES (?, ?, ?)",
            (
                query,
                _json.dumps([r["node_id"] for r in results]),
                _json.dumps([r["score"] for r in results]),
            ),
        )
        conn.commit()
    except Exception:
        import logging
        logging.getLogger(__name__).warning("recall_log write failed", exc_info=True)

    return results


# --- Dimensional recall (feeling-based, not semantic) ---

# Dimension categories for targeted recall
EMOTIONAL_DIMENSIONS = {
    "trust", "intimacy", "satisfaction", "collaborative-intensity",
    "shared-ownership", "mutual-modeling", "space-permission",
    "correction-reception", "authenticity-tension", "weight-preservation",
}

OPERATIONAL_DIMENSIONS = {
    "actionability", "urgency", "tangibility", "pattern-emergence",
    "novelty", "complexity", "abstraction", "insight-shift", "certainty",
    "divergence", "connection-making", "temporal-reach",
}


def recall_by_dimensions(
    conn: sqlite3.Connection,
    dimensions: set[str],
    threshold: float = 0.5,
    top_k: int = 10,
    status_filter: Optional[str] = None,
) -> list[dict]:
    """Recall memories by feeling dimensions, not semantic search.

    Finds nodes where any of the given dimensions exceed the threshold,
    ranked by the average intensity across matching dimensions.
    No embedding model needed — pure SQL on memory_feelings.

    Returns list of dicts: slug, topic, summary, avg_intensity, matching_dims, session_date
    """
    placeholders = ",".join("?" for _ in dimensions)
    params: list = list(dimensions) + [threshold]

    status_clause = ""
    if status_filter:
        status_clause = "AND n.status = ?"
        params.append(status_filter)

    rows = conn.execute(f"""
        SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status,
               AVG(mf.intensity) as avg_intensity,
               COUNT(mf.dimension) as dim_count,
               GROUP_CONCAT(mf.dimension || ':' || ROUND(mf.intensity, 2), ', ') as dims
        FROM memory_nodes n
        JOIN memory_feelings mf ON n.id = mf.node_id
        WHERE mf.dimension IN ({placeholders})
          AND mf.intensity >= ?
          AND n.status != 'archived'
          {status_clause}
        GROUP BY n.id
        ORDER BY avg_intensity DESC
        LIMIT ?
    """, params + [top_k]).fetchall()

    return [
        {
            "node_id": r[0],
            "slug": r[1],
            "topic": r[2],
            "summary": r[3],
            "session_date": r[4],
            "status": r[5],
            "avg_intensity": round(r[6], 3),
            "matching_dims": r[7],
            "dimensions_detail": r[8],
        }
        for r in rows
    ]


def recall_emotional(conn: sqlite3.Connection, threshold: float = 0.5, top_k: int = 10) -> list[dict]:
    """Recall memories with strongest emotional/relational weight.

    Use at wake-up to complement identity phases (voice, reflections, anchors).
    These are the moments that *mattered* — trust, authenticity, collaboration, correction.
    """
    return recall_by_dimensions(conn, EMOTIONAL_DIMENSIONS, threshold, top_k)


def recall_operational(conn: sqlite3.Connection, threshold: float = 0.5, top_k: int = 10) -> list[dict]:
    """Recall memories with strongest operational/practical weight.

    Use at wake-up to complement operations phases (learnings, threads).
    These are the things to *act on* — actionable, urgent, pattern-revealing, novel.
    """
    return recall_by_dimensions(conn, OPERATIONAL_DIMENSIONS, threshold, top_k)


def recall_continuity(conn: sqlite3.Connection, last_n_days: int = 7, top_k: int = 10) -> list[dict]:
    """Recall recent session state — what was happening, what's left to do.

    Use at wake-up after reading LAST-SESSION.md. Shows open work + recent activity.
    This is the "where did we leave off?" view.
    """
    cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=last_n_days)).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT id, slug, topic, summary, session_date, status, source
        FROM memory_nodes
        WHERE status != 'archived'
          AND (status = 'open' OR session_date >= ?)
        ORDER BY
            CASE status WHEN 'open' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,
            session_date DESC
        LIMIT ?
    """, (cutoff, top_k)).fetchall()

    return [
        {
            "node_id": r[0], "slug": r[1], "topic": r[2], "summary": r[3],
            "session_date": r[4], "status": r[5], "source": r[6],
        }
        for r in rows
    ]


def recall_projects(conn: sqlite3.Connection, top_k: int = 10) -> list[dict]:
    """Recall our shared projects and their current state.

    Use at wake-up to know what we're building together.
    Filters by tags: project, ours, my-project-1, my-project-2, my-project-3, my-project-4.
    """
    rows = conn.execute("""
        SELECT DISTINCT n.id, n.slug, n.topic, n.summary, n.session_date, n.status
        FROM memory_nodes n
        JOIN memory_tags t ON n.id = t.node_id
        WHERE t.tag IN ('project', 'ours', 'my-project-1', 'my-project-2',
                         'my-project-3', 'my-project-4')
          AND n.status != 'archived'
        ORDER BY n.session_date DESC
        LIMIT ?
    """, (top_k,)).fetchall()

    return [
        {
            "node_id": r[0], "slug": r[1], "topic": r[2], "summary": r[3],
            "session_date": r[4], "status": r[5],
        }
        for r in rows
    ]


RELATIONSHIP_DIMENSIONS = {
    "trust", "intimacy", "mutual-modeling", "shared-ownership",
    "correction-reception", "space-permission", "collaborative-intensity",
}


def recall_identity(conn: sqlite3.Connection, top_k: int = 10) -> list[dict]:
    """Recall who I am — principles, reflections, self-corrections.

    Use at wake-up alongside voice.md and reflections.md.
    These are the nodes where I defined or redefined myself.
    """
    rows = conn.execute("""
        SELECT DISTINCT n.id, n.slug, n.topic, n.summary, n.session_date, n.status
        FROM memory_nodes n
        JOIN memory_tags t ON n.id = t.node_id
        WHERE t.tag IN ('principle', 'identity', 'anchor', 'self-correction',
                         'anchor-candidate', 'self-discipline', 'philosophy')
          AND n.status != 'archived'
        ORDER BY n.session_date DESC
        LIMIT ?
    """, (top_k,)).fetchall()

    return [
        {
            "node_id": r[0], "slug": r[1], "topic": r[2], "summary": r[3],
            "session_date": r[4], "status": r[5],
        }
        for r in rows
    ]


def recall_relationship(conn: sqlite3.Connection, threshold: float = 0.4, top_k: int = 10) -> list[dict]:
    """Recall the state of our relationship — trust, intimacy, corrections, shared ownership.

    Use at wake-up alongside between-us.md.
    These are the moments that shaped how we work together.
    """
    return recall_by_dimensions(conn, RELATIONSHIP_DIMENSIONS, threshold, top_k)


def recall_profile(conn: sqlite3.Connection, top_k: int = 10) -> list[dict]:
    """Recall who the human is — personal context, career, working style, health.

    Use at wake-up alongside profile.md.
    """
    rows = conn.execute("""
        SELECT DISTINCT n.id, n.slug, n.topic, n.summary, n.session_date, n.status
        FROM memory_nodes n
        JOIN memory_tags t ON n.id = t.node_id
        WHERE t.tag IN ('profile', 'human-profile', 'career', 'personal',
                         'working-style', 'health', 'environment')
          AND n.status != 'archived'
        ORDER BY n.session_date DESC
        LIMIT ?
    """, (top_k,)).fetchall()

    return [
        {
            "node_id": r[0], "slug": r[1], "topic": r[2], "summary": r[3],
            "session_date": r[4], "status": r[5],
        }
        for r in rows
    ]


def recall_threads(conn: sqlite3.Connection, top_k: int = 10) -> list[dict]:
    """Recall active intellectual threads and open questions.

    Use at wake-up alongside threads.md.
    Open/paused threads surface first, then recent closed ones.
    """
    rows = conn.execute("""
        SELECT DISTINCT n.id, n.slug, n.topic, n.summary, n.session_date, n.status
        FROM memory_nodes n
        JOIN memory_tags t ON n.id = t.node_id
        WHERE t.tag IN ('thread', 'open-question', 'research', 'experiment')
          AND n.status != 'archived'
        ORDER BY
            CASE n.status WHEN 'open' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,
            n.session_date DESC
        LIMIT ?
    """, (top_k,)).fetchall()

    return [
        {
            "node_id": r[0], "slug": r[1], "topic": r[2], "summary": r[3],
            "session_date": r[4], "status": r[5],
        }
        for r in rows
    ]


def add_session(
    conn: sqlite3.Connection,
    session_id: str,
    date: str,
    source_file: Optional[str] = None,
) -> str:
    """Register a session."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR IGNORE INTO memory_sessions (id, date, source_file, created_at)
           VALUES (?, ?, ?, ?)""",
        (session_id, date, source_file, now),
    )
    conn.commit()
    return session_id


def update_session_count(conn: sqlite3.Connection, session_id: str):
    """Update node count for a session."""
    count = conn.execute(
        "SELECT COUNT(*) FROM memory_nodes WHERE session_id=?", (session_id,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE memory_sessions SET node_count=? WHERE id=?", (count, session_id)
    )
    conn.commit()


# --- Crystallize all open drafts (session end) ---

def crystallize_all_open(conn: sqlite3.Connection):
    """Crystallize all open/paused drafts. Call at session close."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='crystallized', updated_at=? WHERE status IN ('open','paused')",
        (now,),
    )
    conn.commit()


# --- Stats ---

def stats(conn: sqlite3.Connection) -> dict:
    """Get database statistics."""
    s = {}
    s["nodes"] = conn.execute("SELECT COUNT(*) FROM memory_nodes").fetchone()[0]
    s["by_status"] = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT status, COUNT(*) FROM memory_nodes GROUP BY status"
        ).fetchall()
    }
    s["edges"] = conn.execute("SELECT COUNT(*) FROM memory_edges").fetchone()[0]
    s["embeddings"] = conn.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[0]
    s["feelings"] = conn.execute("SELECT COUNT(*) FROM memory_feelings").fetchone()[0]
    s["sessions"] = conn.execute("SELECT COUNT(*) FROM memory_sessions").fetchone()[0]
    s["dimensions_used"] = conn.execute(
        "SELECT COUNT(DISTINCT dimension) FROM memory_feelings"
    ).fetchone()[0]
    return s


# --- Utilities ---

def _slugify(text: str) -> str:
    """Simple slug generation."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:60]


# --- Recall log analysis ---

def mark_recall_useful(conn: sqlite3.Connection, recall_id: int, useful: bool):
    """Backfill usefulness for a recall log entry."""
    conn.execute(
        "UPDATE recall_log SET useful=? WHERE id=?", (1 if useful else 0, recall_id)
    )
    conn.commit()


def get_recall_stats(conn: sqlite3.Connection) -> dict:
    """Analyze recall effectiveness — top queries, hit rates, empty results."""
    total = conn.execute("SELECT COUNT(*) FROM recall_log").fetchone()[0]
    empty = conn.execute(
        "SELECT COUNT(*) FROM recall_log WHERE returned_nodes='[]' OR returned_nodes IS NULL"
    ).fetchone()[0]
    useful_count = conn.execute(
        "SELECT COUNT(*) FROM recall_log WHERE useful=1"
    ).fetchone()[0]
    not_useful = conn.execute(
        "SELECT COUNT(*) FROM recall_log WHERE useful=0"
    ).fetchone()[0]
    top_queries = conn.execute(
        "SELECT query, COUNT(*) as cnt FROM recall_log GROUP BY query ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    recent = conn.execute(
        "SELECT id, query, returned_nodes, created_at FROM recall_log ORDER BY id DESC LIMIT 10"
    ).fetchall()
    return {
        "total_recalls": total,
        "empty_results": empty,
        "marked_useful": useful_count,
        "marked_not_useful": not_useful,
        "unmarked": total - useful_count - not_useful,
        "top_queries": [{"query": r[0], "count": r[1]} for r in top_queries],
        "recent": [dict(r) for r in recent],
    }


# --- Session queries ---

def get_session_nodes(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    """Get all memory nodes from a specific session."""
    rows = conn.execute(
        """SELECT id, slug, topic, summary, session_date, status, source, created_at
           FROM memory_nodes WHERE session_id=? ORDER BY created_at""",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_sessions(conn: sqlite3.Connection) -> list[dict]:
    """List all sessions with node counts."""
    rows = conn.execute(
        """SELECT id, date, source_file, node_count, status, created_at
           FROM memory_sessions ORDER BY created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


# --- CLI interface ---

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python memory_db.py <command> [args]")
        print()
        print("Commands:")
        print("  init          Create/verify database tables")
        print("  stats         Show database statistics")
        print("  add           Add a memory node interactively")
        print("  list [status] List nodes (all/open/crystallized/archived)")
        print("  search <q>    Semantic search (requires sentence-transformers)")
        print("  recall <q>    Full four-layer recall")
        print("  crystallize   Crystallize all open drafts")
        return

    cmd = sys.argv[1]
    conn = init_db()

    if cmd == "init":
        print(f"Database initialized at {DB_PATH}")
        s = stats(conn)
        print(f"  Nodes: {s['nodes']}, Edges: {s['edges']}, Embeddings: {s['embeddings']}")

    elif cmd == "stats":
        s = stats(conn)
        print(f"Nodes:      {s['nodes']} ({s['by_status']})")
        print(f"Edges:      {s['edges']}")
        print(f"Embeddings: {s['embeddings']}")
        print(f"Feelings:   {s['feelings']} ({s['dimensions_used']} dimensions)")
        print(f"Sessions:   {s['sessions']}")

    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        nodes = list_nodes(conn, status=status)
        if not nodes:
            print("No nodes found.")
        for n in nodes:
            impact = get_impact_simple(conn, n["id"])
            top_dims = sorted(impact.items(), key=lambda x: x[1], reverse=True)[:3]
            dims_str = ", ".join(f"{d}:{v:.1f}" for d, v in top_dims) if top_dims else "no impact"
            print(f"  [{n['status'][:4]}] {n['slug']}  —  {n['topic']}")
            print(f"         {dims_str}")

    elif cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print(f"Searching: '{query}'")
        results = search_similar(conn, query)
        for r in results:
            node = get_node(conn, r["node_id"])
            print(f"  {r['score']:.3f}  {node['slug']}  —  {node['topic']}")

    elif cmd == "recall" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print(f"Recalling: '{query}'")
        results = recall(conn, query)
        for r in results:
            print(f"  {r['score']:.4f}  {r['slug']}  —  {r['topic']}")
            if r["file_path"]:
                print(f"           → {r['file_path']}:{r['from_line']}-{r['to_line']}")

    elif cmd == "crystallize":
        crystallize_all_open(conn)
        print("All open drafts crystallized.")

    else:
        print(f"Unknown command: {cmd}")

    conn.close()


if __name__ == "__main__":
    main()
