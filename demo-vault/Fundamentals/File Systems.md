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

A file system is the method an operating system uses to organise, store, and retrieve files on a storage device.

## Why It Matters

File systems determine how data is persisted, how quickly it can be accessed, and how reliably it survives failures. They are the interface between applications and physical storage.

## Key Principles

- Hierarchy — files organised in a directory tree
- Persistence — data survives process termination and reboots
- Access control — permissions govern who can read, write, or execute

## How It Works

1. The file system formats the storage device with metadata structures (superblock, inode table).
2. When a file is created, an inode is allocated and directory entries are updated.
3. Read and write operations translate logical offsets to physical block addresses.

## Examples

- ext4: the default Linux file system with journaling.
- NTFS: the Windows file system with access control lists.
- ZFS: a combined file system and volume manager with checksumming.

## Common Pitfalls

- Not accounting for file system limits (max path length, inode count).
- Assuming atomic writes without using journaling or write-ahead logs.
- Ignoring permissions leading to security holes.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Journaling | Crash recovery | Write amplification |
| Copy-on-write | Snapshots and checksums | Fragmentation over time |
| In-memory FS | Extreme speed | Volatile, data lost on reboot |

## Related Concepts

- [[Operating Systems]]
- [[Databases]]

## Further Exploration

- Operating Systems: Three Easy Pieces — File System chapters
