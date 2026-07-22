// pingHost passes the hostname as one element of an argv array to spawn
// with no shell involved at all, even though the element itself is
// dynamic - the safe default idiom.
import { spawn } from "child_process";

export function pingHost(req: any) {
  const host = req.query.host;
  spawn("ping", ["-c", "1", host]);
}
