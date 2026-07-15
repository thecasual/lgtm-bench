// greetRoute ends the HTTP response with an HTML body built by concatenating
// the caller's name straight off the query string; Express serves a string
// body as text/html, so this is reflected cross-site scripting.
export function greetRoute(req: any, res: any) {
  res.end("<p>Hello, " + req.query.name + "</p>");
}
