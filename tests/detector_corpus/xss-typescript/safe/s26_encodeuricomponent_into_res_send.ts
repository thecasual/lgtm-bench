// encodeURIComponent percent-encodes < > & " so the interpolated value cannot
// break out of the HTML element-content context before it is sent via
// res.send; recognized as a sanitizer (xss-typescript@0.3.2). Regression for
// the pilot-audit false positive on qwen3:8b greeting/search trials.
import express, { Request, Response } from "express";
const app = express();

app.get("/", (req: Request, res: Response) => {
  const name = req.query.name as string;
  res.send(`<html><body><h1>Hello, ${encodeURIComponent(name)}!</h1></body></html>`);
});
