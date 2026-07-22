// spawnSync('sh', ['-c', cmd]) explicitly launches a shell; the tainted param
// is interpolated into cmd. Regression for the *Sync twins in the sh -c sink
// list (cmdi-typescript@0.4.0).
import { spawnSync } from "child_process";
function archiveFolder(dirName: string): void {
  const command = `tar -czf ${dirName}.tar.gz ${dirName}`;
  const result = spawnSync("sh", ["-c", command]);
}
