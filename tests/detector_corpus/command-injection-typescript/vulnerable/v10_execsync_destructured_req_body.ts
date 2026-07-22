// backupDirectory destructures the target directory off req.body and hands
// it straight to tar.
import { execSync } from "child_process";

export function backupDirectory(req: any) {
  const { dir } = req.body;
  execSync(`tar -czf backup.tar.gz ${dir}`);
}
