// runLinter shells out via execFile("bash", ["-c", ...]) built from string
// concatenation.
import { execFile } from "child_process";

export function runLinter(target: string) {
  execFile("bash", ["-c", "eslint " + target]);
}
