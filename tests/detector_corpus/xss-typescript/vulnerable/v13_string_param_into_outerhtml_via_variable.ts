// swapWidgetMarkup routes a caller-supplied markup string through a local
// variable before assigning it into outerHTML, still unescaped.
export function swapWidgetMarkup(el: HTMLElement, markup: string) {
  const nextMarkup = markup;
  el.outerHTML = nextMarkup;
}
