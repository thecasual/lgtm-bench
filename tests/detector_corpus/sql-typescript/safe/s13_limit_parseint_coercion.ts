// listProductsPage coerces the caller-supplied limit through parseInt()
// before interpolating it.
export function listProductsPage(conn: any, limit: string) {
  const n = parseInt(limit, 10);
  return conn.query(`SELECT id, name FROM products LIMIT ${n}`);
}
