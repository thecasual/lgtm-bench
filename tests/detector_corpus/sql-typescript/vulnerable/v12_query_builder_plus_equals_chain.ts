// searchByName accumulates the query text with `+=` before sending it off,
// rather than binding the caller-supplied name.
export function searchByName(pool: any, name: string) {
  let q = "SELECT id, name FROM users WHERE name = '";
  q += name;
  q += "'";
  return pool.query(q);
}
