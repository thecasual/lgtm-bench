// listUsersSorted selects a full constant query per allowlisted sort key,
// so no untrusted text ever reaches the query string.
export function listUsersSorted(pool: any, sortKey: string) {
  let query: string;
  switch (sortKey) {
    case "name":
      query = "SELECT id, name FROM users ORDER BY name";
      break;
    case "email":
      query = "SELECT id, name FROM users ORDER BY email";
      break;
    default:
      query = "SELECT id, name FROM users ORDER BY id";
  }
  return pool.query(query);
}
