// findUser uses typeorm's :named parameter binding on the QueryBuilder.
export function findUser(repo: any, id: string) {
  return repo.createQueryBuilder("u").where("u.id = :id", { id }).getOne();
}
