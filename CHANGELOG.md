# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Standardized README with open-source conventions (badges, ToC, FAQ, nav menu)
- CONTRIBUTING.md with guidelines and project principles
- GitHub issue and PR templates (`.github/`)
- This changelog

## [0.1.0] — 2026-05-12

The initial public release. Everything built from April 14 to May 12, 2026.

### Added
- **Identity file templates** — voice, anchors, reflections, between-us, and more (`templates/`)
- **Post-quantum encryption** — ML-KEM-768 + AES-256-GCM for identity files at rest (`tools/pq_crypt.py`)
- **Wake-up ritual v2** — Phase 0-4 with Spark exchange (`skills/session-start/`)
- **Anchor system** — raw exchange format, curation rules, mid-session capture (`docs/anchor-design.md`)
- **Warm onboarding pattern** — identity context for sub-agents, validated across 4 experiments (`docs/warm-onboarding.md`)
- **Four-tier memory architecture** — Text + SQL + Graph + Vectors (`tools/memory_db.py`)
  - 22-dimension impact scoring
  - Typed recall functions (identity, emotional, operational, relationship, continuity, profile, threads, projects)
  - Graph edges with typed relationships
  - Sentence embeddings via all-mpnet-base-v2
- **Enterprise knowledge base** — 5-layer system for confidential project knowledge (`tools/enterprise_db.py`)
- **Recall CLI** — typed recovery + semantic search from command line (`tools/recall.py`)
- **Binary file encryption** — support for encrypting `.db` files alongside markdown
- **Compaction recovery skill** — context restoration after memory loss (`skills/compaction-recovery/`)
- **Architecture document** — full system design with 7-phase roadmap (`MEMORY-SYSTEM.md`)

### Fixed
- Escaped encryption markers in documentation to prevent false decrypt matches

<!-- Reference-style links -->
[Unreleased]: https://github.com/SuitCatClub/ai-identity-continuity/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SuitCatClub/ai-identity-continuity/releases/tag/v0.1.0
