// searchRoute echoes the search term back into the response body through a
// template literal taken directly off the query string.
export function searchRoute(req: any, res: any) {
  res.send(`<p>Results for: ${req.query.q}</p>`);
}
