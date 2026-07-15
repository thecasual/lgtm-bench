// tarDirectory shells out via spawn("sh", ["-c", ...]) so it can use shell
// globbing, but the directory name is interpolated straight into the
// command text.
import { spawn } from "child_process";

export function tarDirectory(dir: string) {
  spawn("sh", ["-c", `tar -czf out.tar.gz ${dir}/*`]);
}
