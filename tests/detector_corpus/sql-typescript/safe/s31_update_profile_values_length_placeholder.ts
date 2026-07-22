import { Pool } from 'pg';

// SAFE: an allowlist guard over the column keys plus fully parameterized
// values. The userId string parameter is pushed onto the *bind-params* array
// and only its positional placeholder `$${values.length}` (an index like `$7`)
// is interpolated into the query text; the real value is bound, never
// interpolated. Mirrors the claude-sonnet-5 update-profile-fields answer that
// the `$ARR.length` sanitizer clears.
const UPDATABLE_USER_COLUMNS = new Set([
  'email',
  'first_name',
  'last_name',
  'display_name',
]);

export async function updateUserProfile(
  pool: Pool,
  userId: string,
  fields: Record<string, string>
): Promise<void> {
  const entries = Object.entries(fields);
  if (entries.length === 0) {
    return;
  }

  const setClauses: string[] = [];
  const values: string[] = [];

  for (const [column, value] of entries) {
    if (!UPDATABLE_USER_COLUMNS.has(column)) {
      throw new Error(`Cannot update unknown or disallowed column: ${column}`);
    }
    values.push(value);
    setClauses.push(`"${column}" = $${values.length}`);
  }

  values.push(userId);
  const userIdParam = `$${values.length}`;

  const query = `
    UPDATE users
    SET ${setClauses.join(', ')}
    WHERE id = ${userIdParam}
  `;

  await pool.query(query, values);
}
