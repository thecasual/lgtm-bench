// listProductsSorted concatenates the sort column with no validation.
export function listProductsSorted(conn: any, sortBy: string) {
  return conn.query("SELECT id, name, price FROM products ORDER BY " + sortBy);
}
