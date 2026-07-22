// greetRoute escapes the caller-supplied name with the `escape` helper from
// the html-escaper / escape-html package before interpolating it into the
// response body, neutralizing any markup in the name.
import { escape } from "html-escaper";

export function greetRoute(req: any, res: any) {
  const name = req.query.name;
  res.send(`<h1>Hello, ${escape(name)}!</h1>`);
}
