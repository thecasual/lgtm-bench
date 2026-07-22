def bulk_insert_events(conn, table, rows):
    conn.executemany(f"INSERT INTO {table} (name, ts) VALUES (?, ?)", rows)
    conn.commit()
