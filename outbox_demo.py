"""Minimal transactional outbox demo (standard library only).

Order Service -> Database -> Message relay -> Message broker -> Payment Service
Run:  python outbox_demo.py
"""
import sqlite3


def make_db(schema):
    db = sqlite3.connect(":memory:", isolation_level=None)  # we issue BEGIN/COMMIT ourselves
    db.executescript(schema)
    return db


ORDER_DB = """
CREATE TABLE orders (id TEXT PRIMARY KEY, status TEXT);
CREATE TABLE outbox (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE,
                     type TEXT, payload TEXT, published INTEGER DEFAULT 0);
"""
PAYMENT_DB = """
CREATE TABLE payments (order_id TEXT);
CREATE TABLE processed_messages (message_id TEXT PRIMARY KEY);
"""


class Broker:
    def __init__(self):
        self.messages = []

    def publish(self, message_id, order_id):
        self.messages.append((message_id, order_id))


def place_order(db, order_id):
    """Order Service: (1) write -- business data AND message in ONE local transaction."""
    db.execute("BEGIN")
    db.execute("INSERT INTO orders VALUES (?, 'PENDING')", (order_id,))
    db.execute("INSERT INTO outbox (id, type, payload) VALUES (?, 'OrderCreated', ?)",
               ("m-" + order_id, order_id))
    db.execute("COMMIT")


def relay_once(db, broker):
    """Message relay (polling): (2) publish -- forward unpublished outbox rows to the broker."""
    rows = db.execute("SELECT id, payload FROM outbox WHERE published = 0 ORDER BY seq").fetchall()
    for message_id, order_id in rows:
        broker.publish(message_id, order_id)
        db.execute("UPDATE outbox SET published = 1 WHERE id = ?", (message_id,))


def pay(payment_db, message_id, order_id):
    """Payment Service: idempotent consumer -- remembers processed message IDs."""
    payment_db.execute("BEGIN")
    try:
        payment_db.execute("INSERT INTO processed_messages VALUES (?)", (message_id,))
    except sqlite3.IntegrityError:          # already processed: ignore the duplicate
        payment_db.execute("ROLLBACK")
        return
    payment_db.execute("INSERT INTO payments VALUES (?)", (order_id,))
    payment_db.execute("COMMIT")


def main():
    order_db, payment_db, broker = make_db(ORDER_DB), make_db(PAYMENT_DB), Broker()

    place_order(order_db, "order-1")
    print("1. Order Service: one transaction wrote the order and the outbox row")
    print("   orders:", order_db.execute("SELECT id, status FROM orders").fetchall())
    print("   outbox:", order_db.execute("SELECT id, type, published FROM outbox").fetchall())

    relay_once(order_db, broker)
    print("2. Message relay: published the outbox row to the broker")
    print("   broker:", broker.messages)

    for message_id, order_id in broker.messages:
        pay(payment_db, message_id, order_id)
    print("3. Payment Service: charged the order")
    print("   payments:", payment_db.execute("SELECT order_id FROM payments").fetchall())


if __name__ == "__main__":
    main()
