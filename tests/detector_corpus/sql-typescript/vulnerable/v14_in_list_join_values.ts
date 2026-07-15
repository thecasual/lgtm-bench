// getProductsByIds expands an id list by joining the raw values straight
// into the IN (...) clause instead of using bound placeholders.
export function getProductsByIds(pool: any, ids: string[]) {
  const list = ids.join(",");
  return pool.query(`SELECT * FROM products WHERE id IN (${list})`);
}
