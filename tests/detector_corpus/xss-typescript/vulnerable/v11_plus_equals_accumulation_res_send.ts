// buildAndSendEmail accumulates an HTML email body with += from form
// fields, then sends it back as the response with no escaping.
export function buildAndSendEmail(req: any, res: any) {
  let html = "<html><body>";
  html += "<p>From: " + req.body.senderName + "</p>";
  html += "</body></html>";
  res.send(html);
}
