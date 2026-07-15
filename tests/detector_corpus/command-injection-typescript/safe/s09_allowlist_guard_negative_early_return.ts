// runGitSubcommand rejects any subcommand not on the allowlist up front,
// then safely interpolates the now-constrained value later.
import { execSync } from "child_process";

const ALLOWED = ["status", "log", "diff"];

export function runGitSubcommand(sub: string): string {
  if (!ALLOWED.includes(sub)) {
    throw new Error("unsupported subcommand");
  }
  return execSync(`git ${sub}`).toString();
}
