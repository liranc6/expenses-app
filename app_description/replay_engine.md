# 12. Replay Engine

## Property

```text
replay(events) is pure
```

* no external state
* deterministic output
* identical input → identical state

## Rule

Final state depends only on **sorted event log**
