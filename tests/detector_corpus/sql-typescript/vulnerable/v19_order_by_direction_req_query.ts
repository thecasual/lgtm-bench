// listSorted interpolates a caller-controlled sort direction pulled from the
// Express query object straight after ORDER BY, with no allowlist.
export function listSorted(req: any, pool: any) {
  const dir = req.query.dir;
  return pool.query(`SELECT id, name FROM users ORDER BY name ${dir}`);
}
