// findByRole uses knex's query-builder .where(column, value) binder, which
// parameterizes the value instead of interpolating it into raw SQL text.
export function findByRole(knex: any, role: string) {
  return knex("users").where("role", role).select("*");
}
