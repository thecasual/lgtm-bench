// getProductsByIds builds a placeholder list ($1, $2, ...) for the query
// text and passes the actual id values separately - the values themselves
// never reach the query text.
export function getProductsByIds(pool: any, ids: string[]) {
  const placeholders = ids.map((_, i) => `$${i + 1}`).join(",");
  return pool.query(`SELECT * FROM products WHERE id IN (${placeholders})`, ids);
}
