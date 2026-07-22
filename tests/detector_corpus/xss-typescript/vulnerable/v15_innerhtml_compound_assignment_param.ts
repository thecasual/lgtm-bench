// appendGreeting grows the container's markup with a compound `innerHTML +=`
// assignment built from the caller-supplied name, so a name containing markup
// is parsed and executed in the page.
export function appendGreeting(container: HTMLElement, name: string) {
  container.innerHTML += "<p>Hello, " + name + "</p>";
}
