// renderComment sanitizes the comment body with DOMPurify before it ever
// reaches innerHTML, stripping any active markup.
export function renderComment(container: HTMLElement, body: string) {
  container.innerHTML = DOMPurify.sanitize(body);
}
