// clearSessionsForUser builds a raw exec() string by concatenation;
// better-sqlite3's exec() never binds parameters.
export function clearSessionsForUser(db: any, user: string) {
  return db.exec("DELETE FROM sessions WHERE user = '" + user + "'");
}
