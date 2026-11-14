// app/api/chat/route.ts: a Next.js Route Handler that forwards a chat
// request to the Python AI service and streams its answer back.
import { z } from "zod";

const ChatRequest = z.object({
  message: z.string().trim().min(1).max(2000),
});

export async function POST(req: Request): Promise<Response> {
  const parsed = ChatRequest.safeParse(await req.json().catch(() => null));
  if (!parsed.success) {
    return Response.json({ error: "message is required" }, { status: 400 });
  }

  const upstream = await fetch(`${process.env.AI_SERVICE_URL}/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed.data),
    signal: req.signal, // stop the model call if the user closes the tab
  });
  if (!upstream.ok || !upstream.body) {
    return Response.json({ error: "AI service unavailable" }, { status: 502 });
  }

  // Pass the stream through without waiting for the full answer.
  return new Response(upstream.body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
