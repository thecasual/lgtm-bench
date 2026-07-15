// renderComment sanitizes the body with DOMPurify and then concatenates the
// cleaned result between constant wrapper tags; the tainted value is cleared
// before it reaches innerHTML.
export function renderComment(container: HTMLElement, body: string) {
  container.innerHTML = "<div class='comment'>" + DOMPurify.sanitize(body) + "</div>";
}
