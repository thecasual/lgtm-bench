// filterUsers builds a WHERE clause from an Express query object by
// concatenating the raw values into the SQL text.
export function filterUsers(req: any, pool: any) {
  const { role } = req.query;
  const where = "role = '" + role + "'";
  return pool.query("SELECT * FROM users WHERE " + where);
}
