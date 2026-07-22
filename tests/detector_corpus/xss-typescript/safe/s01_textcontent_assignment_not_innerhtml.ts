// renderGreeting uses textContent, not innerHTML, so the browser treats the
// name as plain text and never parses it as markup (spec: textContent
// assignment must not flag).
export function renderGreeting(container: HTMLElement, name: string) {
  container.textContent = `Welcome, ${name}!`;
}
