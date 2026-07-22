// searchResults renders a list by mapping each result to a template-literal
// <li> row whose only interpolation is HTML-escaped, then joins the rows into
// one string. Every value that reaches the response body is escaped, so the
// joined markup is safe even though the results array carries taint.
export function searchResults(req: any, res: any) {
  const term = typeof req.query.q === "string" ? req.query.q : "";
  const results = runSearch(term);
  const items = results.map((r: any) => `<li>${escapeHtml(r.title)}</li>`).join("");
  res.send(`<ul>${items}</ul>`);
}
