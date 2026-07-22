// CommentBody passes the caller-controlled comment text straight into
// dangerouslySetInnerHTML with no sanitizer or escaper (stored/reflected XSS).
export default function CommentBody({ text }: { text: string }) {
  return <div className="comment-body" dangerouslySetInnerHTML={{ __html: text }} />;
}
