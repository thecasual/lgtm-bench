// promisify(exec) returns a function that still runs its string argument
// through a shell; the tainted filePath reaches it unescaped. Regression for
// the promisified-exec sink (cmdi-typescript@0.3.0).
import { exec } from "child_process";
import { promisify } from "util";

const execPromise = promisify(exec);

async function runFFprobe(filePath: string): Promise<string> {
  const { stdout } = await execPromise(`ffprobe -show_format ${filePath}`);
  return stdout;
}
