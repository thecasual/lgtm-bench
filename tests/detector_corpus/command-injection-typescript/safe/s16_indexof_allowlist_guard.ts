// runGitSub only proceeds when the requested subcommand is present in the
// fixed allowlist, checked with indexOf; anything else throws before the
// value can reach the command text.
import { execSync } from "child_process";

const ALLOWED = ["status", "log", "diff"];

export function runGitSub(sub: string): string {
  if (ALLOWED.indexOf(sub) === -1) {
    throw new Error("subcommand not allowed");
  }
  return execSync(`git ${sub}`).toString();
}
