---
type: core-concept
domain: fundamentals
status: complete
has_key_principles: true
has_how_it_works: true
has_tradeoffs: true
difficulty: intermediate
---

## Definition

Cryptography is the science of securing information by transforming it into an unreadable format that can only be reversed by authorised parties.

## Why It Matters

Cryptography underpins secure communication, authentication, digital signatures, and data protection across all modern systems.

## Key Principles

- Kerckhoffs's principle — security depends on the key, not the secrecy of the algorithm
- Symmetric encryption — same key for encryption and decryption
- Asymmetric encryption — public key encrypts, private key decrypts

## How It Works

1. Select an appropriate algorithm for the use case (symmetric, asymmetric, hashing).
2. Generate cryptographic keys with sufficient entropy.
3. Apply the algorithm to transform plaintext into ciphertext or produce a digest.

## Examples

- AES-256 for symmetric encryption of data at rest.
- RSA and ECDSA for asymmetric key exchange and digital signatures.
- SHA-256 for cryptographic hashing.

## Common Pitfalls

- Rolling your own cryptographic algorithms.
- Using deprecated algorithms (MD5, SHA-1, DES).
- Poor key management and storage.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Symmetric encryption | Fast and efficient | Key distribution problem |
| Asymmetric encryption | Solves key exchange | Much slower than symmetric |
| Hashing | Integrity verification | One-way, cannot recover data |

## Related Concepts

- [[Security Fundamentals]]
- [[Networking Fundamentals]]

## Further Exploration

- Serious Cryptography (Aumasson)
- Cryptography Engineering (Ferguson, Schneier & Kohno)
