// Returns HTML but every interpolation is escaped, so the return-HTML sink must
// stay clean (the shared sanitizer set clears the escaped value).
import express from "express";
import { escapeHtml } from "./util";
function buildEmailBody(req: express.Request): string {
  const message = req.body.message;
  return `<p>${escapeHtml(message)}</p>`;
}
