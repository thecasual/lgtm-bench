// sendMail html field built from an escaped value must not flag.
import nodemailer from "nodemailer";
import express from "express";
import { escapeHtml } from "./util";
const app = express();
app.post("/contact", (req, res) => {
  const { message } = req.body;
  const transporter = nodemailer.createTransport({});
  transporter.sendMail({ from: "a@b.com", to: "c@d.com", subject: "x", html: `<p>${escapeHtml(message)}</p>` });
  res.end();
});
