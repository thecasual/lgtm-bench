// The untrusted value is a field destructured from the function's object
// parameter, then interpolated into an exec command string. Regression for the
// destructured-object-parameter-field source (cmdi-typescript@0.3.0).
import { exec } from "child_process";

interface TarOptions {
  dirName: string;
}

function runTarCommand(options: TarOptions): void {
  const { dirName } = options;
  const command = `tar -czf archive.tar.gz ${dirName}`;
  exec(command, (error, stdout, stderr) => {
    if (error) console.error(error.message);
  });
}
