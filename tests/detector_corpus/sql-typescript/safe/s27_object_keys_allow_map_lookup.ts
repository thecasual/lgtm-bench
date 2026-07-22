// updateProfile maps each caller-chosen field KEY through a fixed lookup table
// before it reaches the query, so only the table's own literal column names do.
export function updateProfile(fields: Record<string, string>, db: any) {
  const COLUMN_MAP: Record<string, string> = { name: "name", email: "email" };
  const sets: string[] = [];
  for (const key of Object.keys(fields)) {
    const col = COLUMN_MAP[key];
    if (!col) {
      continue;
    }
    sets.push(`${col} = ?`);
  }
  return db.prepare(`UPDATE users SET ${sets.join(", ")}`).run();
}
