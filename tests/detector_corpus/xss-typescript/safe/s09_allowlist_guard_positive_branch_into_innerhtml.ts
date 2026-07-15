// applyTheme only assigns a theme name into innerHTML after checking it
// against a fixed allowlist (positive-branch guard form).
export function applyTheme(box: HTMLElement, req: any) {
  const ALLOWED = ["light", "dark", "system"];
  const theme = req.query.theme;
  if (ALLOWED.includes(theme)) {
    box.innerHTML = "<span>" + theme + "</span>";
  }
}
