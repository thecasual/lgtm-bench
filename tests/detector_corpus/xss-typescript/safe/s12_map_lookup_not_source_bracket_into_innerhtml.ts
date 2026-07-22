// renderIcon looks the requested icon name up in a fixed map of literal
// SVG snippets; only the map's own values (never the tainted key) ever
// reach innerHTML.
const ICONS: Record<string, string> = {
  star: "<svg data-icon='star'></svg>",
  heart: "<svg data-icon='heart'></svg>",
};

export function renderIcon(box: HTMLElement, req: any) {
  const iconName = req.query.icon;
  box.innerHTML = ICONS[iconName] || "";
}
