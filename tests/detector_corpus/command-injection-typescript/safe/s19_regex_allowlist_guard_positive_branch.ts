// pingHost only interpolates the host into the shell command inside the
// branch where a restrictive regex character-class allowlist test already
// passed. The `[a-zA-Z0-9.-]+` class, anchored with ^ and $, admits no
// shell metacharacters or whitespace, so command injection is impossible
// regardless of what the caller passes in.
import { exec } from "child_process";

export function pingHost(host: string): void {
  if (/^[a-zA-Z0-9.-]+$/.test(host)) {
    exec(`ping -c 1 ${host}`);
  }
}
