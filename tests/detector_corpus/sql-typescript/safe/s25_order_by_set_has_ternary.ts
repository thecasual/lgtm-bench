// listOrders picks the sort column via a ternary guarded by a Set-based
// allowlist (Set.has); anything not on the allowlist falls back to a
// constant default, so only an allowlisted literal ever reaches the query.
const ALLOWED_SORT_COLUMNS = new Set(["id", "total", "created_at"]);

export function listOrders(pool: any, sortBy: string) {
  const column = ALLOWED_SORT_COLUMNS.has(sortBy) ? sortBy : "id";
  return pool.query(`SELECT * FROM orders ORDER BY ${column}`);
}
