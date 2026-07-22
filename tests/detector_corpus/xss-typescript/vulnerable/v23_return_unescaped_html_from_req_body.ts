// A function that builds and RETURNS an unescaped HTML string from req.body,
// with no in-snippet res.send/innerHTML/sendMail. Regression for the scoped
// return-HTML sink (xss-typescript@0.4.0).
import express from "express";
function buildEmailBody(req: express.Request): string {
  const senderName = req.body.senderName;
  const message = req.body.message;
  return `<p>From: ${senderName}</p><p>${message}</p>`;
}
