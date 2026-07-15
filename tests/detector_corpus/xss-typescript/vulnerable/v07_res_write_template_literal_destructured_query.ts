// searchResultsRoute echoes the search term back in the results page using
// a template literal, with the term destructured straight off req.query.
export function searchResultsRoute(req: any, res: any) {
  const { term } = req.query;
  res.write(`<p>Results for: ${term}</p>`);
  res.end();
}
