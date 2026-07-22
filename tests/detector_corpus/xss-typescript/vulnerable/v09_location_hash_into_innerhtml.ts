// showStatusFromHash reads a status message out of the URL fragment and
// drops it straight into the page via innerHTML.
export function showStatusFromHash(statusBox: HTMLElement) {
  statusBox.innerHTML = "<span>" + location.hash.slice(1) + "</span>";
}
