// legacyBanner writes a banner straight to the document using a message
// taken directly off the query string.
export function legacyBanner(req: any) {
  document.write("<marquee>" + req.query.message + "</marquee>");
}
