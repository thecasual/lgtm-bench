// renderProfileHtml server-renders a small HTML fragment from a props
// object's display name, with no escaping before it hits the response.
export function renderProfileHtml(props: any, res: any) {
  res.send("<div class='profile'>" + props.displayName + "</div>");
}
