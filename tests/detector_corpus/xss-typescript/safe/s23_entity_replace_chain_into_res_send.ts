// searchRoute entity-encodes the search term with an inline replace-chain
// (&, <, > -> &amp;/&lt;/&gt;) before interpolating it into element text, so
// the `<` that would open an injected tag is neutralized.
export function searchRoute(req: any, res: any) {
  const q = String(req.query.q);
  const safe = q.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  res.send(`<p>Results for: ${safe}</p>`);
}
