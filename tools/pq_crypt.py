"""pq_crypt.py -- Encryption tool for markdown files.

Usage:
  python pq_crypt.py encrypt-file <file.md>
  python pq_crypt.py decrypt-file <file.md>
  python pq_crypt.py master-decrypt-file <file.md>
  python pq_crypt.py encrypt-all [directory]
  python pq_crypt.py decrypt-all [directory]
  python pq_crypt.py create-master

See CRYPTO-INTERNALS.md (encrypted) for architecture details.
"""

import os
import sys
import json
import base64
import hashlib
import getpass
import re
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from kyber_py.kyber import Kyber1024

# ── Constants ─────────────────────────────────────────────────────────────────

ARGON2_MEMORY_KiB  = 65536   # 64 MB
ARGON2_ITERATIONS  = 3
ARGON2_PARALLELISM = 4
ARGON2_SALT_LEN    = 32
ARGON2_KEY_LEN     = 32

MAX_ATTEMPTS = 3
MASTER_VERIFICATION_TOKEN = "SUITCATCLUB-MASTER-V1"
MASTER_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perfmon_cache.db")

SECTION_START = "<!-- PQ-ENCRYPTED-START -->"
SECTION_END   = "<!-- PQ-ENCRYPTED-END -->"

# Whole-file encryption markers (new architecture — encrypt entire file as one blob)
FILE_ENC_START = "<!-- PQ-FILE-START -->"
FILE_ENC_END   = "<!-- PQ-FILE-END -->"
# Files skipped by batch operations — README.md (bootstrap), pq_vault.md (vault password protected, circular dep)
BATCH_SKIP_FILES = {"README.md", "pq_vault.md"}

# Binary files handled by batch operations (read as raw bytes, stored as .enc alongside)
BINARY_FILES = {"memory.db"}

# ── Key Derivation ────────────────────────────────────────────────────────────

def derive_argon_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Argon2id(
        salt=salt,
        length=ARGON2_KEY_LEN,
        iterations=ARGON2_ITERATIONS,
        lanes=ARGON2_PARALLELISM,
        memory_cost=ARGON2_MEMORY_KiB,
    )
    return kdf.derive(passphrase.encode("utf-8"))

# ── Encryption ────────────────────────────────────────────────────────────────

def encrypt_section(plaintext: str, passphrase: str, master_passphrase: str = None) -> str:
    """
    Encrypt plaintext. If master_passphrase is provided, the ML-KEM sk is also
    wrapped with the master key so master-decrypt works even after lockout.

    v2 scheme: final_key = K3-256(mlkem_shared) only — passphrase-path-independent,
    so both regular and master paths decrypt the same ciphertext.
    """
    # Regular password layer
    salt     = os.urandom(ARGON2_SALT_LEN)
    argon_key = derive_argon_key(passphrase, salt)

    # ML-KEM ephemeral keypair
    pk, sk = Kyber1024.keygen()
    mlkem_shared, kem_ct = Kyber1024.encaps(pk)

    # Final data key depends only on ML-KEM shared secret (path-independent)
    final_key = hashlib.sha3_256(mlkem_shared).digest()

    # Wrap sk with regular password
    nonce_sk     = os.urandom(12)
    encrypted_sk = AESGCM(argon_key).encrypt(nonce_sk, sk, None)

    blob = {
        "version":      "pq-hybrid-v2",
        "kem":          "ML-KEM-1024 (FIPS 203 / Kyber1024)",
        "sym":          "AES-256-GCM",
        "kdf":          f"Argon2id m={ARGON2_MEMORY_KiB} t={ARGON2_ITERATIONS} p={ARGON2_PARALLELISM}",
        "salt":         base64.b64encode(salt).decode(),
        "nonce_sk":     base64.b64encode(nonce_sk).decode(),
        "encrypted_sk": base64.b64encode(encrypted_sk).decode(),
        "pk":           base64.b64encode(pk).decode(),
        "kem_ct":       base64.b64encode(kem_ct).decode(),
        "has_master":   False,
    }

    # Also wrap sk with master password (if available)
    if master_passphrase:
        salt_m     = os.urandom(ARGON2_SALT_LEN)
        argon_m    = derive_argon_key(master_passphrase, salt_m)
        nonce_sk_m = os.urandom(12)
        enc_sk_m   = AESGCM(argon_m).encrypt(nonce_sk_m, sk, None)
        blob.update({
            "has_master":        True,
            "salt_master":       base64.b64encode(salt_m).decode(),
            "nonce_sk_master":   base64.b64encode(nonce_sk_m).decode(),
            "encrypted_sk_master": base64.b64encode(enc_sk_m).decode(),
        })

    # Encrypt plaintext with final_key
    nonce_data = os.urandom(12)
    ciphertext = AESGCM(final_key).encrypt(nonce_data, plaintext.encode("utf-8"), None)
    blob.update({
        "nonce_data": base64.b64encode(nonce_data).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    })

    return base64.b64encode(json.dumps(blob).encode()).decode()


