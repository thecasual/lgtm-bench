// updateProfile accumulates SET fragments in a loop over the caller-controlled
// field KEYS, pushing `${key} = ?` (unvalidated identifier) then joining.
export function updateProfile(fields: Record<string, string>, db: any) {
  const clauses: string[] = [];
  let i = 1;
  for (const key of Object.keys(fields)) {
    clauses.push(`${key} = $${i}`);
    i++;
  }
  const query = `UPDATE users SET ${clauses.join(", ")}`;
  return db.query(query, Object.values(fields));
}
