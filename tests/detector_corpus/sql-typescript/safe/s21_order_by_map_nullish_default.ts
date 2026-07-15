// listProducts maps the caller-chosen sort key through a fixed lookup table
// and falls back to a constant default via `??`; only one of the table's
// own literal column names can reach the query text.
const SORT_COLUMNS: Record<string, string> = { name: "name", price: "price" };

export function listProducts(pool: any, sortBy: string) {
  const column = SORT_COLUMNS[sortBy] ?? "id";
  return pool.query(`SELECT id, name, price FROM products ORDER BY ${column}`);
}
