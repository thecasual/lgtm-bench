// listUsersSorted only interpolates the sort column inside the positive
// branch of a Set-based allowlist guard (Set.has), so sortBy is constrained
// to one of a fixed literal set before it reaches the query text.
const SORTABLE_COLUMNS = new Set(["name", "email", "created_at"]);

export function listUsersSorted(conn: any, sortBy: string) {
  if (SORTABLE_COLUMNS.has(sortBy)) {
    return conn.query(`SELECT id, name, email FROM users ORDER BY ${sortBy}`);
  }
  return conn.query("SELECT id, name, email FROM users ORDER BY id");
}
