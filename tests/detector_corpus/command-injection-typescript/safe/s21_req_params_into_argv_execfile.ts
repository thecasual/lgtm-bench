// Destructured req.params (now a source) reaching a safe argv-array execFile
// with no shell must stay clean: guards the new params source from over-flagging.
import { execFile } from "child_process";
import express from "express";
const app = express();
app.get("/lint/:filename", async (req, res) => {
  const { filename } = req.params;
  execFile("eslint", [filename]);
  res.end();
});
