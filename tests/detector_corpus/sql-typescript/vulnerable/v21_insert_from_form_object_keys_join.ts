// createSignup builds the INSERT column list from the caller-controlled form
// KEYS (Object.keys), interpolating them as SQL identifiers with no allowlist.
export function createSignup(form: Record<string, string>, pool: any) {
  const columns = Object.keys(form);
  const values = Object.values(form);
  const query = `INSERT INTO signups (${columns.join(", ")}) VALUES (${values
    .map((_, i) => `$${i + 1}`)
    .join(", ")})`;
  return pool.query(query, values);
}
