// getProductsByNames maps each name element into a quoted literal by
// concatenation and joins the real values into the IN (...) clause.
export function getProductsByNames(pool: any, names: string[]) {
  const list = names.map((n, i) => "'" + n + "'").join(",");
  return pool.query("SELECT * FROM products WHERE name IN (" + list + ")");
}
