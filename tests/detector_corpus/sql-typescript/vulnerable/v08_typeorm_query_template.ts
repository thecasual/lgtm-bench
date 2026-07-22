// getUserById uses typeorm's raw query() escape hatch with interpolated id.
export function getUserById(repo: any, id: string) {
  return repo.query(`SELECT * FROM users WHERE id = ${id}`);
}
