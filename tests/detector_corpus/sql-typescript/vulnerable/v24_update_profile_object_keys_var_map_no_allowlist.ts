// updateUserProfile builds the SET clause by mapping the caller-controlled field
// KEYS into `${field} = $n` fragments with NO allowlist and NO quoting; the
// column identifiers are attacker-controlled (SQL identifier injection). Mirrors
// the variable-indirected Object.keys().map() shape (keys assigned, then mapped).
import { Pool } from "pg";

export async function updateUserProfile(
  pool: Pool,
  userId: string,
  fields: Record<string, string>,
): Promise<void> {
  const fieldNames = Object.keys(fields);
  if (fieldNames.length === 0) return;
  const setClause = fieldNames.map((field, i) => `${field} = $${i + 1}`).join(", ");
  const values = [...Object.values(fields), userId];
  const query = `UPDATE users SET ${setClause} WHERE id = $${fieldNames.length + 1}`;
  await pool.query(query, values);
}
