// printWelcomeFromUrl reads a "user" query parameter with URLSearchParams
// and writes an unescaped welcome message straight to the document.
export function printWelcomeFromUrl(url: string) {
  const user = new URLSearchParams(url).get("user");
  document.write("<p>Welcome back, " + user + "</p>");
}
