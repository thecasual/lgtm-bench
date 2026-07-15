// renderBio sanitizes the bio into a local const first and then assigns that
// cleaned value into innerHTML; the sanitizer clears the taint before the
// intermediate variable reaches the sink.
export function renderBio(el: HTMLElement, bio: string) {
  const clean = DOMPurify.sanitize(bio);
  el.innerHTML = clean;
}
