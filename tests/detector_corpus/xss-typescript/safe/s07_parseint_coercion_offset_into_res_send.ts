// pageRoute coerces the caller-supplied page offset to an integer before
// echoing it back in the response body.
export function pageRoute(req: any, res: any) {
  const page = parseInt(req.query.page, 10);
  res.send("<p>Page " + page + "</p>");
}
