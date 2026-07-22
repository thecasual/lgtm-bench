// profileApiRoute returns the caller-supplied name as JSON, not HTML, so
// there is no markup-parsing sink at all (spec: res.json must not flag).
export function profileApiRoute(req: any, res: any) {
  res.json({ name: req.query.name });
}
