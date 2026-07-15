// searchLogs destructures the search term off req.query and interpolates it
// into a grep command.
import { exec } from "child_process";

export function searchLogs(req: any) {
  const { term } = req.query;
  exec(`grep ${term} /var/log/app.log`);
}
