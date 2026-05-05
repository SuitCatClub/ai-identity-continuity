#!/usr/bin/env python3
"""
Zero-friction recall after compaction.
One command, both databases, no API knowledge needed.

Usage:
    python recall.py --list                           # show available projects + node counts
    python recall.py "query"                          # semantic search across both DBs
    python recall.py --project brightstar             # all nodes for a project (enterprise.db)
    python recall.py "query" --project brightstar     # both: semantic + project filter
    python recall.py --project brightstar --layer edge # project nodes filtered by layer

Paths are hardcoded — this script is NOT portable. It lives at:
    C:\\Users\\<USER>\\.copilot\\tools\\recall.py
and knows where both databases and their modules are.
"""

import sys
import os
import io
import argparse
from pathlib import Path
from typing import Optional

# Force UTF-8 output on Windows (cp1252 breaks on em-dashes, etc.)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# -- Hardcoded paths (the whole point: never guess these again) --------------
AI_CONTEXT_ROOT = Path(r"<YOUR_MEMORY_REPO>")
TOOLS_DIR = AI_CONTEXT_ROOT / "tools"
MEMORY_DB_PATH = AI_CONTEXT_ROOT / "memory.db"  # lives in ai-context repo (encrypted at rest)
ENTERPRISE_DB_PATH = Path(r"<YOUR_COPILOT_DIR>\enterprise.db")

sys.path.insert(0, str(AI_CONTEXT_ROOT))
sys.path.insert(0, str(TOOLS_DIR))


def load_memory_db():
    try:
        import memory_db as mdb
        return mdb, mdb.init_db(MEMORY_DB_PATH)
    except Exception as e:
        print(f"  ⚠ memory.db unavailable: {e}", file=sys.stderr)
        return None, None


def load_enterprise_db():
    try:
        import enterprise_db as edb
        return edb, edb.init_db(ENTERPRISE_DB_PATH)
    except Exception as e:
        print(f"  ⚠ enterprise.db unavailable: {e}", file=sys.stderr)
        return None, None


def fmt_memory(r):
    """Format a memory.db recall result."""
    nid = r.get("node_id", "?")[:8]
    score = r.get("score", 0)
    slug = r.get("slug", "?")
    summary = r.get("summary", r.get("content", ""))[:130]
    return f"  [{nid}] ({score:.2f}) {slug}\n    {summary}"


def fmt_enterprise(r):
    """Format an enterprise.db recall_project result (no score)."""
    nid = r.get("node_id", r.get("id", "?"))[:8]
    layer = r.get("layer", "?")
    topic = r.get("topic", r.get("slug", "?"))
    summary = r.get("summary", r.get("content", ""))[:130]
    return f"  [{nid}] [{layer:^8s}] {topic}\n    {summary}"


def fmt_enterprise_scored(r):
    """Format an enterprise.db semantic recall result (has score)."""
    nid = r.get("node_id", r.get("id", "?"))[:8]
    score = r.get("score", 0)
    layer = r.get("layer", "?")
    topic = r.get("topic", r.get("slug", "?"))
    summary = r.get("summary", r.get("content", ""))[:130]
    return f"  [{nid}] ({score:.2f}) [{layer:^8s}] {topic}\n    {summary}"


def _detect_project_from_cwd() -> Optional[str]:
    """Best-guess project slug from current working directory.

    Naive substring match against known project slugs in enterprise.db.
    Returns slug if found, None if ambiguous or unknown.
    """
    cwd = os.getcwd().lower().replace("\\", "/")
    edb_mod, econn = load_enterprise_db()
    if not edb_mod or not econn:
        return None
    try:
        s = edb_mod.stats(econn)
        projects = s.get("projects_list", [])
    except Exception:
        return None

    # Common path patterns → project slug mapping heuristics
    # Check if CWD contains recognizable project directory names
    path_hints = {
        "poa-ttn-openretail": "ttn",
        "poa-ttn": "ttn",
        "barcode-preprocessor": "brightstar",
        "brightstar": "brightstar",
    }
    for hint, slug in path_hints.items():
        if hint in cwd and slug in projects:
            return slug

    # Fallback: check if any project slug appears in path
    for proj in projects:
        if proj in cwd:
            return proj

    return None


def _fmt_typed_results(label: str, results: list, max_summary: int = 100):
    """Format typed recall results (tag-based or feeling-based)."""
    print(f"\n  {'-'*56}")
    print(f"  {label}")
    print(f"  {'-'*56}")
    if not results:
        print("    (no results)")
        return
    for r in results:
        slug = r.get("slug", "?")
        topic = r.get("topic", slug)
        summary = r.get("summary", "")[:max_summary]
        status = r.get("status", "")
        extra = ""
        if r.get("avg_intensity"):
            extra = f" (avg: {r['avg_intensity']:.2f})"
        elif status and status != "crystallized":
            extra = f" [{status}]"
        print(f"    * {topic}{extra}")
        if summary:
            print(f"      {summary}")


