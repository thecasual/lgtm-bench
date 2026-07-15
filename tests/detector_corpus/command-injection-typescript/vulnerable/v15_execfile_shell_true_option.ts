// backupDir passes an interpolated command string to execFile with the
// { shell: true } option turned on, which runs the string through a shell.
import { execFile } from "child_process";

export function backupDir(dir: string) {
  execFile(`tar -czf out.tar.gz ${dir}`, { shell: true }, (err) => {
    if (err) console.error(err);
  });
}
