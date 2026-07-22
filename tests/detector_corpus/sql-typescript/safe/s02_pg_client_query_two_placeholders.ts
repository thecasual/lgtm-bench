// getActiveUserById binds both values via $1/$2 placeholders.
export function getActiveUserById(client: any, id: string) {
  return client.query(
    "SELECT id, name FROM users WHERE id = $1 AND active = $2",
    [id, true]
  );
}
