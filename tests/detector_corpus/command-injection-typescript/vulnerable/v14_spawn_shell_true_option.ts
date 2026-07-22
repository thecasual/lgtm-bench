// runReport hands a fully interpolated command string to spawn with the
// { shell: true } option, so the whole string is run through /bin/sh.
import { spawn } from "child_process";

export function runReport(name: string) {
  spawn(`generate-report ${name}`, { shell: true });
}
