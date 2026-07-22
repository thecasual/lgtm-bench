// runFfprobe builds the command with a `+=` accumulation chain before
// handing it to exec.
import { exec } from "child_process";

export function runFfprobe(mediaPath: string) {
  let cmd = "ffprobe -v error -show_format ";
  cmd += mediaPath;
  exec(cmd);
}
