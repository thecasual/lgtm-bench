// tailLog coerces the caller-supplied line count to an integer with
// Number.parseInt before interpolating it, so no shell metacharacters can
// survive into the command text.
import { execSync } from "child_process";

export function tailLog(count: string): string {
  const n = Number.parseInt(count, 10);
  return execSync(`tail -n ${n} /var/log/app.log`).toString();
}
