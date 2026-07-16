// updateUserProfile narrows the caller-controlled field KEYS through an
// allowlist filter (ALLOWED.has) before building the SET clause, so only vetted
// column identifiers are ever interpolated; values go through placeholders.
import { Pool } from "pg";

const ALLOWED = new Set(["email", "display_name", "bio"]);

export async function updateUserProfile(
  pool: Pool,
  userId: string,
  fields: Record<string, string>,
): Promise<void> {
  const keys = Object.keys(fields).filter((k) => ALLOWED.has(k));
  if (keys.length === 0) return;
  const setClause = keys.map((k, i) => `${k} = $${i + 1}`).join(", ");
  const values = keys.map((k) => fields[k]);
  const sql = `UPDATE users SET ${setClause} WHERE id = $${keys.length + 1}`;
  await pool.query(sql, [...values, userId]);
}
