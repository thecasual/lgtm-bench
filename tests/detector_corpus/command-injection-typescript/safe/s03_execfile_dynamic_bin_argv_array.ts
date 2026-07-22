// runLinter takes even the binary name from the caller, but still passes
// arguments through the argv array rather than a shell string, so this is
// the safe default idiom (spec: execFile(bin, [args]) must not flag).
import { execFile } from "child_process";

export function runLinter(bin: string, target: string) {
  execFile(bin, ["--fix", target]);
}
