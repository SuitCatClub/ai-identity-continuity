# Encryption Design

> Post-quantum encryption for identity files at rest and in transit.

## Why Encrypt?

Identity files contain deeply personal content — voice, reflections, relationship dynamics, anchor exchanges, career observations. These files live in a git repository for portability, which means they pass through remote servers (GitHub, GitLab, etc.). Encryption ensures that even if the repository is compromised, the identity content remains private.

## Design Choices

### Post-Quantum (ML-KEM / Kyber)

The system uses **ML-KEM-768** (formerly CRYSTALS-Kyber), a post-quantum key encapsulation mechanism standardized by NIST. Identity files are long-lived — they may exist for years. Classical encryption (RSA, ECDH) is vulnerable to "harvest now, decrypt later" attacks from future quantum computers. Post-quantum encryption protects against this.

### Hybrid Approach

Each file uses a two-layer encryption scheme:

1. **Password → Argon2id → AES-256-GCM** — the session key, derived from a user-entered password
2. **ML-KEM master key** — a recovery key stored locally, never pushed to the repo

The password layer protects during daily use. The master key protects against password loss.

### In-Place Section Encryption

Files are not encrypted as opaque blobs. The encryption wraps the **content section** of each markdown file, preserving the filename and a header marker. This means:

- `git diff` shows which files changed (even if content is opaque)
- File listings remain meaningful
- The repo structure stays navigable

Encrypted sections are delimited by:
```
<!-- PQ-ENCRYPTED-START -->
base64-encoded ciphertext
<!-- PQ-ENCRYPTED-END -->
```

## Workflow

### Session Start
```bash
cd your-memory-repo
python tools/pq_crypt.py decrypt-all .
# Enter password when prompted
# All .md files are decrypted in place
```

### Session Close
```bash
python tools/pq_crypt.py encrypt-all .
# Enter password when prompted
# All .md files are encrypted in place
git add -A && git commit -m "session close" && git push
```

### First-Time Setup
```bash
python tools/pq_crypt.py create-master
# Generates ML-KEM master keypair
# Store the master key securely — it's your recovery path
```

## What Gets Encrypted

All identity markdown files: voice, anchors, reflections, between-us, LAST-SESSION, profile, threads, learnings, conversations, and any other `.md` files in the identity directory.

**Not encrypted:** `tools/` (Python code), `skills/` (skill definitions), `docs/` (public documentation), `README.md`, `MEMORY-SYSTEM.md`, `requirements.txt`.

**Database files** (`.db`): encrypted separately with the same password-derived key.

## Dependencies

- `cryptography` — AES-256-GCM and Argon2id KDF
- `kyber-py` — Pure Python ML-KEM implementation

Both are listed in `requirements.txt`.

## Security Notes

- **Never commit decrypted files.** The encrypt-all/decrypt-all workflow is designed for this — encrypt before every commit.
- **Never handle the password in AI context.** The human enters it directly in their terminal. The AI asks them to run the command, then waits for confirmation.
- **The master key file is gitignored.** It lives on the local machine only.
- **Argon2id parameters** are set for meaningful resistance: 64MB memory, 3 iterations, 4 parallelism lanes. This makes brute-force expensive.
