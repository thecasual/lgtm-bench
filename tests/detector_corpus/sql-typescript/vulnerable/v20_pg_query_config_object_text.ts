// getUser passes a pg query-config object whose `text` field is built by
// interpolating the id, with no `values` array to bind it.
export function getUser(pool: any, id: string) {
  return pool.query({ text: `SELECT * FROM users WHERE id = ${id}` });
}
