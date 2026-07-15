// findByEmail passes an interpolated string to knex's raw() escape hatch.
export function findByEmail(knex: any, email: string) {
  return knex.raw(`SELECT * FROM users WHERE email = '${email}'`);
}
