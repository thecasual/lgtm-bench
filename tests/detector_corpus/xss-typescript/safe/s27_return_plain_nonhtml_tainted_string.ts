// A function that returns a tainted but NON-HTML string (no angle-bracket tag)
// must NOT flag: proves the return-HTML sink is scoped and does not treat every
// tainted return as XSS.
import express from "express";
function buildCacheKey(req: express.Request): string {
  const id = req.query.id as string;
  return `user-${id}`;
}
