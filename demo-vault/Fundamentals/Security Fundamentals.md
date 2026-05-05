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

Security fundamentals encompass the core principles and practices for protecting information systems from unauthorised access, disclosure, modification, and destruction.

## Why It Matters

Every system connected to a network is a potential target. Security must be designed in from the start, not bolted on as an afterthought.

## Key Principles

- **Confidentiality, Integrity, Availability (CIA triad)** forms the foundational framework for evaluating security properties of any system.
- **Least privilege** grants each component or user only the permissions required for its task, limiting damage from compromise or error.
- **Defence in depth** layers multiple independent controls so that defeating one does not expose the entire system.
- **Threat modelling** systematically identifies assets, potential attackers, and attack vectors before writing code, guiding early design decisions.
- **Secure defaults** configure systems in the most restrictive safe state out of the box, requiring explicit opt-in to open permissions.

## How It Works

1. Identify assets and threats through risk assessment.
2. Apply controls (encryption, access control, monitoring).
3. Continuously audit and respond to incidents.

## Examples

- TLS encrypting data in transit between client and server.
- Role-based access control restricting database queries.
- Intrusion detection systems monitoring network traffic.

## Common Pitfalls

- Storing passwords in plaintext.
- Trusting client-side validation alone.
- Security through obscurity instead of proper controls.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Strong encryption | Data confidentiality | Computational overhead |
| Strict access control | Reduced attack surface | User friction |
| Monitoring | Early threat detection | Privacy and storage costs |

## Related Concepts

- [[Networking Fundamentals]]
- [[Operating Systems]]
- [[Cryptography]]

## Further Exploration

- Security Engineering (Anderson)