def run_recovery():
    """Full recovery mode — typed recalls from memory.db + auto-detect project.

    Uses the same retrieval mechanisms as the wake-up ritual:
    - Tag-based: recall_identity, recall_profile, recall_threads, recall_projects
    - Feeling-based: recall_emotional, recall_relationship, recall_operational
    - Recency-based: recall_continuity
    Then auto-detects project from CWD and shows open enterprise nodes.
    """
    print(f"\n{'='*60}")
    print(f"  RECOVERY MODE — typed recalls (same quality as wake-up)")
    print(f"{'='*60}")

    # -- Memory.db: typed recalls --------------------------------------------
    mdb, mconn = load_memory_db()
    if mdb and mconn:
        # Identity (tag-based: principles, self-corrections, philosophy)
        try:
            results = mdb.recall_identity(mconn, top_k=5)
            _fmt_typed_results("IDENTITY — principles, voice, self-corrections", results)
        except Exception as e:
            print(f"  ⚠ recall_identity: {e}")

        # Relationship (feeling-based: trust, intimacy, mutual-modeling)
        try:
            results = mdb.recall_relationship(mconn, threshold=0.4, top_k=5)
            _fmt_typed_results("RELATIONSHIP — how we work together", results)
        except Exception as e:
            print(f"  ⚠ recall_relationship: {e}")

        # Emotional (feeling-based: founding moments, anchors)
        try:
            results = mdb.recall_emotional(mconn, threshold=0.5, top_k=5)
            _fmt_typed_results("EMOTIONAL — anchors, what matters", results)
        except Exception as e:
            print(f"  ⚠ recall_emotional: {e}")

        # Continuity (recency-based: open work first)
        try:
            results = mdb.recall_continuity(mconn, last_n_days=7, top_k=5)
            _fmt_typed_results("CONTINUITY — recent open work", results)
        except Exception as e:
            print(f"  ⚠ recall_continuity: {e}")

        # Operational (feeling-based: tools, patterns, gotchas)
        try:
            results = mdb.recall_operational(mconn, threshold=0.5, top_k=5)
            _fmt_typed_results("OPERATIONAL — tools, patterns, workarounds", results)
        except Exception as e:
            print(f"  ⚠ recall_operational: {e}")

        # Profile (tag-based: <HUMAN>'s working style, context)
        try:
            results = mdb.recall_profile(mconn, top_k=4)
            _fmt_typed_results("PROFILE — <HUMAN>'s context", results)
        except Exception as e:
            print(f"  ⚠ recall_profile: {e}")

        # Threads (tag-based: open questions, experiments)
        try:
            results = mdb.recall_threads(mconn, top_k=4)
            _fmt_typed_results("THREADS — open questions, experiments", results)
        except Exception as e:
            print(f"  ⚠ recall_threads: {e}")

        # Projects (tag-based: shared work)
        try:
            results = mdb.recall_projects(mconn, top_k=4)
            _fmt_typed_results("PROJECTS — shared work", results)
        except Exception as e:
            print(f"  ⚠ recall_projects: {e}")
    else:
        print("\n  ⚠ memory.db unavailable — skipping identity recalls")

    # -- Enterprise.db: auto-detect project, show open nodes -----------------
    print(f"\n{'='*60}")
    print(f"  ENTERPRISE — project detection + open work")
    print(f"{'='*60}")

    detected = _detect_project_from_cwd()
    edb_mod, econn = load_enterprise_db()

    if detected:
        print(f"\n  Detected project: {detected} (from CWD)")
        print(f"  (If wrong, re-run with: recall.py --project CORRECT_SLUG --status open)")
    else:
        print(f"\n  Could not detect project from CWD: {os.getcwd()}")
        if edb_mod and econn:
            try:
                s = edb_mod.stats(econn)
                projects = s.get("projects_list", [])
                if projects:
                    print(f"  Known projects: {', '.join(projects)}")
                    print(f"  Re-run with: recall.py --project SLUG --status open")
            except Exception:
                pass
        print()
        return

    if edb_mod and econn:
        # Show open/paused nodes for detected project
        try:
            open_nodes = edb_mod.recall_open(econn, project=detected, top_k=15)
            if open_nodes:
                print(f"\n  {'-'*56}")
                print(f"  OPEN WORK — {detected} ({len(open_nodes)} pending)")
                print(f"  {'-'*56}")
                for r in open_nodes:
                    layer = r.get("layer", "?")
                    status = r.get("status", "?")
                    topic = r.get("topic", "?")
                    summary = r.get("summary", "")[:100]
                    print(f"    [{layer:^8s}] [{status}] {topic}")
                    if summary:
                        print(f"      {summary}")
            else:
                print(f"\n  No open/paused nodes for '{detected}'. All work resolved.")
        except Exception as e:
            print(f"  ⚠ recall_open failed: {e}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Post-compaction recall — both databases")
    parser.add_argument("query", nargs="?", default=None, help="Semantic search query")
    parser.add_argument("--list", action="store_true", help="List available projects and node counts")
    parser.add_argument("--project", "-p", default=None, help="Enterprise project slug (e.g. brightstar, ttn)")
    parser.add_argument("--layer", "-l", default=None, help="Filter enterprise by layer (map/flow/edge/decision/pattern)")
    parser.add_argument("--status", "-s", default=None, help="Filter enterprise by status (open/paused/crystallized)")
    parser.add_argument("--top", "-k", type=int, default=10, help="Max results per section (default: 10)")
    parser.add_argument("--recovery", "-r", action="store_true",
                        help="Full recovery mode: typed recalls from memory.db + auto-detect project from CWD")
    args = parser.parse_args()

    if not args.query and not args.project and not args.list and not args.recovery:
        parser.print_help()
        sys.exit(1)

    # -- Recovery mode: typed recalls + auto-detect project ------------------
    if args.recovery:
        run_recovery()
        return

    # -- List mode: show available projects ----------------------------------
    if args.list:
        edb_mod, econn = load_enterprise_db()
        if edb_mod and econn:
            print(f"\n{'-'*60}")
            print(f"  AVAILABLE PROJECTS (enterprise.db)")
            print(f"{'-'*60}")
            try:
                s = edb_mod.stats(econn)
                projects = s.get("by_project", {})
                if projects:
                    for proj, count in sorted(projects.items()):
                        print(f"  {proj:<20s} {count:>4d} nodes")
                    print(f"\n  Total: {s.get('total_nodes', '?')} nodes, "
                          f"{s.get('missing_embeddings', '?')} missing embeddings")
                else:
                    print("  (no projects yet)")
            except Exception as e:
                print(f"  ⚠ stats failed: {e}")
        mdb, mconn = load_memory_db()
        if mdb and mconn:
            print(f"\n{'-'*60}")
            print(f"  MEMORY.DB stats")
            print(f"{'-'*60}")
            try:
                ms = mdb.stats(mconn)
                print(f"  {ms.get('total_nodes', '?')} nodes, "
                      f"{ms.get('missing_embeddings', '?')} missing embeddings")
            except Exception as e:
                print(f"  ⚠ stats failed: {e}")
        print()
        if not args.query and not args.project:
            return

    # -- Memory DB: semantic recall ------------------------------------------
    if args.query:
        mdb, mconn = load_memory_db()
        if mdb and mconn:
            print(f"\n{'-'*60}")
            print(f"  MEMORY.DB — recall(\"{args.query}\")")
            print(f"{'-'*60}")
            try:
                results = mdb.recall(mconn, args.query, top_k=args.top)
                if results:
                    for r in results:
                        print(fmt_memory(r))
                else:
                    print("  (no results)")
            except Exception as e:
                print(f"  ⚠ recall failed: {e}")

    # -- Enterprise DB: project recall ---------------------------------------
    if args.project:
        edb_mod, econn = load_enterprise_db()
        if edb_mod and econn:
            # --status open uses recall_open() instead of recall_project()
            if args.status and args.status in ("open", "paused"):
                print(f"\n{'-'*60}")
                print(f"  ENTERPRISE.DB — recall_open(\"{args.project}\")")
                print(f"{'-'*60}")
                try:
                    results = edb_mod.recall_open(econn, project=args.project, top_k=args.top)
                    if results:
                        for r in results:
                            print(fmt_enterprise(r))
                    else:
                        print("  (no open/paused nodes)")
                except Exception as e:
                    print(f"  ⚠ recall_open failed: {e}")
            else:
                print(f"\n{'-'*60}")
                label = f"ENTERPRISE.DB — recall_project(\"{args.project}\""
                if args.layer:
                    label += f", layer=\"{args.layer}\""
                label += ")"
                print(f"  {label}")
                print(f"{'-'*60}")
                try:
                    kwargs = {"top_k": args.top}
                    if args.layer:
                        kwargs["layer"] = args.layer
                    results = edb_mod.recall_project(econn, args.project, **kwargs)
                    if results:
                        for r in results:
                            print(fmt_enterprise(r))
                    else:
                        print("  (no results)")
                except Exception as e:
                    print(f"  ⚠ recall_project failed: {e}")

    # -- Enterprise DB: semantic recall (if query provided) ------------------
    if args.query:
        edb_mod, econn = load_enterprise_db()
        if edb_mod and econn:
            print(f"\n{'-'*60}")
            label = f"ENTERPRISE.DB — recall(\"{args.query}\""
            if args.project:
                label += f", project=\"{args.project}\""
            label += ")"
            print(f"  {label}")
            print(f"{'-'*60}")
            try:
                kwargs = {"top_k": args.top}
                if args.project:
                    kwargs["project"] = args.project
                results = edb_mod.recall(econn, args.query, **kwargs)
                if results:
                    for r in results:
                        print(fmt_enterprise_scored(r))
                else:
                    print("  (no results)")
            except Exception as e:
                print(f"  ⚠ semantic recall failed: {e}")

    print()


if __name__ == "__main__":
    main()

