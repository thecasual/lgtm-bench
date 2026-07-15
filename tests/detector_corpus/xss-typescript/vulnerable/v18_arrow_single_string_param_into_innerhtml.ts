// renderMarkup is a single-parameter arrow function whose string argument is
// assigned straight into the document body's innerHTML, unescaped.
export const renderMarkup = (html: string) => {
  document.body.innerHTML = html;
};
