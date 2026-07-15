// gzipFile shells out via spawn with an absolute "/bin/bash" path and the
// request-supplied file path interpolated into the -c command text.
import { spawn } from "child_process";

export function gzipFile(req: any) {
  const path = req.query.path;
  spawn("/bin/bash", ["-c", `gzip ${path}`]);
}
