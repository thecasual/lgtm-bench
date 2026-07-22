// listProducts orders by a caller-chosen column with no allowlist check.
export function listProducts(pool: any, sortBy: string) {
  return pool.query(`SELECT id, name, price FROM products ORDER BY ${sortBy}`);
}
