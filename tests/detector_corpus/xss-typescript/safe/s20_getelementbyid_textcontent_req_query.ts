// updateStatus resolves the target element with getElementById and writes the
// caller-supplied status via textContent, which never parses markup.
export function updateStatus(req: any) {
  document.getElementById("status")!.textContent = req.query.status;
}
