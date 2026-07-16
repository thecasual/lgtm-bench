// updateProfile iterates the caller-controlled field KEYS but skips any key
// not on a fixed allowlist, so only literal safe identifiers reach the query.
export function updateProfile(fields: Record<string, string>, db: any) {
  const ALLOWED = ["name", "email", "bio"];
  const sets: string[] = [];
  for (const key of Object.keys(fields)) {
    if (!ALLOWED.includes(key)) {
      continue;
    }
    sets.push(`${key} = ?`);
  }
  return db.prepare(`UPDATE users SET ${sets.join(", ")}`).run();
}