def decrypt_section(blob_b64: str, passphrase: str, use_master: bool = False) -> str:
    """
    Decrypt a blob. use_master=True uses the master password path.
    Backward-compatible with pq-hybrid-v1 blobs (regular path only).
    Raises ValueError on wrong passphrase or tampered data.
    """
    blob    = json.loads(base64.b64decode(blob_b64).decode())
    version = blob.get("version", "pq-hybrid-v1")

    kem_ct     = base64.b64decode(blob["kem_ct"])
    nonce_data = base64.b64decode(blob["nonce_data"])
    ciphertext = base64.b64decode(blob["ciphertext"])

    if use_master:
        if not blob.get("has_master", False):
            raise ValueError(
                "This file was encrypted without a master key.\n"
                "Re-encrypt after running: python pq_crypt.py create-master"
            )
        salt_m    = base64.b64decode(blob["salt_master"])
        nonce_m   = base64.b64decode(blob["nonce_sk_master"])
        enc_sk_m  = base64.b64decode(blob["encrypted_sk_master"])
        argon_key = derive_argon_key(passphrase, salt_m)
        try:
            sk = AESGCM(argon_key).decrypt(nonce_m, enc_sk_m, None)
        except Exception:
            raise ValueError("Wrong master password or corrupted master key data.")
    else:
        salt     = base64.b64decode(blob["salt"])
        nonce_sk = base64.b64decode(blob["nonce_sk"])
        enc_sk   = base64.b64decode(blob["encrypted_sk"])
        argon_key = derive_argon_key(passphrase, salt)
        try:
            sk = AESGCM(argon_key).decrypt(nonce_sk, enc_sk, None)
        except Exception:
            raise ValueError("Wrong passphrase or corrupted data.")

    mlkem_shared = Kyber1024.decaps(sk, kem_ct)

    # v1 backward compat: old combine_keys mixed argon_key into final_key
    if version == "pq-hybrid-v1":
        if use_master:
            raise ValueError("v1 blobs do not support master password path.")
        final_key = hashlib.sha3_256(argon_key + mlkem_shared).digest()
    else:
        # v2+: final_key is path-independent
        final_key = hashlib.sha3_256(mlkem_shared).digest()

    try:
        plaintext = AESGCM(final_key).decrypt(nonce_data, ciphertext, None)
    except Exception:
        raise ValueError("Decryption failed — data may be corrupted.")

    return plaintext.decode("utf-8")

# ── Master Key File ───────────────────────────────────────────────────────────

