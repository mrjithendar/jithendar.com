// UI state for the chat component.
type ChatState =
  | { status: "idle" }
  | { status: "streaming"; text: string }
  | { status: "error"; message: string };

export function label(state: ChatState): string {
  switch (state.status) {
    case "idle":
      return "Ask a question";
    case "streaming":
      return state.text;
    case "error":
      return state.message;
  }
}
