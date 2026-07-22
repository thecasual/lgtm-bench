// resizeImage interpolates the caller-supplied filename straight into the
// ImageMagick command line via a template literal.
import { exec } from "child_process";

export function resizeImage(filename: string) {
  exec(`convert ${filename} -resize 50% out.png`, (err, stdout) => {
    console.log(stdout);
  });
}
