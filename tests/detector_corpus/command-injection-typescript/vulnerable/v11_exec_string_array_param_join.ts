// runGitCommand joins caller-supplied argument tokens straight into a git
// command line before shelling out.
import { exec } from "child_process";

export function runGitCommand(args: string[]) {
  const cmd = "git " + args.join(" ");
  exec(cmd);
}
