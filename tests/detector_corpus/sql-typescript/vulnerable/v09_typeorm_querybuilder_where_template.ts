// findUser builds a typeorm QueryBuilder WHERE fragment by interpolating
// the id directly instead of using a :named parameter.
export function findUser(repo: any, id: string) {
  return repo.createQueryBuilder("u").where(`u.id = ${id}`).getOne();
}
