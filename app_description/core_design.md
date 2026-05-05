# 1. Core Design

The system is an **event-sourced, append-only ledger**.

All state is derived by deterministic replay of events. There is no mutable financial state.

```text
state = replay(sorted(events))
```
