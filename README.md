# Minimal transactional outbox demo

Pure Python (standard library, SQLite in memory), one file: `outbox_demo.py`.
Follows the scenario of the first slide: *Order Service -> Database -> Message relay -> Message broker -> Payment Service*.

```
docker build -t outbox-demo .
docker run --rm outbox-demo
```

Steps: (1) the Order Service writes the order and the outbox row in one local transaction,
(2) the message relay publishes the outbox row to the broker, (3) the Payment Service
consumes the message (idempotent: processed message IDs are stored).

Deliberately simplified: broker is an in-memory list, the relay runs once instead of in a loop,
no ordering guarantees, no outbox cleanup, no failures.
