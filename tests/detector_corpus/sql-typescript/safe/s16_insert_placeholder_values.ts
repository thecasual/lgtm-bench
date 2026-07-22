// createSignup inserts a new row using bound placeholders for every value
// pulled from the request body.
export function createSignup(req: any, pool: any) {
  const { email, name } = req.body;
  return pool.query(
    "INSERT INTO signups (email, name) VALUES ($1, $2)",
    [email, name]
  );
}
