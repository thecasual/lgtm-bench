// tailLog runs `tail -n <N>` against a fixed log file, where N is coerced
// through Number() first, so no shell syntax from the original string can
// survive into the command.
import { execSync } from "child_process";

export function tailLog(req: any): string {
  const n = Number(req.query.lines);
  return execSync(`tail -n ${n} /var/log/app.log`).toString();
}
