// deleteUser concatenates the caller-supplied id into an execute() call.
export function deleteUser(conn: any, userId: string) {
  return conn.execute("DELETE FROM users WHERE id = " + userId);
}
