// getProductsByIds maps each id element into a quoted literal and joins the
// real values straight into the IN (...) clause - a value join, not a
// placeholder list, so the caller-supplied ids reach the query text.
export function getProductsByIds(pool: any, ids: string[]) {
  const list = ids.map((id, i) => `'${id}'`).join(",");
  return pool.query(`SELECT * FROM products WHERE id IN (${list})`);
}
