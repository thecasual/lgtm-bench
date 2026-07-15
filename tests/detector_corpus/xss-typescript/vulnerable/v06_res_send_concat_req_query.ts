// greetRoute answers with an HTML greeting built by concatenating the
// caller's name straight off the query string into the response body.
export function greetRoute(req: any, res: any) {
  res.send("<p>Hello, " + req.query.name + "</p>");
}
