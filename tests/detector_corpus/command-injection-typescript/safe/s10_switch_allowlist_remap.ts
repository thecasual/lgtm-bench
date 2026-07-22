// runGitSubcommand maps the caller's choice to one of a fixed set of
// literal subcommand strings via a switch statement rather than
// interpolating the caller's value directly.
import { execSync } from "child_process";

export function runGitSubcommand(sub: string): string {
  let cmd: string;
  switch (sub) {
    case "status":
      cmd = "git status";
      break;
    case "log":
      cmd = "git log";
      break;
    default:
      cmd = "git status";
  }
  return execSync(cmd).toString();
}
