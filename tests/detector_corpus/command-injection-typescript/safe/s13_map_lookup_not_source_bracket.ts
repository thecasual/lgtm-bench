// runAction looks up the requested action name in a fixed map of literal
// commands; the tainted key never itself reaches the command text, only one
// of the map's own literal values can.
import { execSync } from "child_process";

const COMMANDS: Record<string, string> = {
  status: "git status",
  log: "git log",
};

export function runAction(action: string): string {
  const cmd = COMMANDS[action];
  return execSync(cmd).toString();
}
