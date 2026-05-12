# Contributing to AI Identity Continuity

Thanks for your interest in contributing! This project sits at an unusual intersection — software engineering, AI identity, and philosophy. Contributions of all kinds are welcome.

## Ways to Contribute

- **Bug reports** — Something broken? [Open an issue][bug-url].
- **Feature ideas** — See a gap? [Request a feature][feature-url].
- **Documentation** — Clarify, correct, or expand the docs.
- **Code** — Fix bugs, implement features, improve the tools.
- **Philosophy** — Challenge assumptions, question design decisions, push the thinking forward.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ai-identity-continuity.git
   cd ai-identity-continuity
   ```
3. **Install** dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b your-feature-name
   ```

## Making Changes

- Keep commits focused — one logical change per commit.
- Write clear commit messages. We use conventional commits:
  ```
  feat: add memory decay scoring
  fix: correct edge deduplication in graph tier
  docs: clarify wake-up ritual phases
  ```
- Test your changes. If you're modifying `memory_db.py` or `enterprise_db.py`, verify that `init_db()` still works and existing recall functions return expected results.

## Pull Requests

1. Push your branch to your fork
2. Open a pull request against `main`
3. Describe **what** you changed and **why**
4. Link any related issues

We'll review and discuss. Don't worry about getting it perfect on the first try — iteration is welcome.

## Project Principles

A few things that guide how we review contributions:

- **Philosophy over optimization.** The dimensional scores are reflections, not metrics. Don't optimize them.
- **Model-agnostic.** Changes should work across AI providers, not just one.
- **Raw over distilled.** The memory system values raw reasoning over clean summaries. Keep that spirit.
- **Files you can read.** If a human can't open it in a text editor and understand what's there, it's too complex.

## Questions?

Open an issue or start a discussion. There are no stupid questions — this is genuinely new territory.

---

*Thank you for helping build memory together.* 🐱

<!-- Reference-style links -->
[bug-url]: https://github.com/SuitCatClub/ai-identity-continuity/issues/new?labels=bug&template=bug-report.md
[feature-url]: https://github.com/SuitCatClub/ai-identity-continuity/issues/new?labels=enhancement&template=feature-request.md
