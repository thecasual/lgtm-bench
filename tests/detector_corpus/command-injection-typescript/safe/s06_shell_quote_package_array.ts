// runGitCommand uses the shell-quote package's array-of-args quote() helper
// to escape each token before building the command string.
import { exec } from "child_process";
import { quote } from "shell-quote";

export function runGitCommand(args: string[]) {
  const cmd = "git " + quote([...args]);
  exec(cmd);
}
