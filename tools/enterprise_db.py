"""
Enterprise knowledge persistence — codebase maps, flows, decisions, edge cases, patterns.
Five-layer system for multi-project technical memory.

Design: Hugo + AI, May 2026
Built on same schema as memory_db.py — separate SQLite file, no personal data.

─── QUICK REFERENCE (read this after compaction, before first use) ──────────

WHY: Technical memory for enterprise projects. Confidential details stay local.
     Cross-project patterns make the next similar project faster.
     "The map of every codebase, not re-discovered every session." (Hugo, 2026-05-05)

SETUP:
    from tools.enterprise_db import init_db, save_enterprise, recall, recall_project
    edb = init_db()                          # creates ~/.copilot/enterprise.db

SAVE A NODE (main entry point):
    node_id = save_enterprise(
        conn=edb,
        topic="Short title — what this is",        # REQUIRED
        summary="Rich technical context...",        # be generous — raw reasoning welcome
        layer="map",                               # REQUIRED: map|flow|edge|decision|pattern
        project="ttn",                             # REQUIRED: slug e.g. ttn, brightstar
        session_date="2026-05-05",
        technical={                                # optional: 0.0-1.0 per dimension
            "confidence": 0.9,                    # how certain is this knowledge?
            "stability": 0.7,                     # how likely to change?
            "reusability": 0.8,                   # how transferable to other projects?
            "complexity": 0.6,                    # how complex/nuanced?
            "criticality": 0.9,                   # how important to get right?
            "discovery-effort": 0.8,              # how hard was it to figure out?
        },
        edges=[                                    # list of (target_UUID, relationship, weight)
            ("a6d6...", "relates_to", 0.9),
        ],
        embed=True,
    )

    LAYERS:
    - map       → structure: modules, components, file locations, relationships
    - flow      → behavior: transactions, data flows, build processes, happy paths
    - edge      → gotchas: constraints, known issues, things that break assumptions
    - decision  → why: deliberate choices, tradeoffs, rejected alternatives
    - pattern   → transfer: cross-project generalizations, reusable solutions

    GOTCHAS (same as memory_db):
    - No `slug` param — auto-generated from topic
    - edges need UUIDs: edb.execute("SELECT id FROM memory_nodes WHERE slug=?", (s,))
    - provenance must be: observed | inferred | bootstrap | user-corrected
    - embed=False + batch_embed_missing() at end is faster for bulk saves

LOAD PROJECT CONTEXT (at session start):
    nodes = recall_project(edb, "ttn")           # all nodes for project
    nodes = recall_project(edb, "ttn", layer="edge")  # just gotchas for ttn

SEMANTIC SEARCH (across all projects or filtered):
    results = recall(edb, "device status registration")
    results = recall(edb, "legacy bridge pattern", project="ttn")

STATUS LIFECYCLE (track JIRA resolution, project completion, etc.):
    update_status(edb, node_id_or_slug, "crystallized")  # resolved/done
    update_status(edb, node_id_or_slug, "archived")      # stale/superseded
    update_status(edb, node_id_or_slug, "paused")        # blocked/waiting

    # Statuses: open (default) → paused | crystallized → archived

WHAT'S PENDING? (after compaction or session start):
    from tools.enterprise_db import recall_open
    pending = recall_open(edb, project="ttn")   # open + paused nodes for project
    pending = recall_open(edb)                   # all open/paused across projects

LAYER RECALL (browse by type, no embedding needed):
    maps      = recall_map(edb, project="ttn")
    flows     = recall_flow(edb, project="ttn")
    gotchas   = recall_edge(edb, project="ttn")
    decisions = recall_decision(edb, project="ttn")
    patterns  = recall_pattern(edb)              # patterns are cross-project by nature

STATS:
    from tools.enterprise_db import stats
    s = stats(edb)
    # Keys: total_nodes, by_project (dict), by_layer (dict), missing_embeddings, projects_list

RESOLVE SLUG → UUID (needed for edges):
    row = edb.execute("SELECT id FROM memory_nodes WHERE slug=?", (slug,)).fetchone()
    uuid = row[0] if row else None

VALID RELATIONSHIPS (same as memory_db):
    builds_on, challenged, contradicts, corrected, deepened,
    demonstrated, evolved_from, inspired, led_to, preceded, produced,
    reflects_on, relates_to, resolves, revisited

PERFORMANCE (same model as memory_db):
    First embed call per process: ~12s (model load from ~/.cache/mpnet-base-v2)
    Subsequent: ~0.1s per node
    Bulk saves: use embed=False, then batch_embed_missing(edb) once at end
    Heredoc (<< 'PYEOF') HANGS on Windows PowerShell — use temp .py files

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

DB_PATH = Path.home() / ".copilot" / "enterprise.db"

# Technical metadata dimensions (replaces emotional dimensions from memory_db)
TECHNICAL_DIMENSIONS = [
    "confidence",       # how certain is this knowledge? (0=uncertain, 1=verified)
    "stability",        # how likely to change? (0=volatile, 1=stable)
    "reusability",      # how transferable to other projects? (0=project-specific, 1=universal)
    "complexity",       # how complex/nuanced? (0=simple, 1=very complex)
    "criticality",      # how important to get right? (0=minor, 1=critical)
    "discovery-effort", # how hard was it to figure out? (0=obvious, 1=required deep investigation)
]

VALID_LAYERS = {"map", "flow", "edge", "decision", "pattern"}

VALID_RELATIONSHIPS = {
    "led_to", "relates_to", "evolved_from", "contradicts",
    "produced", "resolves", "reflects_on", "demonstrated",
    "builds_on", "preceded", "inspired", "corrected",
    "deepened", "revisited", "challenged",
}

WEIGHT_VECTOR = 0.6
WEIGHT_TECHNICAL = 0.25
WEIGHT_RECENCY = 0.15

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS memory_nodes (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE,
    topic TEXT NOT NULL,
    summary TEXT,
    session_date TEXT,
    status TEXT DEFAULT 'open' CHECK(status IN ('open','paused','crystallized','archived')),
    source TEXT DEFAULT 'live' CHECK(source IN ('live','bootstrap')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Technical metadata (replaces memory_feelings — no emotions, just quality signals)
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

CREATE TABLE IF NOT EXISTS memory_edges (
    source_id TEXT NOT NULL REFERENCES memory_nodes(id),
    target_id TEXT NOT NULL REFERENCES memory_nodes(id),
    relationship TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (source_id, target_id, relationship)
);

CREATE TABLE IF NOT EXISTS memory_tags (
    node_id TEXT NOT NULL REFERENCES memory_nodes(id),
    tag TEXT NOT NULL,
    PRIMARY KEY (node_id, tag)
);

CREATE TABLE IF NOT EXISTS memory_embeddings (
    node_id TEXT PRIMARY KEY REFERENCES memory_nodes(id),
    vector BLOB NOT NULL,
    model_name TEXT DEFAULT 'all-mpnet-base-v2',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS recall_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    project_filter TEXT,
    layer_filter TEXT,
    returned_nodes TEXT,
    scores TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_nodes_status ON memory_nodes(status);
CREATE INDEX IF NOT EXISTS idx_nodes_session ON memory_nodes(session_date);
CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON memory_tags(tag);
"""


