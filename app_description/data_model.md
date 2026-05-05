# 3. Data Model

## 3.1 Events (source of truth)

```text
event_id | request_id | timestamp_ns | type | payload_json
```

### Event types

* EXPENSE_CREATED
* EXPENSE_EDITED
* EXPENSE_DELETED
* SETTLEMENT_CREATED
