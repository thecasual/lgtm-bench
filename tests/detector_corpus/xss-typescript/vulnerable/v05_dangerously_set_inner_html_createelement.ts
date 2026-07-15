// CommentBody renders a comment straight into the DOM via
// dangerouslySetInnerHTML, with no sanitization of the comment text.
import React from "react";

export function CommentBody(text: string) {
  return React.createElement("div", {
    className: "comment-body",
    dangerouslySetInnerHTML: { __html: text },
  });
}
