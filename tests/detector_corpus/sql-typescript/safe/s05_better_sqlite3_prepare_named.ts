// getUserRow uses better-sqlite3's named-parameter binding.
export function getUserRow(db: any, id: string) {
  const stmt = db.prepare("SELECT * FROM users WHERE id = @id");
  return stmt.get({ id });
}
