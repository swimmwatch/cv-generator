const http = require("http");

const req = http.request(
  {
    hostname: "localhost",
    port: 8931,
    path: "/sse",
    method: "GET",
  },
  (res) => process.exit(res.statusCode < 500 ? 0 : 1)
);

req.on("error", () => process.exit(1));
req.end();