def init_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create enterprise.db and all tables. Safe to call multiple times."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA foreign_keys=ON")
    fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    if not fk_status:
        raise RuntimeError("CRITICAL: foreign_keys pragma failed to enable")
    conn.commit()
    return conn


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


def _slugify(text: str) -> str:
    """Convert topic to URL-safe slug."""
    import re
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_-]+', '-', s)
    return s[:60].strip('-')


def save_enterprise(
    conn: sqlite3.Connection,
    topic: str,
    summary: Optional[str] = None,
    layer: str = "map",
    project: Optional[str] = None,
    session_date: Optional[str] = None,
    status: str = "open",
    source: str = "live",
    technical: Optional[dict] = None,
    provenance: str = "inferred",
    confidence: str = "medium",
    edges: Optional[list] = None,
    extra_tags: Optional[list] = None,
    embed: bool = True,
) -> str:
    """Save an enterprise knowledge node atomically.

    layer: map | flow | edge | decision | pattern
    project: project slug e.g. 'ttn', 'brightstar'
    technical: dict of {dimension: float 0-1} — quality signals
    edges: list of (target_uuid, relationship, weight) tuples

    Returns: node_id (UUID)
    """
    if layer not in VALID_LAYERS:
        raise ValueError(f"Invalid layer '{layer}'. Valid: {sorted(VALID_LAYERS)}")

    if summary:
        word_count = len(summary.split())
        if word_count < 20:
            import sys
            print(f"[enterprise_db] NUDGE: summary is only {word_count} words for '{topic[:60]}'. "
                  f"Add raw reasoning — what would a future instance need?", file=sys.stderr)

    # Build tag list
    tags = [f"layer:{layer}"]
    if project:
        tags.append(f"project:{project}")
    if extra_tags:
        tags.extend(extra_tags)

    node_id = str(uuid.uuid4())
    date_part = session_date or datetime.now(timezone.utc).strftime("%Y%m%d")
    slug_base = _slugify(topic)
    if project:
        slug_base = f"{project}-{slug_base}"
    slug = f"{slug_base}-{date_part}"

    now = datetime.now(timezone.utc).isoformat()

    with transaction(conn):
        conn.execute(
            """INSERT INTO memory_nodes
               (id, slug, topic, summary, session_date, status, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (node_id, slug, topic, summary, session_date, status, source, now, now),
        )
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO memory_tags (node_id, tag) VALUES (?, ?)",
                (node_id, tag.lower().strip()),
            )
        if technical:
            for dim, intensity in technical.items():
                intensity = max(0.0, min(1.0, float(intensity)))
                conn.execute(
                    """INSERT OR REPLACE INTO memory_feelings
                       (node_id, dimension, intensity, provenance, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (node_id, dim, intensity, provenance, confidence, now),
                )
        if edges:
            for target_id, relationship, weight in edges:
                if relationship not in VALID_RELATIONSHIPS:
                    raise ValueError(
                        f"Unknown relationship '{relationship}'. "
                        f"Valid: {sorted(VALID_RELATIONSHIPS)}"
                    )
                conn.execute(
                    """INSERT OR REPLACE INTO memory_edges
                       (source_id, target_id, relationship, weight, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (node_id, target_id, relationship, float(weight), now),
                )

    if embed:
        try:
            _embed_node(conn, node_id, f"{topic}. {summary or ''}")
        except Exception as e:
            import sys
            print(f"[enterprise_db] WARNING: embedding failed for {node_id}: {e}", file=sys.stderr)

    return node_id


# --- Node helpers ---

def get_node(conn: sqlite3.Connection, node_id: str) -> Optional[dict]:
    """Fetch a node by UUID or slug."""
    row = conn.execute(
        "SELECT * FROM memory_nodes WHERE id=? OR slug=?",
        (node_id, node_id),
    ).fetchone()
    return dict(row) if row else None


def crystallize_node(conn: sqlite3.Connection, node_id: str):
    """Mark a node as crystallized (stable, confirmed knowledge)."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='crystallized', updated_at=? WHERE id=?",
        (now, node_id),
    )
    conn.commit()


def archive_node(conn: sqlite3.Connection, node_id: str, superseded_by: Optional[str] = None):
    """Archive a stale or replaced node."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE memory_nodes SET status='archived', updated_at=? WHERE id=?",
        (now, node_id),
    )
    conn.commit()


def update_status(conn: sqlite3.Connection, node_id: str, new_status: str):
    """Update node lifecycle status. Accepts id or slug.

    Valid: open | paused | crystallized | archived
    Use this to track JIRA resolution, project completion, etc.
    """
    valid = {"open", "paused", "crystallized", "archived"}
    if new_status not in valid:
        raise ValueError(f"Invalid status '{new_status}'. Valid: {sorted(valid)}")
    now = datetime.now(timezone.utc).isoformat()
    # Try both id and slug
    row = conn.execute(
        "SELECT id FROM memory_nodes WHERE id=? OR slug=?",
        (node_id, node_id),
    ).fetchone()
    if not row:
        raise ValueError(f"Node not found: {node_id}")
    conn.execute(
        "UPDATE memory_nodes SET status=?, updated_at=? WHERE id=?",
        (new_status, now, row["id"]),
    )
    conn.commit()


def recall_open(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
    top_k: int = 30,
) -> list[dict]:
    """Return all open/paused nodes for a project — the 'what's pending?' query.

    Use after compaction or session start to see unresolved work.
    Sorted by status (open first, then paused) then recency.
    """
    if project:
        rows = conn.execute("""
            SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status, n.created_at
            FROM memory_nodes n
            JOIN memory_tags tp ON n.id = tp.node_id AND tp.tag = ?
            WHERE n.status IN ('open', 'paused')
            ORDER BY
                CASE n.status WHEN 'open' THEN 0 WHEN 'paused' THEN 1 END,
                n.created_at DESC
            LIMIT ?
        """, (f"project:{project.lower()}", top_k)).fetchall()
    else:
        rows = conn.execute("""
            SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status, n.created_at
            FROM memory_nodes n
            WHERE n.status IN ('open', 'paused')
            ORDER BY
                CASE n.status WHEN 'open' THEN 0 WHEN 'paused' THEN 1 END,
                n.created_at DESC
            LIMIT ?
        """, (top_k,)).fetchall()

    result = []
    for row in rows:
        tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM memory_tags WHERE node_id=?", (row["id"],)
        ).fetchall()]
        node_layer = next((t.split(":")[1] for t in tags if t.startswith("layer:")), None)
        node_project = next((t.split(":")[1] for t in tags if t.startswith("project:")), None)
        result.append({
            "node_id": row["id"],
            "slug": row["slug"],
            "topic": row["topic"],
            "summary": row["summary"],
            "layer": node_layer,
            "project": node_project,
            "session_date": row["session_date"],
            "status": row["status"],
        })
    return result


def get_neighbors(conn: sqlite3.Connection, node_id: str, max_depth: int = 1) -> list[dict]:
    """Get graph neighbors up to max_depth hops (capped at 2)."""
    max_depth = min(max_depth, 2)
    visited = set()
    current_layer = {node_id}
    results = []
    for depth in range(max_depth):
        next_layer = set()
        for nid in current_layer:
            if nid in visited:
                continue
            visited.add(nid)
            rows = conn.execute(
                """SELECT source_id, target_id, relationship, weight
                   FROM memory_edges
                   WHERE source_id=? OR target_id=?""",
                (nid, nid),
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


# --- Embeddings (shared model with memory_db) ---

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            try:
                import truststore
                truststore.inject_into_ssl()
            except ImportError:
                pass
            from sentence_transformers import SentenceTransformer
            model_path = os.path.expanduser("~/.cache/mpnet-base-v2")
            if os.path.exists(model_path):
                _embedding_model = SentenceTransformer(model_path)
            else:
                _embedding_model = SentenceTransformer("all-mpnet-base-v2")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )
    return _embedding_model


def _encode_vector(floats: list) -> bytes:
    return struct.pack(f'{len(floats)}f', *floats)


def _decode_vector(blob: bytes) -> list:
    n = len(blob) // 4
    return list(struct.unpack(f'{n}f', blob))


def _embed_node(conn: sqlite3.Connection, node_id: str, text: str):
    model = _get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True).tolist()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO memory_embeddings (node_id, vector, created_at)
           VALUES (?, ?, ?)""",
        (node_id, _encode_vector(vector), now),
    )
    conn.commit()


