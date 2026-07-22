// Destructured req.params inside an anonymous Express arrow handler flows
// unescaped into child_process.exec. Regression for the standalone req.params
// destructure source (cmdi-typescript@0.4.0).
import { exec } from "child_process";
import express from "express";
const app = express();
app.get("/lint/:filename", async (req, res) => {
  const { filename } = req.params;
  const command = `eslint ${filename}`;
  await exec(command);
  res.end();
});
