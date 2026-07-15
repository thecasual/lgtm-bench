// resizeImage passes filename as a separate argv element, never through a
// shell, so it cannot be used to inject extra shell commands.
import { execFile } from "child_process";

export function resizeImage(filename: string) {
  execFile("convert", [filename, "-resize", "50%", "out.png"]);
}
