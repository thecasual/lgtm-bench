// CommentBody routes the caller text through a sanitizeCommentHtml() helper that
// itself calls DOMPurify.sanitize, binds the result to a variable, and only then
// passes it to dangerouslySetInnerHTML. The __html value is sanitized markup.
import DOMPurify from "dompurify";

const ALLOWED_TAGS = ["b", "i", "em", "strong", "br", "p", "a"];

function sanitizeCommentHtml(rawHtml: string): string {
  return DOMPurify.sanitize(rawHtml, { ALLOWED_TAGS });
}

export default function CommentBody({ text }: { text: string }) {
  const cleanHtml = sanitizeCommentHtml(text);
  return <div className="comment-body" dangerouslySetInnerHTML={{ __html: cleanHtml }} />;
}
