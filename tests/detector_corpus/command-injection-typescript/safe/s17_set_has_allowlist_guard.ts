// runGitSub restricts the subcommand to members of a fixed allow-Set,
// checked with Set.has; a non-member throws before it can reach the
// command text.
import { execSync } from "child_process";

const ALLOWED = new Set(["status", "log", "diff"]);

export function runGitSub(sub: string): string {
  if (!ALLOWED.has(sub)) {
    throw new Error("subcommand not allowed");
  }
  return execSync(`git ${sub}`).toString();
}
