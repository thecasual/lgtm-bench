// updateNotice destructures the notice text straight off req.body and
// assigns it into innerHTML unescaped.
export function updateNotice(noticeBox: HTMLElement, req: any) {
  const { text } = req.body;
  noticeBox.innerHTML = text;
}
