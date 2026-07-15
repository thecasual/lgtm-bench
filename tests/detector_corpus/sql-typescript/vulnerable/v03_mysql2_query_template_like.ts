// searchProducts builds a LIKE pattern via template-literal interpolation
// and hands the whole string to mysql2's query() as the SQL text.
export function searchProducts(conn: any, term: string) {
  return conn.query(`SELECT id, name FROM products WHERE name LIKE '%${term}%'`);
}
