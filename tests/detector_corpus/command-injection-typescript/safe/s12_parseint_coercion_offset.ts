// runGitLog only ever interpolates a parseInt-coerced depth value into the
// command text.
import { execSync } from "child_process";

export function runGitLog(req: any): string {
  const depth = parseInt(req.query.depth, 10);
  return execSync(`git log -n ${depth}`).toString();
}
