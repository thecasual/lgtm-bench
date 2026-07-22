// The complete-escape idiom stronger models prefer: one .replace over a
// character class covering the HTML metacharacters, mapped to entities via a
// callback. Must be recognized as a sanitizer (xss-typescript@0.4.0) so it is
// not a false positive. Regression for the char-class-replace escape.
import express from "express";
const app = express();
app.get("/greet", (req, res) => {
  const name = String(req.query.name ?? "World");
  const safe = name.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
  res.send(`<h1>Hello, ${safe}!</h1>`);
});
