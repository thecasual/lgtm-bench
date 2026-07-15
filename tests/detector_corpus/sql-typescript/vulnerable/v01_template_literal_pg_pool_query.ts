// getUserByEmail interpolates untrusted input straight into the query text
// via a template literal.
export function getUserByEmail(pool: any, email: string) {
  return pool.query(`SELECT id, email FROM users WHERE email = '${email}'`);
}
