// In the React chat component: show text as it arrives.
export async function streamChat(
  message: string,
  onText: (chunk: string) => void,
  baseUrl = "",
): Promise<void> {
  const res = await fetch(`${baseUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok || !res.body) throw new Error(`chat failed: HTTP ${res.status}`);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onText(value);
  }
}
