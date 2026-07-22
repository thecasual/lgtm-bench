// getUserById concatenates the numeric-looking id string straight into the
// query text instead of binding it.
export function getUserById(client: any, id: string) {
  return client.query("SELECT id, name FROM users WHERE id = " + id);
}
