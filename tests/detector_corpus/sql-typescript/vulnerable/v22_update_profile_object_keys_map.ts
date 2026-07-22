// updateProfile builds the SET clause by mapping the caller-controlled field
// KEYS into `${field} = $n` fragments; the column identifiers are unvalidated.
export function updateProfile(id: string, fields: Record<string, string>, pool: any) {
  const sets = Object.keys(fields).map((field, i) => `${field} = $${i + 2}`);
  const query = `UPDATE users SET ${sets.join(", ")} WHERE id = $1`;
  return pool.query(query, [id, ...Object.values(fields)]);
}
