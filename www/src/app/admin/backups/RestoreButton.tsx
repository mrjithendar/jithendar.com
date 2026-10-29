"use client";

/** One-click restore, after a clear confirmation (a safety backup of the current state is taken first). */
export function RestoreButton({ name, created, action }: { name: string; created: string; action: (form: FormData) => Promise<void> }) {
  return (
    <form
      action={action}
      onSubmit={(e) => {
        const ok = window.confirm(
          `Restore the backup from ${created}?\n\nPosts, pages, categories, comments, messages, media records, redirects and Appearance settings are replaced with that backup. ` +
            "Accounts are kept (missing ones are recreated). The current state is saved to R2 first, so you can restore it again if needed.",
        );
        if (!ok) e.preventDefault();
      }}
    >
      <input type="hidden" name="name" value={name} />
      <button type="submit" className="font-semibold text-red-600 underline dark:text-red-400">Restore</button>
    </form>
  );
}
