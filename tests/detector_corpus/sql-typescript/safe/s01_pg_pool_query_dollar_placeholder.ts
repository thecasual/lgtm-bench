// getUserByEmail binds the email through a $1 placeholder and a separate
// values array, never interpolating it into the query text.
export function getUserByEmail(pool: any, email: string) {
  return pool.query("SELECT id, email FROM users WHERE email = $1", [email]);
}
