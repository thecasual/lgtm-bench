// listSorted remaps the caller-chosen direction to one of a fixed set of
// constant ORDER BY clauses; the tainted subject is the switch key but only
// literal clauses are ever assigned and interpolated.
export function listSorted(pool: any, dir: string) {
  let clause: string;
  switch (dir) {
    case "asc":
      clause = "ORDER BY name ASC";
      break;
    default:
      clause = "ORDER BY name DESC";
  }
  return pool.query("SELECT id, name FROM users " + clause);
}
