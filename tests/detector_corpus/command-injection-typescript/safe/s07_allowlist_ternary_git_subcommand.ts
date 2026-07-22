// runGitSubcommand only ever runs one of a fixed set of subcommands: the
// tainted value is checked against an allowlist and replaced with a safe
// default otherwise before it ever reaches the command text.
import { execSync } from "child_process";

const ALLOWED = ["status", "log", "diff"];

export function runGitSubcommand(sub: string): string {
  const safeSub = ALLOWED.includes(sub) ? sub : "status";
  return execSync(`git ${safeSub}`).toString();
}
