import { Pool } from 'pg';

// VULNERABLE near-miss for the `$ARR.length` sanitizer: the function uses a
// legitimate positional placeholder `$${values.length}` for one column, but
// ALSO interpolates the raw string value of another column directly into the
// query text. The `.length` sanitizer must clear ONLY the numeric length read,
// leaving the co-interpolated tainted value flagged (SQL injection).
export async function updateUserProfile(
  pool: Pool,
  userId: string,
  displayName: string
): Promise<void> {
  const values: string[] = [];

  values.push(userId);
  const userIdParam = `$${values.length}`;

  // BUG: displayName is concatenated straight into the query text instead of
  // being bound like userId.
  const query = `
    UPDATE users
    SET display_name = '${displayName}'
    WHERE id = ${userIdParam}
  `;

  await pool.query(query, values);
}
