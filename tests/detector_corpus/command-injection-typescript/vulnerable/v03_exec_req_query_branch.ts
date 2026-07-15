// runGitLog shells out to `git log` for a branch name taken straight off
// the query string.
import { exec } from "child_process";

export function runGitLog(req: any, res: any) {
  exec(`git log ${req.query.branch}`, (err, stdout) => {
    res.send(stdout);
  });
}
