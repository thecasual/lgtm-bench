// countLines shells out to `wc -l` for a filename taken from the request
// body.
import { execSync } from "child_process";

export function countLines(req: any): string {
  return execSync(`wc -l ${req.body.filename}`).toString();
}
