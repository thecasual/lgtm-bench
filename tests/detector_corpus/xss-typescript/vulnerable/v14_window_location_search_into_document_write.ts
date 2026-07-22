// echoQueryToPage writes the raw query string portion of the URL straight
// into the document.
export function echoQueryToPage() {
  document.write("<p>" + window.location.search + "</p>");
}
