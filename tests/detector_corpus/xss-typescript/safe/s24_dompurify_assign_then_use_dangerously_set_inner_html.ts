// CommentBody binds the DOMPurify-sanitized markup to a variable first and then
// passes that variable to dangerouslySetInnerHTML (the assign-then-use form real
// components write), so the rendered __html is escaped/sanitized markup.
import DOMPurify from "dompurify";

export function CommentBody({ text }: { text: string }) {
  const clean = DOMPurify.sanitize(text);
  return <div className="comment-body" dangerouslySetInnerHTML={{ __html: clean }} />;
}
