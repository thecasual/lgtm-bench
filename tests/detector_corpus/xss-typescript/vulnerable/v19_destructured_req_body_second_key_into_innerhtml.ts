// renderNote destructures the note text as the second key off req.body and
// drops it straight into innerHTML with no escaping.
export function renderNote(el: HTMLElement, req: any) {
  const { id, note } = req.body;
  el.innerHTML = "<p>" + note + "</p>";
}
