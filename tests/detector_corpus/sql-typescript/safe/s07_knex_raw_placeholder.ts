// findByEmail passes a constant query string to knex.raw() and binds the
// email through the separate values array.
export function findByEmail(knex: any, email: string) {
  return knex.raw("SELECT * FROM users WHERE email = ?", [email]);
}
