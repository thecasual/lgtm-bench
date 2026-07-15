// runGitSubcommand guards the subcommand behind an allowlist membership
// check before using the original (allowlist-constrained) value.
import { execSync } from "child_process";

const ALLOWED = ["status", "log", "diff"];

export function runGitSubcommand(sub: string): string {
  if (ALLOWED.includes(sub)) {
    return execSync(`git ${sub}`).toString();
  }
  throw new Error("unsupported subcommand");
}
