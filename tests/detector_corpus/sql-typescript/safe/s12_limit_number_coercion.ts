// listProductsPage coerces the caller-supplied page size through Number()
// before interpolating it, stripping any SQL syntax it could carry.
export function listProductsPage(pool: any, limit: string) {
  return pool.query(`SELECT id, name FROM products LIMIT ${Number(limit)}`);
}
