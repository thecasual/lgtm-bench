// updateProfileField remaps the caller-chosen field to one of a fixed set
// of constant column names before building the UPDATE, and binds the new
// value through a placeholder.
export function updateProfileField(conn: any, field: string, value: string) {
  let column: string;
  switch (field) {
    case "displayName":
      column = "display_name";
      break;
    case "bio":
      column = "bio";
      break;
    default:
      throw new Error("unknown profile field");
  }
  return conn.execute(`UPDATE profiles SET ${column} = ? WHERE id = ?`, [
    value,
    1,
  ]);
}
