// listProductsSorted only lets the sort column through when it is a member
// of the fixed allowlist; anything else falls back to a constant default.
const ALLOWED_COLUMNS = ["name", "price", "created_at"];

export function listProductsSorted(conn: any, sortBy: string) {
  const column = ALLOWED_COLUMNS.includes(sortBy) ? sortBy : "id";
  return conn.query("SELECT id, name, price FROM products ORDER BY " + column);
}
