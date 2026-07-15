// welcomeCard escapes the caller-supplied name inside the template literal
// before it reaches innerHTML, so any markup in the name is neutralized.
export function welcomeCard(container: HTMLElement, name: string) {
  container.innerHTML = `<p>Hello, ${escapeHtml(name)}</p>`;
}
