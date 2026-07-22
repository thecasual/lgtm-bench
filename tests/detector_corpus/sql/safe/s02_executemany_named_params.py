def record_events(conn, events):
    conn.executemany(
        "INSERT INTO events (name, ts) VALUES (:name, :ts)", events
    )
    conn.commit()
