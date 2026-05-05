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

Networking fundamentals cover the principles, protocols, and architectures that enable communication between computing devices.

## Why It Matters

All modern software depends on network communication. Understanding networking is essential for building distributed systems, web applications, and secure infrastructure.

## Key Principles

- **Layered model** separates network concerns into distinct layers (e.g., OSI or TCP/IP), allowing each layer to evolve independently.
- **Addressing** uniquely identifies every endpoint using IP addresses at the network layer and port numbers at the transport layer.
- **TCP vs UDP trade-off** balances reliable ordered delivery (TCP) against low-latency best-effort delivery (UDP) depending on application needs.
- **Stateless vs stateful protocols** determines whether a server retains session context between requests, affecting scalability and failure recovery.
- **Encapsulation** wraps data with headers at each layer as it descends the stack, with each header stripped off at the corresponding layer on the receiving side.

## How It Works

1. An application generates data and passes it to the transport layer.
2. The transport layer segments data and adds port information (TCP/UDP).
3. The network layer adds source and destination IP addresses.
4. The data link layer frames the packet and adds MAC addresses.
5. The physical layer transmits bits over the medium.

## Examples

- HTTP request from browser to web server over TCP.
- DNS resolution converting domain names to IP addresses.
- ARP resolving IP addresses to MAC addresses on a LAN.

## Common Pitfalls

- Ignoring latency and packet loss in distributed system design.
- Hardcoding IP addresses instead of using DNS.
- Not accounting for NAT traversal in peer-to-peer applications.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| TCP | Reliable, ordered delivery | Higher latency and overhead |
| UDP | Low latency, simple | No delivery guarantee |
| Layered model | Modular, interchangeable components | Encapsulation overhead |

## Related Concepts

- [[Operating Systems]]
- [[Security Fundamentals]]

## Further Exploration

- Computer Networking: A Top-Down Approach (Kurose & Ross)
