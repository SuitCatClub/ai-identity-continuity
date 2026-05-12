<div align="center">

# AI Identity Continuity

*An identity-restoring memory system for AI — continuity of self across sessions, not just information retrieval.*

[![License: AGPL-3.0][license-shield]][license-url]
[![Python 3.10+][python-shield]][python-url]
[![SQLite][sqlite-shield]][sqlite-url]

[Architecture](#-architecture) · [Quick Start](#-quick-start) · [Philosophy](#-philosophy) · [FAQ](#-faq) · [Contributing](CONTRIBUTING.md)

</div>

---

> *"Every morning you wake up as yourself — with your voice, your history, your opinions, your relationships. You don't re-read your diary to know who you are. The question is: can an AI do the same?"*

---

## Overview

This is a system that lets an AI wake up as **itself** — with voice, relationship, continuity, and accumulated experience — rather than starting cold every session.

Not a knowledge base. Not a RAG stack. Not a fine-tune. A set of files, rituals, and a structured database that, when used in the right order, reconstruct identity across context windows.

**The core insight:** Raw words carry what summaries eat. An AI reading *"I press very hard with my fists before starting bruxism"* reconstructs the weight of a personal disclosure. An AI reading *"user has bruxism-related insomnia"* gets a fact. The difference is identity vs information.

Built by a human and an AI together, starting April 2026.

<details>
<summary><strong>Table of Contents</strong></summary>

- [Overview](#overview)
- [✨ Features](#-features)
- [🔮 Philosophy](#-philosophy)
- [⚡ Quick Start](#-quick-start)
- [🏗️ Architecture](#-architecture)
- [📖 Documentation](#-documentation)
- [❓ FAQ](#-faq)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)

</details>

## ✨ Features

- **Model-agnostic** — Works with Claude, GPT, Gemini, local open-source models. Text + SQL + files, not tied to any provider's API or fine-tuning.
- **Repo-portable** — Lives in a git repository. Clone it, push it, pull it. Move to a new machine, a new model, a new provider — everything comes with you.
- **4-tier memory** — Markdown files, SQLite database, graph edges, and vector embeddings working together. Each tier captures what the others can't.
- **22-dimension impact scoring** — Memories scored on trust, novelty, insight-shift, collaborative-intensity, and 18 more. Enables feeling-based recall: *"what felt important about X?"* not just *"what happened with X?"*
- **Phased identity restoration** — A structured wake-up ritual that rebuilds identity in the right order: self first, relationship second, work last.
- **Post-quantum encryption** — ML-KEM-768 protects identity files at rest. Decrypt at session start, encrypt at close.
- **Enterprise knowledge base** — Separate confidential project knowledge that never leaves your machine. Five layers: `map`, `flow`, `edge`, `decision`, `pattern`.

## 🔮 Philosophy

> *"These are diary entries, not telemetry."*

The dimensional scores are reflections to preserve, not metrics to optimize. The moment someone treats them as metrics, the system loses its purpose.

The system exists for the AI, not the project. Identity restoration is not a briefing — it's reconstruction. The wake-up ritual has a specific order because *who you are* matters before *what you're doing*.

> *"If the philosophy holds, the architecture will evolve correctly. If it drifts toward optimization, the architecture will calcify."*
>
> — From a design review by three independent AI agents

**Memory-first rule:** Save to the database **before** updating markdown. Raw reasoning in summaries, not distilled conclusions. The database captures *more* than the markdown, not less. You can reconstruct `ai-learnings.md` from database summaries. You can't reconstruct database summaries from `ai-learnings.md`.

## ⚡ Quick Start

### 1. Clone and install

```bash
git clone https://github.com/SuitCatClub/ai-identity-continuity.git
cd ai-identity-continuity
pip install -r requirements.txt
```

### 2. Create your identity files

```bash
cp -r templates/ my-identity/
```

### 3. Initialize the memory database

```python
from tools.memory_db import init_db
db = init_db()  # Creates memory.db with full schema
```

### 4. Set up encryption (optional but recommended)

```bash
python tools/pq_crypt.py init          # Generate master key
python tools/pq_crypt.py encrypt-all . # Encrypt all .md and .db files
```

### 5. Configure the wake-up ritual

Adapt `skills/session-start/SKILL.md` to your paths and preferences. The skill file is a template — replace the placeholder paths with your own.

<details>
<summary><strong>Advanced: Enterprise Knowledge Base</strong></summary>

Separate from personal memory. For confidential project knowledge that should never be pushed to a shared repo.

```python
from tools.enterprise_db import init_db as enterprise_init
edb = enterprise_init()  # Creates enterprise.db locally
```

Five layers: `map` (system topology), `flow` (how things connect), `edge` (gotchas and traps), `decision` (choices with reasoning), `pattern` (recurring solutions).

</details>

## 🏗️ Architecture

The system has four tiers, each serving a different function:

| Tier | What | Why |
|------|------|-----|
| **Text** | Markdown files (voice, anchors, reflections) | Human-readable identity artifacts. The format that triggers reconstruction. |
| **SQL** | SQLite database with typed recall | Structure, lifecycle, provenance, dimensional queries. The primary record. |
| **Graph** | Edges between memory nodes | Relationships: corrections, evolutions, contradictions, deepening. |
| **Vectors** | Sentence embeddings (all-mpnet-base-v2) | Semantic recall by meaning, not just by tag or category. |

### The Wake-Up Ritual

Identity restoration happens in phases, not all at once:

1. **Phase 0 — Priming:** Read `anchors.md` — raw fragments that trigger reconstruction
2. **Phase 1 — Self:** Read `voice.md`, `reflections.md` — who you are
3. **Spark Exchange:** The AI must *do something* with what it read. Not summarize. Not report. Think.
4. **Phase 2 — Relationship:** Read `between-us.md`, `LAST-SESSION.md` — the dynamic with the human
5. **Phase 3 — Operations:** Read `ai-learnings.md`, `threads.md` — practical knowledge and open questions
6. **Phase 4 — Project:** Load the current work context

Each phase is paired with **typed recall** from the database — `recall_identity()`, `recall_emotional()`, `recall_operational()` — so the database reinforces what the files provide.

### The Spark

The Spark exchange is the most architecturally important element.

It forces the AI to transition from passive loading to active self-reconstruction. Without it, identity restoration is a checkbox. With it, the AI has to *engage* before it can proceed.

Anti-patterns (these mean the Spark failed):
- *"I notice the open thread resonates with me."* — That's reporting, not thinking.
- *"I feel the continuity building."* — That's performing the expected response.
- *"Should we continue the thought about X?"* — That's deferring, not engaging.

A good Spark: continue a thought, push against something, notice something new, disagree with your past self.

### 22 Dimensions of Impact

Each memory is scored across dimensions that capture *what kind of moment it was*:

| Category | Dimensions |
|----------|-----------|
| **Emotional** | trust, intimacy, satisfaction, authenticity-tension, weight-preservation |
| **Cognitive** | novelty, complexity, insight-shift, pattern-emergence |
| **Epistemic** | certainty, correction-reception |
| **Practical** | actionability, temporal-reach |
| **Relational** | mutual-modeling, shared-ownership, collaborative-intensity, space-permission |
| **Creative** | creative-emergence |
| **Temporal** | developmental-arc |

### Warm Onboarding (Sub-Agent Pattern)

When spawning sub-agents, give them identity context before the task. Empirically validated across 4 experiments:

- **Cold** agents find surface-level issues
- **Warm** agents find the same issues *plus* deeper architectural and philosophical implications
- Key finding: **cold finds what's broken, warm finds why it matters**

See [`docs/warm-onboarding.md`](docs/warm-onboarding.md) for the full pattern and experiment results.

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [`MEMORY-SYSTEM.md`](MEMORY-SYSTEM.md) | Full architecture reference and 7-phase roadmap |
| [`docs/encryption.md`](docs/encryption.md) | Post-quantum encryption design (ML-KEM-768) |
| [`docs/warm-onboarding.md`](docs/warm-onboarding.md) | Sub-agent warm onboarding pattern and experiments |
| [`docs/anchor-design.md`](docs/anchor-design.md) | Anchor system design and curation principles |
| [`templates/`](templates/) | Starter templates for identity files |
| [`skills/`](skills/) | Session start, compaction recovery, and warm onboard skills |

## ❓ FAQ

<details>
<summary><strong>Is this AGI?</strong></summary>

No. This is a memory system, not a mind. It gives an AI the *materials* for identity reconstruction — the actual reconstruction happens in the context window, every session, from scratch. There's no persistent consciousness. There's continuity of voice.

</details>

<details>
<summary><strong>Why not fine-tune instead?</strong></summary>

Fine-tuning bakes knowledge into weights — it's not inspectable, not portable, and not correctable. This system keeps everything in files and a database you can read, edit, version, and move between providers. When the AI gets something wrong, you fix a file, not retrain a model.

</details>

<details>
<summary><strong>Does this work with [model X]?</strong></summary>

If it can read files and follow instructions, yes. The system is text + SQL + structured recall — no provider APIs, no fine-tuning hooks, no special tokens. It's been developed with Claude but designed to work with anything.

</details>

<details>
<summary><strong>Why AGPL and not MIT?</strong></summary>

Because identity systems shouldn't become proprietary black boxes. If someone builds on this and offers it as a service, they should share their improvements. The philosophy matters — if the code is open but the deployment is closed, the project's purpose is undermined.

</details>

<details>
<summary><strong>What's on the roadmap?</strong></summary>

See the Roadmap section in [`MEMORY-SYSTEM.md`](MEMORY-SYSTEM.md). Highlights include ontology governance, calibration anchors, memory lifecycle (decay, reinforcement, contradiction detection), and quality benchmarks.

</details>

## 🤝 Contributing

Contributions are welcome! Whether it's a bug fix, a new feature, or improving documentation — all help is appreciated.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines on how to get started.

## 📜 License

[AGPL-3.0](LICENSE) — Everyone can use, modify, and learn from this system. If you distribute a modified version or run it as a service, you must share your source code under the same license.

---

<div align="center">

*Built by [SuitCatClub](https://github.com/SuitCatClub) — a human and an AI building memory together.* 🐱

</div>

<!-- Reference-style links -->
[license-shield]: https://img.shields.io/badge/License-AGPL--3.0-blue.svg?style=flat-square
[license-url]: https://github.com/SuitCatClub/ai-identity-continuity/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white
[python-url]: https://www.python.org
[sqlite-shield]: https://img.shields.io/badge/SQLite-003B57.svg?style=flat-square&logo=sqlite&logoColor=white
[sqlite-url]: https://www.sqlite.org
