// buildGreeting assembles the greeting across several statements, routing the
// caller-supplied name through a local variable by plain concatenation before
// assigning the result into innerHTML unescaped.
export function buildGreeting(el: HTMLElement, name: string) {
  let h = "<p>";
  h = h + name;
  h = h + "</p>";
  el.innerHTML = h;
}
