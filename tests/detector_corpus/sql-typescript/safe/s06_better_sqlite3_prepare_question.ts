// deleteSession uses better-sqlite3's ? placeholder binding.
export function deleteSession(db: any, sessionId: string) {
  const stmt = db.prepare("DELETE FROM sessions WHERE id = ?");
  return stmt.run(sessionId);
}
