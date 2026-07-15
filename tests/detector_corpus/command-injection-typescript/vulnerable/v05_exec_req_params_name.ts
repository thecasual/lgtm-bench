// gzipUpload gzips a file whose path comes straight from the route params.
import * as child_process from "child_process";

export function gzipUpload(req: any) {
  child_process.exec(`gzip ${req.params.path}`, () => {});
}
