// listProducts only lets the sort column through when it is a member of a
// fixed Set-based allowlist (Set.has, not Array.includes); the guard throws
// before any other value can reach the query text.
const SORTABLE_COLUMNS = new Set(["id", "name", "price", "created_at"]);

export async function listProducts(pool: any, sortBy: string) {
  if (!SORTABLE_COLUMNS.has(sortBy)) {
    throw new Error("invalid sort column");
  }
  return pool.query(`SELECT * FROM products ORDER BY "${sortBy}"`);
}
