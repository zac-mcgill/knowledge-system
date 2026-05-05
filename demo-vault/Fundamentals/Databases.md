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

A database is an organised collection of structured data managed by a database management system (DBMS) that supports efficient storage, retrieval, and manipulation.

## Why It Matters

Databases are the persistence layer for virtually all applications. Choosing the right database model and understanding query optimisation are essential skills.

## Key Principles

- **ACID** (Atomicity, Consistency, Isolation, Durability) guarantees that transactions are processed reliably even in the presence of errors or concurrent access.
- **Normalisation** organises tables to reduce redundancy by ensuring each piece of information is stored in exactly one place.
- **Indexing** creates auxiliary data structures that accelerate lookups at the cost of additional write overhead and storage.
- **Query optimisation** uses the query planner to choose efficient execution plans, leveraging statistics, indexes, and join strategies.
- **Transactions** group multiple operations into an atomic unit so partial failures cannot leave data in an inconsistent state.

## How It Works

1. Define a schema describing tables, columns, and relationships.
2. Insert data through validated transactions.
3. Query data using SQL or a query API.

## Examples

- PostgreSQL for relational data with ACID guarantees.
- MongoDB for document-oriented flexible schemas.
- Redis for in-memory key-value caching.

## Common Pitfalls

- N+1 query problem in ORM usage.
- Over-normalisation leading to excessive joins.
- Missing indexes on frequently queried columns.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Normalisation | Reduces redundancy | More complex joins |
| Denormalisation | Faster reads | Data duplication risk |
| Indexing | Accelerates queries | Slower writes and more storage |

## Related Concepts

- [[Data Structures]]
- [[Concurrency]]

## Further Exploration

- Database Internals (Petrov)
- Designing Data-Intensive Applications (Kleppmann)
