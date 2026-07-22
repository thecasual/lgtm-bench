// replaceCard rebuilds an element's outerHTML by string concatenation from
// a caller-supplied title, with no escaping of markup characters.
export function replaceCard(el: HTMLElement, title: string) {
  el.outerHTML = "<div class='card'>" + title + "</div>";
}
