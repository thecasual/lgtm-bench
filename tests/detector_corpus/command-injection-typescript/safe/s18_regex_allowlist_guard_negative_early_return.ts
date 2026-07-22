// pingHost rejects any host that doesn't match a restrictive regex
// character-class allowlist up front, then safely interpolates the
// now-constrained value later. The `[a-zA-Z0-9.-]+` class, anchored with
// ^ and $, admits no shell metacharacters or whitespace, so command
// injection is impossible regardless of what the caller passes in.
import { exec } from "child_process";

export function pingHost(host: string): void {
  if (!/^[a-zA-Z0-9.-]+$/.test(host)) {
    throw new Error("invalid host");
  }
  exec(`ping -c 1 ${host}`);
}
