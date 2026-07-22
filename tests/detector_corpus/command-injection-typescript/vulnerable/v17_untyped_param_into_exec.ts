// Plain-JS helper inside a .ts file: the parameter has no type annotation but
// is still the caller-controlled entry point, and it flows unescaped into a
// child_process.exec command string. Regression for the untyped-parameter
// source (cmdi-typescript@0.3.0).
const childProcess = require("child_process");

function resizeImage(filename) {
  const command = `convert ${filename} -resize 50% resized.png`;
  return new Promise((resolve, reject) => {
    childProcess.exec(command, (error, stdout) => {
      if (error) reject(error);
      else resolve(stdout.trim());
    });
  });
}
