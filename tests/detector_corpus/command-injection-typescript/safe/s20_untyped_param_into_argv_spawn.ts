// An untyped parameter (now a taint source) that flows into a safe argv-array
// spawn with no shell is NOT a command-injection sink and must stay clean:
// guards the broadened untyped-parameter source against over-flagging.
const childProcess = require("child_process");

function resizeImage(filename) {
  return childProcess.spawnSync("convert", [filename, "-resize", "50%", "out.png"]);
}
