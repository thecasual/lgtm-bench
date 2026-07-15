// listProducts maps the caller-chosen sort key through a fixed lookup
// table; only one of the table's own literal values reaches the query.
const ALLOWED_SORT: Record<string, string> = { name: "name", price: "price" };

export function listProducts(pool: any, sortBy: string) {
  const column = ALLOWED_SORT[sortBy] || "id";
  return pool.query(`SELECT id, name, price FROM products ORDER BY ${column}`);
}