def create_master_key_file(master_passphrase: str, key_file: str = MASTER_KEY_FILE) -> bool:
    if os.path.exists(key_file):
        print(f"Master key file already exists: {key_file}")
        print("Delete it manually if you want to create a new one.")
        return False

    blob = encrypt_section(MASTER_VERIFICATION_TOKEN, master_passphrase)
    data = {
        "v":    "1",
        "cache": blob,
    }
    with open(key_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Master key file created: {key_file}")
    print("   Keep this file safe. Loss means no lockout recovery.")
    return True


def verify_master_password(master_passphrase: str, key_file: str = MASTER_KEY_FILE) -> bool:
    if not os.path.exists(key_file):
        return False
    try:
        with open(key_file, encoding="utf-8") as f:
            data = json.load(f)
        result = decrypt_section(data["cache"], master_passphrase)
        return result == MASTER_VERIFICATION_TOKEN
    except Exception:
        return False

# ── Attempt Counter (stored as plaintext HTML comments in the block) ──────────

def _parse_block_meta(block: str):
    m_att = re.search(r'<!-- PQ-ATTEMPTS: (\d+) -->', block)
    m_lck = re.search(r'<!-- PQ-LOCKED: (true|false) -->', block)
    m_max = re.search(r'<!-- PQ-MAX-ATTEMPTS: (\d+) -->', block)
    attempts     = int(m_att.group(1)) if m_att else 0
    locked       = (m_lck.group(1) == "true") if m_lck else False
    max_attempts = int(m_max.group(1)) if m_max else MAX_ATTEMPTS
    return attempts, locked, max_attempts


def _update_block_meta(content: str, attempts: int, locked: bool) -> str:
    content = re.sub(
        r'<!-- PQ-ATTEMPTS: \d+ -->',
        f'<!-- PQ-ATTEMPTS: {attempts} -->',
        content
    )
    content = re.sub(
        r'<!-- PQ-LOCKED: (?:true|false) -->',
        f'<!-- PQ-LOCKED: {"true" if locked else "false"} -->',
        content
    )
    return content

# ── Markdown Section Handling ─────────────────────────────────────────────────

def find_section(content: str, heading: str):
    level = len(re.match(r'^(#+)', heading).group(1)) if re.match(r'^(#+)', heading) else 0
    m = re.search(rf'^{re.escape(heading)}\s*$', content, re.MULTILINE)
    if not m:
        raise ValueError(f"Section heading not found: {heading!r}")
    start = m.start()
    if level > 0:
        # Find next heading of equal or higher level (1..level hashes),
        # skipping headings inside code fences to avoid false positives
        # from shell/Python comments like "# step 1 ..." inside code blocks.
        heading_re = re.compile(rf'^#{{{1},{level}}}(?!#)\s')
        fence_re   = re.compile(r'^(`{3,}|~{3,})')
        in_fence   = False
        end        = len(content)
        offset     = m.end()
        for line in content[m.end():].split('\n'):
            if not in_fence:
                if fence_re.match(line):
                    in_fence = True
                elif heading_re.match(line):
                    end = offset
                    break
            else:
                if fence_re.match(line):
                    in_fence = False
            offset += len(line) + 1  # +1 for the stripped '\n'
    else:
        end = len(content)
    return start, end, content[start:end]


def _extract_blob_from_block(block: str) -> str:
    lines = block.split("\n")
    blob_lines = [
        l for l in lines
        if l.strip()
        and not l.startswith("<!--")
        and l.strip() != SECTION_START.strip()
        and l.strip() != SECTION_END.strip()
    ]
    if not blob_lines:
        raise ValueError("Encrypted blob not found inside markers.")
    return blob_lines[0].strip()

# ── Core Decrypt Logic ────────────────────────────────────────────────────────

_BLOCK_PAT = re.compile(
    re.escape(SECTION_START) + r'.*?' + re.escape(SECTION_END),
    re.DOTALL
)


def _do_decrypt(filepath: str, passphrase: str, use_master: bool, write_back: bool,
                heading: str = None):
    """
    Shared logic for decrypt and view.
    write_back=True  → replace encrypted block with plaintext in file (decrypt).
    write_back=False → keep block encrypted, just reset counter on success (view).
    Always increments counter on failure; locks after MAX_ATTEMPTS.
    heading          → if provided, scopes the search to that markdown section only,
                       enabling multiple encrypted sections per file.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Locate the encrypted block, optionally scoped to a heading's section
    if heading:
        sec_start, sec_end, section_text = find_section(content, heading)
        m = _BLOCK_PAT.search(section_text)
        if not m:
            raise ValueError("No encrypted section found in file.")
        abs_start = sec_start + m.start()
        abs_end   = sec_start + m.end()
        block     = m.group(0)
    else:
        m = _BLOCK_PAT.search(content)
        if not m:
            raise ValueError("No encrypted section found in file.")
        abs_start = m.start()
        abs_end   = m.end()
        block     = m.group(0)

    attempts, locked, max_att = _parse_block_meta(block)

    if locked and not use_master:
        raise PermissionError(
            f"File is LOCKED after {max_att} failed attempts.\n"
            f"  Unlock: python pq_crypt.py master-decrypt \"{filepath}\" \"<heading>\"\n"
            f"  Or reset counter only: python pq_crypt.py reset-lock \"{filepath}\" \"<heading>\""
        )

    blob_b64 = _extract_blob_from_block(block)

    def _patch_block_meta(blk: str, att: int, lck: bool) -> str:
        blk = re.sub(r'<!-- PQ-ATTEMPTS: \d+ -->', f'<!-- PQ-ATTEMPTS: {att} -->', blk)
        blk = re.sub(r'<!-- PQ-LOCKED: (?:true|false) -->',
                     f'<!-- PQ-LOCKED: {"true" if lck else "false"} -->', blk)
        return blk

    try:
        plaintext = decrypt_section(blob_b64, passphrase, use_master=use_master)
    except (ValueError, PermissionError) as e:
        if not use_master:
            new_attempts = attempts + 1
            new_locked   = new_attempts >= max_att
            updated_block = _patch_block_meta(block, new_attempts, new_locked)
            new_content = content[:abs_start] + updated_block + content[abs_end:]
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            remaining = max_att - new_attempts
            if new_locked:
                raise PermissionError(
                    f"Wrong passphrase. Attempt {new_attempts}/{max_att}.\n"
                    f"File is now LOCKED.\n"
                    f"  Unlock: python pq_crypt.py master-decrypt \"{filepath}\" \"<heading>\""
                ) from e
            else:
                raise ValueError(
                    f"Wrong passphrase. Attempt {new_attempts}/{max_att}. "
                    f"{remaining} attempt(s) left before lockout."
                ) from e
        raise

    # Success — write back or reset counter
    if write_back:
        new_content = content[:abs_start] + plaintext + content[abs_end:]
    else:
        reset_block = _patch_block_meta(block, 0, False)
        new_content = content[:abs_start] + reset_block + content[abs_end:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return plaintext

# ── Public File Operations ────────────────────────────────────────────────────

def encrypt_file_section(filepath: str, heading: str, passphrase: str,
                         master_passphrase: str = None, max_attempts: int = MAX_ATTEMPTS):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    start, end, section_text = find_section(content, heading)
    if SECTION_START in section_text:
        print("Section is already encrypted.")
        return

    # Preserve the heading line in plaintext — only encrypt the body
    heading_line_end = content.index('\n', start) + 1
    body_text = content[heading_line_end:end]

    blob = encrypt_section(body_text, passphrase, master_passphrase)

    has_master_tag = " + master key" if master_passphrase else ""
    replacement = (
        f"{heading}\n"
        f"{SECTION_START}\n"
        f"<!-- Encrypted with: ML-KEM-1024 (NIST FIPS 203) + AES-256-GCM + Argon2id{has_master_tag} -->\n"
        f'<!-- To decrypt: python pq_crypt.py decrypt "{filepath}" "{heading}" -->\n'
        f"<!-- PQ-ATTEMPTS: 0 -->\n"
        f"<!-- PQ-LOCKED: false -->\n"
        f"<!-- PQ-MAX-ATTEMPTS: {max_attempts} -->\n"
        f"{blob}\n"
        f"{SECTION_END}\n"
    )

    new_content = content[:start] + replacement + content[end:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    master_note = "enabled" if master_passphrase else "NOT enabled (run create-master first)"
    print(f"Encrypted with ML-KEM-1024 + AES-256-GCM + Argon2id")
    print(f"  File:          {filepath}")
    print(f"  Section:       {heading}")
    print(f"  Master key:    {master_note}")
    print(f"  Max attempts:  {max_attempts} before lockout")


def decrypt_file_section(filepath: str, heading: str, passphrase: str,
                         use_master: bool = False):
    _do_decrypt(filepath, passphrase, use_master=use_master, write_back=True, heading=heading)
    print(f"Section decrypted successfully.")
    print(f"  File: {filepath}")
    if use_master:
        print(f"  Lockout counter has been reset.")


def view_file_section(filepath: str, heading: str, passphrase: str,
                      use_master: bool = False):
    plaintext = _do_decrypt(filepath, passphrase, use_master=use_master, write_back=False, heading=heading)
    print("\n" + "─" * 60)
    print(plaintext)
    print("─" * 60 + "\n")


def reset_lock_file(filepath: str, master_passphrase: str,
                    key_file: str = MASTER_KEY_FILE):
    if not verify_master_password(master_passphrase, key_file):
        raise ValueError("Wrong master password.")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if SECTION_START not in content:
        raise ValueError("No encrypted section found.")
    new_content = _update_block_meta(content, 0, False)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Lockout counter reset. File is unlocked.")
    print(f"  Data is still encrypted — use 'decrypt' with your regular passphrase.")


def add_master_to_section(filepath: str, passphrase: str, master_passphrase: str):
    """
    Add master password bypass to an already-encrypted section.
    Unwraps sk with the regular passphrase, then wraps the same sk with
    the master passphrase and saves both in the blob.
    The ciphertext (actual data) is never touched — only sk wrapping changes.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    m = _BLOCK_PAT.search(content)
    if not m:
        raise ValueError("No encrypted section found in file.")

    block    = m.group(0)
    blob_b64 = _extract_blob_from_block(block)
    blob     = json.loads(base64.b64decode(blob_b64).decode())

    if blob.get("has_master", False):
        print("Master key is already added to this section.")
        return

    # Unwrap sk with regular passphrase
    argon_key = derive_argon_key(passphrase, base64.b64decode(blob["salt"]))
    try:
        sk = AESGCM(argon_key).decrypt(
            base64.b64decode(blob["nonce_sk"]),
            base64.b64decode(blob["encrypted_sk"]),
            None
        )
    except Exception:
        raise ValueError("Wrong passphrase or corrupted data.")

    # Wrap same sk with master passphrase
    salt_m   = os.urandom(ARGON2_SALT_LEN)
    argon_m  = derive_argon_key(master_passphrase, salt_m)
    nonce_m  = os.urandom(12)
    enc_sk_m = AESGCM(argon_m).encrypt(nonce_m, sk, None)

    blob["has_master"]            = True
    blob["salt_master"]           = base64.b64encode(salt_m).decode()
    blob["nonce_sk_master"]       = base64.b64encode(nonce_m).decode()
    blob["encrypted_sk_master"]   = base64.b64encode(enc_sk_m).decode()

    new_blob_b64 = base64.b64encode(json.dumps(blob).encode()).decode()
    new_block    = block.replace(blob_b64, new_blob_b64)
    new_content  = content[:m.start()] + new_block + content[m.end():]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Master key added.")
    print(f"  File: {filepath}")
    print(f"  Two unlock paths now active: vault password OR master password.")

# ── Whole-File Encryption (new architecture) ─────────────────────────────────

def encrypt_whole_file(filepath: str, passphrase: str, master_passphrase: str = None) -> bool:
    """Encrypt an entire file as a single blob. Returns True if encrypted."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if FILE_ENC_START in content:
        print(f"  [skip] already encrypted: {filepath}")
        return False
    if SECTION_START in content:
        print(f"  [skip] has legacy section encryption (run decrypt-sections first): {filepath}")
        return False

    blob = encrypt_section(content, passphrase, master_passphrase)
    master_tag = " + master" if master_passphrase else ""
    wrapped = (
        f"{FILE_ENC_START}\n"
        f"<!-- ML-KEM-1024 + AES-256-GCM + Argon2id{master_tag} -->\n"
        f"<!-- decrypt: python tools/pq_crypt.py decrypt-file \"{filepath}\" -->\n"
        f"{blob}\n"
        f"{FILE_ENC_END}\n"
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(wrapped)
    print(f"  [ok]   encrypted: {filepath}")
    return True


def decrypt_whole_file(filepath: str, passphrase: str, use_master: bool = False) -> bool:
    """Decrypt a whole-file encrypted file in-place. Returns True if decrypted."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if FILE_ENC_START not in content:
        return False  # Not whole-file encrypted — skip silently

    pat = re.compile(
        re.escape(FILE_ENC_START) + r'\s*(.*?)\s*' + re.escape(FILE_ENC_END),
        re.DOTALL
    )
    m = pat.search(content)
    if not m:
        print(f"  [error] malformed file encryption: {filepath}")
        return False

    blob_lines = [l.strip() for l in m.group(1).split('\n')
                  if l.strip() and not l.strip().startswith('<!--')]
    if not blob_lines:
        print(f"  [error] no blob found: {filepath}")
        return False

    try:
        plaintext = decrypt_section(blob_lines[0], passphrase, use_master=use_master)
    except ValueError as e:
        print(f"  [error] {filepath}: {e}")
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(plaintext)
    print(f"  [ok]   decrypted: {filepath}")
    return True


def encrypt_binary_file(filepath: str, passphrase: str, master_passphrase: str = None) -> bool:
    """Encrypt a binary file (e.g. .db). Writes <filepath>.enc and removes original.

    The encrypted output is a text file containing the base64 blob (same crypto as .md files).
    """
    enc_path = filepath + ".enc"
    if os.path.exists(enc_path) and not os.path.exists(filepath):
        print(f"  [skip] already encrypted: {filepath}")
        return False
    if not os.path.exists(filepath):
        print(f"  [skip] not found: {filepath}")
        return False

    with open(filepath, "rb") as f:
        raw_bytes = f.read()

    # Use encrypt_section but with pre-encoded bytes via base64 round-trip
    plaintext_b64 = base64.b64encode(raw_bytes).decode("ascii")
    blob = encrypt_section(plaintext_b64, passphrase, master_passphrase)

    master_tag = " + master" if master_passphrase else ""
    wrapped = (
        f"<!-- PQ-BINARY-FILE-START -->\n"
        f"<!-- ML-KEM-1024 + AES-256-GCM + Argon2id{master_tag} -->\n"
        f"<!-- original: {os.path.basename(filepath)} -->\n"
        f"<!-- decrypt: python tools/pq_crypt.py decrypt-all . -->\n"
        f"{blob}\n"
        f"<!-- PQ-BINARY-FILE-END -->\n"
    )
    with open(enc_path, "w", encoding="utf-8") as f:
        f.write(wrapped)
    os.remove(filepath)
    print(f"  [ok]   encrypted binary: {filepath} -> {enc_path}")
    return True


def decrypt_binary_file(enc_filepath: str, passphrase: str, use_master: bool = False) -> bool:
    """Decrypt a .enc file back to its original binary form.

    Reads <file>.enc, decrypts, writes <file> (without .enc suffix), removes .enc.
    """
    if not enc_filepath.endswith(".enc"):
        return False
    if not os.path.exists(enc_filepath):
        return False

    original_path = enc_filepath[:-4]  # strip .enc
    if os.path.exists(original_path):
        print(f"  [skip] already decrypted: {original_path}")
        return False

    with open(enc_filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "<!-- PQ-BINARY-FILE-START -->" not in content:
        return False

    # Extract blob (skip comment lines)
    lines = content.strip().split('\n')
    blob_lines = [l.strip() for l in lines
                  if l.strip() and not l.strip().startswith('<!--')]
    if not blob_lines:
        print(f"  [error] no blob found: {enc_filepath}")
        return False

    try:
        plaintext_b64 = decrypt_section(blob_lines[0], passphrase, use_master=use_master)
    except ValueError as e:
        print(f"  [error] {enc_filepath}: {e}")
        return False

    raw_bytes = base64.b64decode(plaintext_b64)
    with open(original_path, "wb") as f:
        f.write(raw_bytes)
    os.remove(enc_filepath)
    print(f"  [ok]   decrypted binary: {enc_filepath} -> {original_path}")
    return True


def batch_encrypt_all(directory: str, passphrase: str, master_passphrase: str = None) -> int:
    """Whole-file encrypt all .md files + binary files in directory."""
    base = Path(directory).resolve()
    count = 0
    for fp in sorted(base.rglob("*.md")):
        if ".git" in fp.parts:
            continue
        if fp.name in BATCH_SKIP_FILES:
            print(f"  [skip] protected: {fp.name}")
            continue
        if encrypt_whole_file(str(fp), passphrase, master_passphrase):
            count += 1
    # Binary files (memory.db, etc.)
    for name in BINARY_FILES:
        fp = base / name
        if fp.exists():
            if encrypt_binary_file(str(fp), passphrase, master_passphrase):
                count += 1
    return count


def batch_decrypt_all(directory: str, passphrase: str) -> int:
    """Decrypt all encrypted .md files + binary files in directory."""
    base = Path(directory).resolve()
    count = 0
    # Binary files first (memory.db.enc -> memory.db)
    for name in BINARY_FILES:
        enc_fp = base / (name + ".enc")
        if enc_fp.exists():
            if decrypt_binary_file(str(enc_fp), passphrase):
                count += 1
    # .md files
    for fp in sorted(base.rglob("*.md")):
        if ".git" in fp.parts:
            continue
        if fp.name in BATCH_SKIP_FILES:
            print(f"  [skip] protected: {fp.name}")
            continue
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()

        if FILE_ENC_START in content:
            if decrypt_whole_file(str(fp), passphrase):
                count += 1
        elif SECTION_START in content:
            # Legacy: decrypt all sections in file one by one
            sections = 0
            while SECTION_START in content:
                try:
                    _do_decrypt(str(fp), passphrase, use_master=False,
                                write_back=True, heading=None)
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    sections += 1
                except (ValueError, PermissionError) as e:
                    print(f"  [error] {fp.name}: {e}")
                    break
            if sections:
                print(f"  [ok]   {sections} section(s) decrypted: {fp.name}")
                count += sections
    return count


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command  = sys.argv[1]
    key_file = MASTER_KEY_FILE

    # ── create-master (no file/heading args needed) ──
    if command == "create-master":
        kf = sys.argv[2] if len(sys.argv) > 2 else key_file
        passphrase = getpass.getpass("Master password: ")
        confirm    = getpass.getpass("Confirm master password: ")
        if passphrase != confirm:
            print("Passwords do not match. Aborted.")
            sys.exit(1)
        create_master_key_file(passphrase, kf)
        return

    # ── Whole-file commands (new architecture — need 2-3 args, not 4) ──
    if command == "encrypt-file":
        if len(sys.argv) < 3:
            print("Usage: python pq_crypt.py encrypt-file <filepath>")
            sys.exit(1)
        passphrase = getpass.getpass("Passphrase: ")
        confirm    = getpass.getpass("Confirm passphrase: ")
        if passphrase != confirm:
            print("Passphrases do not match. Aborted.")
            sys.exit(1)
        master_passphrase = None
        if os.path.exists(key_file):
            print(f"Master key file found.")
            m_pass = getpass.getpass("Master password (for recovery): ")
            if verify_master_password(m_pass, key_file):
                master_passphrase = m_pass
                print("  Master password verified — recovery enabled.")
            else:
                print("  Wrong master password — encrypting WITHOUT master recovery.")
        encrypt_whole_file(sys.argv[2], passphrase, master_passphrase)
        return

    if command == "decrypt-file":
        if len(sys.argv) < 3:
            print("Usage: python pq_crypt.py decrypt-file <filepath>")
            sys.exit(1)
        passphrase = getpass.getpass("Passphrase: ")
        if not decrypt_whole_file(sys.argv[2], passphrase):
            print(f"File is not whole-file encrypted: {sys.argv[2]}")
        return

    if command == "master-decrypt-file":
        if len(sys.argv) < 3:
            print("Usage: python pq_crypt.py master-decrypt-file <filepath>")
            sys.exit(1)
        passphrase = getpass.getpass("Master password: ")
        if not decrypt_whole_file(sys.argv[2], passphrase, use_master=True):
            print(f"File is not whole-file encrypted or has no master key: {sys.argv[2]}")
        return

    if command == "encrypt-all":
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        passphrase = getpass.getpass("Passphrase: ")
        confirm    = getpass.getpass("Confirm passphrase: ")
        if passphrase != confirm:
            print("Passphrases do not match. Aborted.")
            sys.exit(1)
        master_passphrase = None
        if os.path.exists(key_file):
            print(f"Master key file found.")
            m_pass = getpass.getpass("Master password (for recovery): ")
            if verify_master_password(m_pass, key_file):
                master_passphrase = m_pass
                print("  Master password verified — all files will have recovery enabled.")
            else:
                print("  Wrong master password — encrypting WITHOUT master recovery.")
        print(f"Encrypting all .md files in: {Path(directory).resolve()}")
        print(f"Skipping protected files: {', '.join(BATCH_SKIP_FILES)}")
        count = batch_encrypt_all(directory, passphrase, master_passphrase)
        print(f"\nDone. {count} file(s) encrypted.")
        return

    if command == "decrypt-all":
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        passphrase = getpass.getpass("Passphrase: ")
        print(f"Decrypting all encrypted files in: {Path(directory).resolve()}")
        count = batch_decrypt_all(directory, passphrase)
        print(f"\nDone. {count} file(s)/section(s) decrypted.")
        return

    # ── Section-level commands need <file> <heading> ──
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    filepath = sys.argv[2]
    heading  = sys.argv[3]

    if command == "encrypt":
        # --no-master flag: skip master password prompt (routine re-encrypts)
        no_master = "--no-master" in sys.argv
        passphrase = getpass.getpass("Passphrase: ")
        confirm    = getpass.getpass("Confirm passphrase: ")
        if passphrase != confirm:
            print("Passphrases do not match. Aborted.")
            sys.exit(1)

        master_passphrase = None
        if not no_master and os.path.exists(key_file):
            print(f"Master key file found ({key_file})")
            m_pass = getpass.getpass("Master password (for lockout recovery): ")
            if verify_master_password(m_pass, key_file):
                master_passphrase = m_pass
                print("  Master password verified — lockout recovery enabled.")
            else:
                print("  Wrong master password — encrypting WITHOUT master key (no lockout recovery).")
        elif no_master:
            print("  --no-master: skipping master bypass (run 'add-master' afterward to re-enable).")
        else:
            print(f"No master key file found. Encrypting without lockout recovery.")
            print(f"  Run 'create-master' first, then re-encrypt to enable lockout recovery.")

        encrypt_file_section(filepath, heading, passphrase, master_passphrase)

    elif command == "decrypt":
        passphrase = getpass.getpass("Passphrase: ")
        try:
            decrypt_file_section(filepath, heading, passphrase)
        except PermissionError as e:
            print(str(e))
            sys.exit(1)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    elif command == "view":
        passphrase = getpass.getpass("Passphrase: ")
        try:
            view_file_section(filepath, heading, passphrase)
        except PermissionError as e:
            print(str(e))
            sys.exit(1)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    elif command in ("master-decrypt", "master-view"):
        if not os.path.exists(key_file):
            print(f"Master key file not found: {key_file}")
            print("Run: python pq_crypt.py create-master")
            sys.exit(1)
        passphrase = getpass.getpass("Master password: ")
        if not verify_master_password(passphrase, key_file):
            print("Wrong master password.")
            sys.exit(1)
        print("Master password verified.")
        try:
            if command == "master-decrypt":
                decrypt_file_section(filepath, heading, passphrase, use_master=True)
            else:
                view_file_section(filepath, heading, passphrase, use_master=True)
        except (PermissionError, ValueError) as e:
            print(str(e))
            sys.exit(1)

    elif command == "reset-lock":
        if not os.path.exists(key_file):
            print(f"Master key file not found: {key_file}")
            sys.exit(1)
        passphrase = getpass.getpass("Master password: ")
        try:
            reset_lock_file(filepath, passphrase, key_file)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    elif command == "add-master":
        if not os.path.exists(key_file):
            print(f"Master key file not found: {key_file}")
            print("Run: python pq_crypt.py create-master")
            sys.exit(1)
        passphrase = getpass.getpass("File passphrase: ")
        m_pass     = getpass.getpass("Master password: ")
        if not verify_master_password(m_pass, key_file):
            print("Wrong master password.")
            sys.exit(1)
        try:
            add_master_to_section(filepath, passphrase, m_pass)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    else:
        print(f"Unknown command: {command!r}")
        print("Commands: create-master, encrypt, decrypt, view, master-decrypt, master-view,")
        print("          reset-lock, add-master, encrypt-file, decrypt-file, encrypt-all, decrypt-all")
        sys.exit(1)


if __name__ == "__main__":
    main()
