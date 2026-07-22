// showName writes the caller's name via textContent (not innerHTML), so the
// browser renders it as plain text even though it is concatenated with a
// constant prefix (spec: textContent is a different property than the sink).
export function showName(el: HTMLElement, req: any) {
  el.textContent = "Hello, " + req.query.name;
}
