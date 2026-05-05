# 14. Replay Cache

Cache valid iff:

* event append succeeded
* request_id confirmed in memory index

### Constraints

* process-local only
* invalidated on restart
* no persistence across sessions

Else:

* full replay fallback
