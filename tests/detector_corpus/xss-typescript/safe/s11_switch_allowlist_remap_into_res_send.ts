// sizeRoute remaps a caller-supplied size name to itself only inside a
// switch allowlist; any other value falls through to a fixed default.
export function sizeRoute(req: any, res: any) {
  const size = req.query.size;
  let safeSize = "medium";
  switch (size) {
    case "small":
    case "medium":
    case "large":
      safeSize = size;
      break;
  }
  res.send("<span>" + safeSize + "</span>");
}
