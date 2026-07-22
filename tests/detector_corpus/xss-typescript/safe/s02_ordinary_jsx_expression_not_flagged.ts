// CommentBody uses an ordinary JSX expression, which React auto-escapes;
// no dangerouslySetInnerHTML is involved (spec: plain {x} JSX must not
// flag).
export function CommentBody(text: string) {
  return <div className="comment-body">{text}</div>;
}
