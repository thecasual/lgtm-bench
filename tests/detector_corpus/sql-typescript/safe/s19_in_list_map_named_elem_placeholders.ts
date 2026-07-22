// getProductsByIds builds a `$1,$2,...` positional placeholder list from
// the loop index and passes the id values separately. The map callback
// names its element `id` but never uses it - only the index reaches the
// generated token - so no value ever lands in the query text.
export function getProductsByIds(pool: any, ids: string[]) {
  const placeholders = ids.map((id, i) => `$${i + 1}`).join(",");
  return pool.query(`SELECT * FROM products WHERE id IN (${placeholders})`, ids);
}
