// Test harness: runs the route and client against the Python service.
import { createServer } from "node:http";
import { POST } from "./chat-route.ts";
import { streamChat } from "./chat-client.ts";

const server = createServer(async (req, res) => {
  const chunks: Buffer[] = [];
  for await (const c of req) chunks.push(c as Buffer);
  const response = await POST(
    new Request("http://local/api/chat", { method: "POST", body: Buffer.concat(chunks) }),
  );
  res.writeHead(response.status, Object.fromEntries(response.headers));
  if (response.body) for await (const c of response.body) res.write(c);
  res.end();
});
server.listen(0, async () => {
  const { port } = server.address() as { port: number };
  const base = `http://127.0.0.1:${port}`;
  const pieces: string[] = [];
  await streamChat("Why is checkout slow?", (t) => pieces.push(t), base);
  const bad = await fetch(`${base}/api/chat`, { method: "POST", body: "{}" });
  console.log(JSON.stringify({ chunks: pieces.length, text: pieces.join(""), badStatus: bad.status }));
  server.close();
});
