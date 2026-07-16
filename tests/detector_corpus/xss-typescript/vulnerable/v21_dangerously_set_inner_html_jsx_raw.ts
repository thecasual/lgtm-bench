// CommentBody renders a user-supplied comment straight into the DOM via a raw
// dangerouslySetInnerHTML JSX attribute (double-brace object literal), with no
// sanitizer. This is the JSX shape the typescript grammar cannot parse, caught
// by the generic-mode backstop rule.
import React from "react";

export function CommentBody(props: { text: string }) {
  return <div className="comment-body" dangerouslySetInnerHTML={{ __html: props.text }} />;
}
