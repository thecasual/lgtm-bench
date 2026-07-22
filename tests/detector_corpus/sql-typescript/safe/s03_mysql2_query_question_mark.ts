// getUserById uses mysql2's ? placeholder with the id bound separately.
export function getUserById(conn: any, id: string) {
  return conn.query("SELECT id, name FROM users WHERE id = ?", [id]);
}
