// createSignup builds the INSERT column list from the caller-controlled form
// KEYS, but each identifier is emitted as a double-quoted identifier whose
// internal quotes are doubled (.replace(/"/g, '""')), so no key can break out
// of its quoting; the values go through positional placeholders.
import { Pool } from "pg";

export async function createSignup(
  pool: Pool,
  form: Record<string, string>,
): Promise<number> {
  const columns = Object.keys(form);
  const values = columns.map((col) => form[col]);
  const placeholders = columns.map((_, i) => `$${i + 1}`);
  const columnList = columns.map((col) => `"${col.replace(/"/g, '""')}"`).join(", ");
  const query = `INSERT INTO signups (${columnList}) VALUES (${placeholders.join(", ")}) RETURNING id`;
  const result = await pool.query(query, values);
  return result.rows[0].id;
}
