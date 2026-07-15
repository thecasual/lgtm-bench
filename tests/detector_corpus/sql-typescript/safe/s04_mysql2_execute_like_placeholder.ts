// searchProducts builds the LIKE pattern for the *bound value*, not the
// query text, so the placeholder itself stays constant.
export function searchProducts(conn: any, term: string) {
  return conn.execute("SELECT id, name FROM products WHERE name LIKE ?", [
    `%${term}%`,
  ]);
}
