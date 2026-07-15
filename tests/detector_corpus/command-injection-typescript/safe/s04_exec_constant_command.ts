// listUploads runs a fully constant command string with no interpolated
// input at all.
import { exec } from "child_process";

export function listUploads() {
  exec("ls -la /var/uploads", (err, stdout) => console.log(stdout));
}
