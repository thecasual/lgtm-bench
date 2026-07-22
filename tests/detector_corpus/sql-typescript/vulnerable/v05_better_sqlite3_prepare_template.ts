// getUserRow interpolates the id straight into the prepared statement text.
export function getUserRow(db: any, id: string) {
  const stmt = db.prepare(`SELECT * FROM users WHERE id = ${id}`);
  return stmt.get();
}
