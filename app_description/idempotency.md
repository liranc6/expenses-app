# 6. Idempotency

## Rule

If `request_id` already exists → ignore event.

## Implementation

* In-memory index:
  * `request_id → event_id`
* Rebuilt on startup via full scan

## Constraint

* `request_id` is globally unique
* generated via `uuid4().hex`
* never reused
