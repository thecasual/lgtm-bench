// statusRoute constrains the caller-supplied status to a fixed allowlist
// with a ternary before it reaches the response body.
export function statusRoute(req: any, res: any) {
  const ALLOWED = ["ok", "pending", "error"];
  const status = req.query.status;
  const safeStatus = ALLOWED.includes(status) ? status : "unknown";
  res.send("<span>" + safeStatus + "</span>");
}
