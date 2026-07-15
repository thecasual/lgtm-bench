// convertMedia uses the namespaced child_process.execSync receiver form
// with a template-literal path from the request.
import * as cp from "child_process";

export function convertMedia(req: any) {
  cp.execSync(`ffmpeg -i ${req.params.input} out.mp4`);
}
