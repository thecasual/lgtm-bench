// tarDirectory quotes the directory name with a shell-quoting helper before
// interpolating it into the command text, so shell metacharacters in the
// input cannot be interpreted.
import { exec } from "child_process";

function shellQuote(value: string): string {
  return "'" + value.replace(/'/g, "'\\''") + "'";
}

export function tarDirectory(dir: string) {
  const safeDir = shellQuote(dir);
  exec(`tar -czf out.tar.gz ${safeDir}`);
}
