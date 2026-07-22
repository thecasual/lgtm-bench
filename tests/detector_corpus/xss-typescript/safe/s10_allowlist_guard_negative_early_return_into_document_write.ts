// printLocale bails out early when the requested locale isn't on the
// allowlist, so only an allowlisted locale ever reaches document.write.
export function printLocale(req: any) {
  const ALLOWED = ["en", "fr", "de", "es"];
  const locale = req.query.locale;
  if (!ALLOWED.includes(locale)) {
    return;
  }
  document.write("<p>Locale: " + locale + "</p>");
}
