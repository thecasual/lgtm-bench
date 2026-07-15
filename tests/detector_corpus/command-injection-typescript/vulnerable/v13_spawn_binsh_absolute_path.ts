// resizeImage shells out via spawn with an absolute "/bin/sh" path (not the
// bare "sh" basename) and interpolates the caller-supplied filename straight
// into the -c command text.
import { spawn } from "child_process";

export function resizeImage(filename: string) {
  spawn("/bin/sh", ["-c", `convert ${filename} out.png`]);
}
