# 9. Expense Semantics

## 9.1 Creation

Full snapshot event.

## 9.2 Edit

* emits EXPENSE_EDITED
* replaces full expense state (no patching)

## 9.3 Delete

* emits EXPENSE_DELETED
* globally overrides expense

## 9.4 Resolution (STRICT ORDERED RULE)

For each `expense_id`:

1. Sort events by `(timestamp_ns, event_id)`
2. If any `EXPENSE_DELETED` exists → expense = NULL
3. Else → last event wins

```text
group_by(expense_id) → sort → apply rules → derive state
```
