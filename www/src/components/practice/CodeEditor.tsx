"use client";

import { useEffect, useRef } from "react";

/**
 * Python editor on CodeMirror 6 (chosen over Monaco because Monaco does not support mobile browsers): syntax
 * highlighting, line numbers, bracket matching, autocomplete of keywords and names in the file, search,
 * undo history, auto-indent, keyboard accessibility (Tab indents; Esc then Tab leaves the editor).
 * Shortcuts: Ctrl/Cmd+Enter = Run, Ctrl/Cmd+Shift+Enter = Submit, Ctrl/Cmd+S = save draft.
 */
export type EditorHandle = { setValue: (code: string) => void; focus: () => void };

export function CodeEditor({
  value,
  onChange,
  readOnly = false,
  dark,
  fontSize = 14,
  onRun,
  onSubmit,
  onSave,
  label = "Python code editor",
  handleRef,
}: {
  value: string;
  onChange?: (code: string) => void;
  readOnly?: boolean;
  dark: boolean;
  fontSize?: number;
  onRun?: () => void;
  onSubmit?: () => void;
  onSave?: () => void;
  label?: string;
  handleRef?: (h: EditorHandle | null) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onChange, onRun, onSubmit, onSave });
  useEffect(() => {
    callbacks.current = { onChange, onRun, onSubmit, onSave };
  });
  const viewRef = useRef<import("@codemirror/view").EditorView | null>(null);
  const initial = useRef(value);

  useEffect(() => {
    let destroyed = false;
    (async () => {
      const [{ EditorView, keymap }, { EditorState }, { python }, cmds, lang, { basicSetup }] = await Promise.all([
        import("@codemirror/view"),
        import("@codemirror/state"),
        import("@codemirror/lang-python"),
        import("@codemirror/commands"),
        import("@codemirror/language"),
        import("codemirror"),
      ]);
      if (destroyed || !host.current) return;
      const theme = EditorView.theme(
        {
          "&": { fontSize: `${fontSize}px`, height: "100%", backgroundColor: "var(--color-surface)", color: "var(--color-fg)" },
          ".cm-content": { fontFamily: "var(--font-jetbrains), ui-monospace, monospace", caretColor: "var(--color-accent)" },
          ".cm-gutters": { backgroundColor: "var(--color-surface-muted)", color: "var(--color-fg-subtle)", borderRight: "1px solid var(--color-line)" },
          ".cm-activeLine, .cm-activeLineGutter": { backgroundColor: "color-mix(in oklab, var(--color-accent) 7%, transparent)" },
          "&.cm-focused": { outline: "none" },
          ".cm-scroller": { overflow: "auto" },
        },
        { dark },
      );
      const run = (fn?: () => void) => () => {
        fn?.();
        return true;
      };
      const view = new EditorView({
        parent: host.current,
        state: EditorState.create({
          doc: initial.current,
          extensions: [
            keymap.of([
              { key: "Mod-Enter", run: run(() => callbacks.current.onRun?.()) },
              { key: "Mod-Shift-Enter", run: run(() => callbacks.current.onSubmit?.()) },
              { key: "Mod-s", run: run(() => callbacks.current.onSave?.()), preventDefault: true },
              cmds.indentWithTab,
            ]),
            // basicSetup: line numbers, active line, bracket matching, autocomplete, search, history, folding.
            basicSetup,
            python(),
            lang.indentUnit.of("    "),
            EditorState.tabSize.of(4),
            theme,
            EditorView.editable.of(!readOnly),
            EditorState.readOnly.of(readOnly),
            EditorView.contentAttributes.of({ "aria-label": label }),
            EditorView.updateListener.of((u) => {
              if (u.docChanged) callbacks.current.onChange?.(u.state.doc.toString());
            }),
          ],
        }),
      });
      viewRef.current = view;
      handleRef?.({
        setValue: (code) => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: code } }),
        focus: () => view.focus(),
      });
    })();
    return () => {
      destroyed = true;
      viewRef.current?.destroy();
      viewRef.current = null;
      handleRef?.(null);
    };
    // The editor is rebuilt only when its look changes; content flows through the update listener.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dark, fontSize, readOnly]);

  // Keep the latest text across rebuilds (theme or font changes).
  useEffect(() => {
    initial.current = value;
  }, [value]);

  return <div ref={host} className="h-full min-h-[18rem] overflow-hidden" data-testid="code-editor" />;
}
