// legacyBanner runs the message through an HTML-escape helper before
// writing it to the document.
export function legacyBanner(req: any) {
  document.write("<marquee>" + escapeHtml(req.query.message) + "</marquee>");
}
