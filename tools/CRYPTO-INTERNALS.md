# pq_crypt.py — Architecture Internals

> This file is encrypted at rest. It contains the full security architecture
> of the encryption tool. Do not commit this file in plaintext.

---

## Security Layers

Hybrid scheme: ML-KEM-1024 (NIST FIPS 203) + AES-256-GCM + Argon2id

1. **Argon2id** (memory-hard KDF) — brute-force resistant passphrase hashing
2. **ML-KEM-1024** — NIST FIPS 203 lattice-based post-quantum key encapsulation
3. **AES-256-GCM** — quantum-resistant authenticated encryption (128-bit PQ security)
4. **Final key** = K3-256(mlkem_shared_secret) — key independent of password path,
   so both regular and master passwords decrypt the same ciphertext.

## Lockout System

- Wrong password attempts are tracked inside the encrypted block (plaintext counter).
- After MAX_ATTEMPTS (3) failures, the file is LOCKED.
- A locked file can only be opened with the master password.
- The master password is verified against the master key file (same directory as pq_crypt.py).
- Master path is only available if the master key file existed when the file was encrypted.

## Full Command Reference

### Section-level encryption (legacy)
```
encrypt <file.md> "<Section Heading>"    — Encrypt section in-place
decrypt <file.md> "<Section Heading>"    — Decrypt with regular passphrase
view <file.md> "<Section Heading>"       — Decrypt to stdout only
master-decrypt <file.md> "<Section>"     — Decrypt with master password (bypasses lockout)
master-view <file.md> "<Section>"        — View with master password
add-master <file.md> "<Section>"         — Add master bypass to existing encrypted section
reset-lock <file.md> "<Section>"         — Reset lockout counter using master password
```

### Whole-file encryption (current architecture)
```
encrypt-file <file.md>                   — Encrypt entire file as single blob
decrypt-file <file.md>                   — Decrypt whole-file encrypted file
master-decrypt-file <file.md>            — Decrypt with master password
encrypt-all [directory]                  — Batch encrypt all .md files (skips README.md)
decrypt-all [directory]                  — Batch decrypt all encrypted .md files
```

### Master key management
```
create-master                            — Create the master key file (run ONCE)
```

## Key Derivation Flow

```
passphrase → Argon2id(64MB, 3 iterations) → derived_key
derived_key → unwrap KEM secret key (sk)
sk → KEM.decaps(ciphertext) → shared_secret
shared_secret → SHA3-256 → final AES-256-GCM key
```

Both regular and master passwords follow the same flow but unwrap independent copies of the KEM sk.

## Dependencies

```
pip install cryptography kyber-py
```
