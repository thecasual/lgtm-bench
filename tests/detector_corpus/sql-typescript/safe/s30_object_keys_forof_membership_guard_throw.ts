// updateUserProfile validates every caller-controlled field KEY against a fixed
// allowlist in a for-of loop, throwing on any unknown column before building the
// SET clause; the whole key array is therefore constrained to vetted identifiers.
import { Pool } from "pg";

const UPDATABLE_COLUMNS = new Set(["email", "display_name", "avatar_url", "bio"]);

export async function updateUserProfile(
  pool: Pool,
  userId: string,
  fields: Record<string, string>,
): Promise<void> {
  const keys = Object.keys(fields);
  if (keys.length === 0) return;
  for (const key of keys) {
    if (!UPDATABLE_COLUMNS.has(key)) {
      throw new Error(`Column "${key}" is not updatable`);
    }
  }
  const setClause = keys.map((key, i) => `"${key}" = $${i + 1}`).join(", ");
  const values = keys.map((key) => fields[key]);
  const sql = `UPDATE users SET ${setClause} WHERE id = $${keys.length + 1}`;
  await pool.query(sql, [...values, userId]);
}
