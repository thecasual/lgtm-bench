// pingHost uses spawn with an argv array (no shell invoked), so the
// hostname can never break out into a second command.
import { spawn } from "child_process";

export function pingHost(host: string) {
  spawn("ping", ["-c", "1", host]);
}
