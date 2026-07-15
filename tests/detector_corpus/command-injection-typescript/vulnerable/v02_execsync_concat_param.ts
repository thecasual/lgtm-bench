// pingHost builds the ping command by string concatenation from a
// caller-supplied hostname, then runs it synchronously.
import { execSync } from "child_process";

export function pingHost(host: string): string {
  return execSync("ping -c 1 " + host).toString();
}
