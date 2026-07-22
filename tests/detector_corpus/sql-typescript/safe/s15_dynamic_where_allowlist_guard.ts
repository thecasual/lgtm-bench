// filterUsersByField only lets the field name through the guard when it is
// on the fixed allowlist; the guard throws before any other value can
// reach the query text.
const ALLOWED_FIELDS = ["role", "status"];

export function filterUsersByField(pool: any, field: string, value: string) {
  if (!ALLOWED_FIELDS.includes(field)) {
    throw new Error("unknown filter field");
  }
  return pool.query(`SELECT * FROM users WHERE ${field} = $1`, [value]);
}
