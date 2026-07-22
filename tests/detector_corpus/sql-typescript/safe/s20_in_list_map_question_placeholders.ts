// getProductsByIds builds a constant `?,?,...` placeholder list (mysql2 /
// better-sqlite3 style) by mapping every element to a literal `?`, then
// binds the actual id values separately - the values never reach the text.
export function getProductsByIds(conn: any, ids: string[]) {
  const placeholders = ids.map(() => "?").join(",");
  return conn.query(`SELECT * FROM products WHERE id IN (${placeholders})`, ids);
}
