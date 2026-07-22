// updateProfileField updates a single caller-chosen column with a
// caller-chosen value, both concatenated straight into the SET clause.
export function updateProfileField(conn: any, field: string, value: string) {
  return conn.execute(
    "UPDATE profiles SET " + field + " = '" + value + "' WHERE id = 1"
  );
}
