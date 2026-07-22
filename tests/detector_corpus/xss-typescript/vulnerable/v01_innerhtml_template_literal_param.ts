// renderGreeting drops the caller-supplied name straight into innerHTML via
// a template literal, so a name containing markup executes in the page.
export function renderGreeting(container: HTMLElement, name: string) {
  container.innerHTML = `<h1>Welcome, ${name}!</h1>`;
}
