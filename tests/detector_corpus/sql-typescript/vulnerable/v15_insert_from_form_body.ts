// createSignup inserts a new row using values pulled straight from the
// request body and concatenated into the INSERT text.
export function createSignup(req: any, pool: any) {
  const { email, name } = req.body;
  return pool.query(
    "INSERT INTO signups (email, name) VALUES ('" + email + "', '" + name + "')"
  );
}
