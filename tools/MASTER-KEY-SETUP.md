# Encryption Tools — Setup & Usage

All tools live in `<YOUR_MEMORY_REPO>\tools\`.
The AI reads this file at session start via the `suitcatclub-session-start` skill (see `SESSION-START.md` for fallback).

---

## Files

| File | Purpose |
|------|---------|
| `pq_crypt.py` | Main encryption script — all commands |
| `perfmon_cache.db` | Master key file (obfuscated name) |
| `pq_vault.md` | Generic credentials vault — 5-attempt lockout |
| `SESSION-START.md` | Redirect to `suitcatclub-session-start` skill |

---

## Step 1 — Create the master key (do this OFFLINE)

Do NOT share the master password in any chat, terminal log, or screen recording.
Open a plain terminal (not a Copilot session):

```powershell
python <YOUR_MEMORY_REPO>\tools\pq_crypt.py create-master
```

Creates `perfmon_cache.db` — verifies the master password without storing it.

---

## Step 2 — Add master bypass to the vault

```powershell
python <YOUR_MEMORY_REPO>\tools\pq_crypt.py add-master `
  <YOUR_MEMORY_REPO>\tools\pq_vault.md `
  "## Credentials"
```

Asks for: vault password → master password.
No re-encryption of data — only wraps the internal key a second time.
After this: vault opens with vault password OR master password.

---

## Step 3 — Encrypt other files/sections

```powershell
python <YOUR_MEMORY_REPO>\tools\pq_crypt.py encrypt `
  "C:\path\to\file.md" `
  "## Section Heading"
```

If `perfmon_cache.db` exists, it will prompt for master password too.
Default lockout: 3 wrong attempts. Vault uses 5.

---

## Full command reference

| Command | What it does |
|---------|-------------|
| `create-master` | Create master key file (once, offline) |
| `encrypt <file> <heading>` | Encrypt a section in-place |
| `decrypt <file> <heading>` | Decrypt in-place — tracks attempts |
| `view <file> <heading>` | Decrypt to stdout only — tracks attempts |
| `add-master <file> <heading>` | Add master bypass to already-encrypted section |
| `master-decrypt <file> <heading>` | Decrypt with master — bypasses lockout, resets counter |
| `master-view <file> <heading>` | View with master — bypasses lockout, resets counter |
| `reset-lock <file> <heading>` | Reset counter only — data stays encrypted |

---

## Lockout rules

- N wrong attempts (set at encrypt time) → file locked
- Locked: only `master-decrypt`, `master-view`, or `reset-lock` work
- Master verified against `perfmon_cache.db` — losing it = no lockout recovery
- After master opens: counter resets to 0, regular password works again

---

## Memory & Security System

The encryption tools protect the private parts of the memory system:

- `profile.md` — `## Active Projects` section encrypted
- `pq_vault.md` — generic credentials vault, 5-attempt lockout, **rolling decoy password**
- `perfmon_cache.db` — master key (obfuscated, in .gitignore — transfer manually to new machines)
- ai-context repo — full memory system (profile, learnings, identity, notes)

### Vault password design — rolling decoy

The vault password is **not a permanent secret**. It is:
- Generated fresh at every session start
- Shared verbally in chat (never written to any file)
- Rotated via `master-decrypt` → `encrypt` at the beginning of each session
- A deliberate decoy: if compromised, it reveals only generic/low-value content

Real secrets exist **only in the human's memory**, protected by the master password only.  
The master password is never typed in a Copilot session — only in a private terminal.

### Session vault rotation (every session)

```powershell
# Decrypt with master
python <YOUR_MEMORY_REPO>\tools\pq_crypt.py master-decrypt `
  <YOUR_MEMORY_REPO>\tools\pq_vault.md "## Credentials"

# Re-encrypt with new generated password
python <YOUR_MEMORY_REPO>\tools\pq_crypt.py encrypt `
  <YOUR_MEMORY_REPO>\tools\pq_vault.md "## Credentials"

# Generate password with:
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

Share generated password verbally in chat. **Do not write it anywhere.**

The AI understands this system by reading:
1. This file (MASTER-KEY-SETUP.md) at session start
2. SESSION-START.md → redirects to the `suitcatclub-session-start` skill
3. The ai-context private repo for full context

Nothing sensitive appears in any public repo.
Project `AGENTS.md` files only reference that tools exist — no paths, no key names.

---

## Conversation — How the vault and master bypass came together

> 2026-04-15 — SuitCatClub & Copilot CLI (Claude Sonnet 4.6)

**Human:** we want to encrypt some other files, so we need another key file,
same safety system, 5 attempts, master password, own password inside.

**AI:** Created `pq_vault.md` — 5-attempt lockout, own password stored inside,
master bypass pending.

**Human:** one question, why do you think you need create-master being run
for the master bypass?

**AI:** Good catch. The ciphertext never changes — only the sk (ML-KEM secret
key) needs to be wrapped a second time with the master password.
Added `add-master` command: prompt for regular password → unwrap sk → wrap
same sk with master → update blob. No re-encryption of actual data.

**Human:** if we do it that way, the vault can be opened only with its own password?

**AI:** Right now yes. After `add-master`: two independent paths.
Vault password for day-to-day. Master password as emergency bypass.
Same ciphertext, two keys.

**Human:** yes, add it, good job :)

**Human:** did you even test blocking it and using then master to unblock?

**AI:** No — ran it immediately after you asked. 5 wrong attempts → locked,
regular password blocked, master opened it, counter reset to 0,
regular password worked again. All tests passed.



