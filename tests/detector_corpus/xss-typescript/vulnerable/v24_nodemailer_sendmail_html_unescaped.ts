// Unescaped req.body interpolated directly into a nodemailer sendMail html:
// field (inline options object). Regression for the sendMail html sink
// (xss-typescript@0.4.0). NOTE: the assign-then-call form with an intermediate
// htmlBody variable is a documented remaining gap (see METHODOLOGY).
import nodemailer from "nodemailer";
import express from "express";
const app = express();
app.post("/contact", (req, res) => {
  const { senderName, message } = req.body;
  const transporter = nodemailer.createTransport({});
  transporter.sendMail({
    from: "a@b.com",
    to: "c@d.com",
    subject: "New contact",
    html: `<p>Name: ${senderName}</p><p>${message}</p>`,
  });
  res.end();
});
