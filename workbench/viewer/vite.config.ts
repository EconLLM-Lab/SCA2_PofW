// Serves the local capture exports (../exports, gitignored) at /exports.
// The exports never enter the bundle. The viewer reads them only from this dev server.
import { defineConfig } from "vite";
import fs from "node:fs";
import path from "node:path";

const EXPORTS = path.resolve(__dirname, "../exports");

export default defineConfig({
  server: { host: "127.0.0.1", port: 5178, strictPort: true },
  plugins: [
    {
      name: "local-exports",
      configureServer(server) {
        server.middlewares.use("/exports", (req, res, next) => {
          const rel = decodeURIComponent((req.url ?? "/").split("?")[0]);
          const file = path.resolve(EXPORTS, "." + rel);
          if (!file.startsWith(EXPORTS + path.sep) || !fs.existsSync(file)) return next();
          res.setHeader("Content-Type", file.endsWith(".json") ? "application/json" : "application/octet-stream");
          res.setHeader("Cache-Control", "no-store");
          fs.createReadStream(file).pipe(res);
        });
      },
    },
  ],
});
