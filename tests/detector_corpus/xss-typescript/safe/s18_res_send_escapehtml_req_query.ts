// greetRoute escapes the caller's name with an HTML-escape helper before
// concatenating it into the response body.
export function greetRoute(req: any, res: any) {
  res.send("<p>Hello, " + escapeHtml(req.query.name) + "</p>");
}
