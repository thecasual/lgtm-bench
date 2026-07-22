// showResultCount coerces the caller-supplied count to a number before
// building the markup, stripping any markup characters it could carry.
export function showResultCount(box: HTMLElement, req: any) {
  const count = Number(req.query.count);
  box.innerHTML = "<span>" + count + " results</span>";
}