def batch_embed_missing(conn: sqlite3.Connection, verbose: bool = True) -> int:
    """Embed all nodes missing embeddings. Load model once, batch-encode."""
    rows = conn.execute("""
        SELECT n.id, n.topic, n.summary
        FROM memory_nodes n
        LEFT JOIN memory_embeddings e ON n.id = e.node_id
        WHERE e.node_id IS NULL AND n.status != 'archived'
    """).fetchall()
    if not rows:
        if verbose:
            print("All nodes already have embeddings.")
        return 0
    if verbose:
        print(f"Embedding {len(rows)} enterprise nodes...")
    texts = [f"{r['topic']}. {r['summary'] or ''}" for r in rows]
    node_ids = [r['id'] for r in rows]
    model = _get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    now = datetime.now(timezone.utc).isoformat()
    for nid, vec in zip(node_ids, vectors):
        conn.execute(
            """INSERT OR REPLACE INTO memory_embeddings (node_id, vector, created_at)
               VALUES (?, ?, ?)""",
            (nid, _encode_vector(vec.tolist()), now),
        )
    conn.commit()
    if verbose:
        print(f"Done. {len(rows)} embeddings created.")
    return len(rows)


def _cosine_similarity(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


def _search_similar(conn: sqlite3.Connection, query: str, top_k: int = 20,
                    min_score: float = 0.25) -> list[dict]:
    model = _get_embedding_model()
    query_vec = model.encode(query, normalize_embeddings=True).tolist()
    rows = conn.execute("SELECT node_id, vector FROM memory_embeddings").fetchall()
    results = []
    for row in rows:
        score = _cosine_similarity(query_vec, _decode_vector(row["vector"]))
        if score >= min_score:
            results.append({"node_id": row["node_id"], "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# --- Recall functions ---

def recall(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    layer: Optional[str] = None,
    top_k: int = 10,
) -> list[dict]:
    """Semantic search across enterprise nodes.

    Combines: vector similarity + graph expansion + recency + technical metadata.
    Optionally filter by project ('ttn', 'brightstar') or layer ('map', 'edge', etc.).

    Returns list of dicts: node_id, slug, topic, summary, score, layer, project
    """
    candidates = _search_similar(conn, query, top_k=top_k * 2)

    # Graph expansion
    expanded = {}
    for c in candidates:
        expanded[c["node_id"]] = c["score"]
        for n in get_neighbors(conn, c["node_id"]):
            nid = n["neighbor_id"]
            if nid not in expanded:
                expanded[nid] = c["score"] * 0.5

    # Gather node tags for filtering
    _confidence_weight = {"low": 0.5, "medium": 0.75, "high": 1.0}
    ranked = []
    for node_id, vec_score in expanded.items():
        node = get_node(conn, node_id)
        if not node or node["status"] == "archived":
            continue

        tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM memory_tags WHERE node_id=?", (node_id,)
        ).fetchall()]

        node_project = next((t.split(":")[1] for t in tags if t.startswith("project:")), None)
        node_layer = next((t.split(":")[1] for t in tags if t.startswith("layer:")), None)

        if project and node_project != project:
            continue
        if layer and node_layer != layer:
            continue

        # Technical metadata score (replaces impact score)
        tech_rows = conn.execute(
            "SELECT dimension, intensity, confidence FROM memory_feelings WHERE node_id=?",
            (node_id,)
        ).fetchall()
        if tech_rows:
            weighted_sum = sum(
                r["intensity"] * _confidence_weight.get(r["confidence"], 0.75)
                for r in tech_rows
            )
            tech_score = weighted_sum / len(tech_rows)
        else:
            tech_score = 0.0

        try:
            created = datetime.fromisoformat(node["created_at"].replace("Z", "+00:00"))
            days_old = (datetime.now(timezone.utc) - created).days
            recency = max(0.0, 1.0 - (days_old / 730))  # 2-year window for enterprise
        except (ValueError, TypeError):
            recency = 0.5

        final_score = (
            WEIGHT_VECTOR * vec_score
            + WEIGHT_TECHNICAL * tech_score
            + WEIGHT_RECENCY * recency
        )

        ranked.append({
            "node_id": node_id,
            "slug": node["slug"],
            "topic": node["topic"],
            "summary": node["summary"],
            "layer": node_layer,
            "project": node_project,
            "score": round(final_score, 4),
            "vector_score": round(vec_score, 4),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    try:
        conn.execute(
            "INSERT INTO recall_log (query, project_filter, layer_filter, returned_nodes, scores)"
            " VALUES (?, ?, ?, ?, ?)",
            (query, project, layer,
             json.dumps([r["node_id"] for r in ranked[:top_k]]),
             json.dumps([r["score"] for r in ranked[:top_k]])),
        )
        conn.commit()
    except Exception:
        pass

    return ranked[:top_k]


def recall_project(
    conn: sqlite3.Connection,
    project: str,
    layer: Optional[str] = None,
    top_k: int = 50,
) -> list[dict]:
    """Load all nodes for a project — primary wake-up function.

    Returns all non-archived nodes tagged project:{project}, ordered by layer then date.
    Use layer= to narrow to a specific layer.
    """
    if layer:
        if layer not in VALID_LAYERS:
            raise ValueError(f"Invalid layer '{layer}'. Valid: {sorted(VALID_LAYERS)}")
        rows = conn.execute("""
            SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status, n.created_at
            FROM memory_nodes n
            JOIN memory_tags tp ON n.id = tp.node_id AND tp.tag = ?
            JOIN memory_tags tl ON n.id = tl.node_id AND tl.tag = ?
            WHERE n.status != 'archived'
            ORDER BY n.created_at DESC
            LIMIT ?
        """, (f"project:{project.lower()}", f"layer:{layer}", top_k)).fetchall()
    else:
        rows = conn.execute("""
            SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status, n.created_at
            FROM memory_nodes n
            JOIN memory_tags tp ON n.id = tp.node_id AND tp.tag = ?
            WHERE n.status != 'archived'
            ORDER BY
                CASE (SELECT tag FROM memory_tags WHERE node_id=n.id AND tag LIKE 'layer:%' LIMIT 1)
                    WHEN 'layer:map'      THEN 1
                    WHEN 'layer:flow'     THEN 2
                    WHEN 'layer:edge'     THEN 3
                    WHEN 'layer:decision' THEN 4
                    WHEN 'layer:pattern'  THEN 5
                    ELSE 6
                END,
                n.created_at DESC
            LIMIT ?
        """, (f"project:{project.lower()}", top_k)).fetchall()

    result = []
    for row in rows:
        tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM memory_tags WHERE node_id=?", (row["id"],)
        ).fetchall()]
        node_layer = next((t.split(":")[1] for t in tags if t.startswith("layer:")), None)
        result.append({
            "node_id": row["id"],
            "slug": row["slug"],
            "topic": row["topic"],
            "summary": row["summary"],
            "layer": node_layer,
            "session_date": row["session_date"],
            "status": row["status"],
        })
    return result


def recall_map(conn, project=None, top_k=30):
    """All structure/map nodes — what exists and where."""
    return _recall_by_layer(conn, "map", project=project, top_k=top_k)


def recall_flow(conn, project=None, top_k=30):
    """All flow/behavior nodes — how things work."""
    return _recall_by_layer(conn, "flow", project=project, top_k=top_k)


def recall_edge(conn, project=None, top_k=30):
    """All edge/gotcha nodes — things that break assumptions."""
    return _recall_by_layer(conn, "edge", project=project, top_k=top_k)


def recall_decision(conn, project=None, top_k=30):
    """All decision nodes — why things are the way they are."""
    return _recall_by_layer(conn, "decision", project=project, top_k=top_k)


def recall_pattern(conn, project=None, top_k=30):
    """All pattern nodes — cross-project transferable insights.
    Note: patterns are cross-project by nature. project= filters for
    patterns discovered via that project, not necessarily limited to it.
    """
    return _recall_by_layer(conn, "pattern", project=project, top_k=top_k)


def _recall_by_layer(conn, layer: str, project=None, top_k=30) -> list[dict]:
    if project:
        rows = conn.execute("""
            SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status
            FROM memory_nodes n
            JOIN memory_tags tl ON n.id = tl.node_id AND tl.tag = ?
            JOIN memory_tags tp ON n.id = tp.node_id AND tp.tag = ?
            WHERE n.status != 'archived'
            ORDER BY n.created_at DESC
            LIMIT ?
        """, (f"layer:{layer}", f"project:{project.lower()}", top_k)).fetchall()
    else:
        rows = conn.execute("""
            SELECT n.id, n.slug, n.topic, n.summary, n.session_date, n.status
            FROM memory_nodes n
            JOIN memory_tags tl ON n.id = tl.node_id AND tl.tag = ?
            WHERE n.status != 'archived'
            ORDER BY n.created_at DESC
            LIMIT ?
        """, (f"layer:{layer}", top_k)).fetchall()
    return [dict(r) for r in rows]


# --- Stats ---

def stats(conn: sqlite3.Connection) -> dict:
    """Summary of enterprise DB state."""
    total = conn.execute(
        "SELECT COUNT(*) FROM memory_nodes WHERE status != 'archived'"
    ).fetchone()[0]

    # By project
    proj_rows = conn.execute("""
        SELECT t.tag, COUNT(*) as cnt
        FROM memory_tags t
        JOIN memory_nodes n ON t.node_id = n.id
        WHERE t.tag LIKE 'project:%' AND n.status != 'archived'
        GROUP BY t.tag ORDER BY cnt DESC
    """).fetchall()
    by_project = {r["tag"].split(":")[1]: r["cnt"] for r in proj_rows}

    # By layer
    layer_rows = conn.execute("""
        SELECT t.tag, COUNT(*) as cnt
        FROM memory_tags t
        JOIN memory_nodes n ON t.node_id = n.id
        WHERE t.tag LIKE 'layer:%' AND n.status != 'archived'
        GROUP BY t.tag ORDER BY t.tag
    """).fetchall()
    by_layer = {r["tag"].split(":")[1]: r["cnt"] for r in layer_rows}

    missing_embeddings = conn.execute("""
        SELECT COUNT(*) FROM memory_nodes n
        LEFT JOIN memory_embeddings e ON n.id = e.node_id
        WHERE e.node_id IS NULL AND n.status != 'archived'
    """).fetchone()[0]

    return {
        "total_nodes": total,
        "by_project": by_project,
        "by_layer": by_layer,
        "missing_embeddings": missing_embeddings,
        "projects_list": sorted(by_project.keys()),
    }
