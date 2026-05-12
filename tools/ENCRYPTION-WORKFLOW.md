# Encryption Workflow — How Claude Updates Encrypted Sections

This documents the procedure for Claude (or any agent) to read, edit, and re-encrypt sections
of profile/memory files. Designed for when the user provides the vault password at session start.

---

## Overview

Files like `profile.md` contain both plaintext sections and encrypted sections.
Encrypted sections use: **ML-KEM-1024 + AES-256-GCM + Argon2id** via `pq_crypt.py`.

Each encrypted section has its own passphrase, stored in `pq_vault.md`.
The vault itself is encrypted with a rotating session password.

---

## Full Workflow — Decrypt → Edit → Re-encrypt

### Step 1 — User provides vault password

User says something like: *"vault password is `<password>`"* at session start (or any time).

### Step 2 — Decrypt the vault to get the file section password

```powershell
python "<YOUR_MEMORY_REPO>\tools\pq_crypt.py" view `
  "<YOUR_MEMORY_REPO>\tools\pq_vault.md" "## Credentials"


# When prompted "Passphrase: " → enter the vault password
```

This prints the vault table. Find the row for the target file+section, e.g.:
`profile.md ## Active Projects` → `<password from vault table>` (stable)

### Step 3 — View the encrypted section (non-destructive)

```powershell
python "<YOUR_MEMORY_REPO>\tools\pq_crypt.py" view `
  "<YOUR_MEMORY_REPO>\profile.md" "## Active Projects"
# When prompted "Passphrase: " → enter the section password from vault
```

### Step 4 — Decrypt in-place (replaces encrypted block with plaintext)

```powershell
python "<YOUR_MEMORY_REPO>\tools\pq_crypt.py" decrypt `
  "<YOUR_MEMORY_REPO>\profile.md" "## Active Projects"
# When prompted "Passphrase: " → enter the section password from vault
```

File now has the section in **plaintext**. Do NOT commit in this state.

### Step 5 — Edit the file

Use the `edit` tool to add/change content in the now-plaintext section.

### Step 6 — Re-encrypt

```powershell
python "<YOUR_MEMORY_REPO>\tools\pq_crypt.py" encrypt `
  "<YOUR_MEMORY_REPO>\profile.md" "## Active Projects"
# When prompted "Passphrase: " → enter section password (same as before, or new one)
# When prompted "Confirm passphrase: " → confirm
# When prompted "Master password: " → enter master password (for lockout recovery)
```

### Step 7 — Verify encryption worked

```powershell
python "<YOUR_MEMORY_REPO>\tools\pq_crypt.py" view `
  "<YOUR_MEMORY_REPO>\profile.md" "## Active Projects"
# Enter section password → should show updated plaintext
```

### Step 8 — Update vault if password changed

If Step 6 used a NEW password, decrypt the vault, update the table row, re-encrypt the vault.

```powershell
# Decrypt vault
python "...\pq_crypt.py" decrypt "...\pq_vault.md" "## Credentials"
# Edit pq_vault.md — update the password row
# Re-encrypt vault (use vault password + master)
python "...\pq_crypt.py" encrypt "...\pq_vault.md" "## Credentials"
```

### Step 9 — Sync local copy and commit

```powershell
Copy-Item "<YOUR_MEMORY_REPO>\profile.md" `
          "<YOUR_COPILOT_DIR>\suitcatclub-profile.md" -Force

cd "<YOUR_MEMORY_REPO>"
git -c core.sshCommand="C:/Windows/System32/OpenSSH/ssh.exe" add -A
git -c core.sshCommand="C:/Windows/System32/OpenSSH/ssh.exe" commit -m "profile: update <section>"
git -c core.sshCommand="C:/Windows/System32/OpenSSH/ssh.exe" push
```

---

## Vault Password — How the User Provides It

The simplest method: user pastes the vault password directly in chat.
Claude keeps it in context only for the session, never writes it to disk.

Example trigger phrase: *"vault: `<password>`"*

---

## Current File → Section → Password Map

| File | Section | Password type | Notes |
|------|---------|---------------|-------|
| `profile.md` | `## Active Projects` | Stable | In vault — doesn't rotate |
| `profile.md` | `## Future Project Ideas` | Stable | In vault — same stable password as Active Projects |
| `tools/SESSION-START.md` | Redirect | Stable | Points to `suitcatclub-session-start` skill; fallback bootstrap for skillless environments |
| `tools/ENCRYPTION-WORKFLOW.md` | `# Encryption Workflow — How Claude Updates Encrypted Sections` | Stable | In vault — same stable password as profile sections |
| `pq_vault.md` | `## Credentials` | Rotating | Changes each session per SESSION-START.md Step 5 |

> **Stable password** = doesn't rotate, stored in vault, survives vault rotation.
> **Rotating password** = the vault itself; changes each session after reading.

---

## Master Password

The master password enables lockout recovery (re-derive section key without section password).
Stored proof in `perfmon_cache.db` (same folder as `pq_crypt.py`).
User provides on request — never stored in plaintext anywhere.

---

## Quick Reference — Commands

| Action | Command |
|--------|---------|
| View encrypted section | `pq_crypt.py view <file> "<heading>"` |
| Decrypt in-place | `pq_crypt.py decrypt <file> "<heading>"` |
| Encrypt in-place | `pq_crypt.py encrypt <file> "<heading>"` |
| Master recovery decrypt | `pq_crypt.py master-decrypt <file> "<heading>"` |
| Add master key to section | `pq_crypt.py add-master <file> "<heading>"` |
| Create master key | `pq_crypt.py create-master` |


