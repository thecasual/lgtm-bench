// appendComment inserts a new comment block using insertAdjacentHTML, with
// the comment body taken straight from the request body.
export function appendComment(list: HTMLElement, req: any) {
  list.insertAdjacentHTML("beforeend", `<li>${req.body.comment}</li>`);
}
