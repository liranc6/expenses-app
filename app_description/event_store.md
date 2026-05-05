# 5. Event Store Behavior

## 5.1 Startup loading

* Single **batch read of full sheet**
* Parse into memory

No row-by-row reads allowed.

## 5.2 Ordering invariant (MANDATORY)

All processing must use:

```text
sort(events, key=(timestamp_ns, event_id))
```

Sheet row order is irrelevant.
