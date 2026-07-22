// greetRoute encodes the caller's name with the `he` library before
// building the response body.
export function greetRoute(req: any, res: any) {
  res.send("<p>Hello, " + he.encode(req.query.name) + "</p>");
}
