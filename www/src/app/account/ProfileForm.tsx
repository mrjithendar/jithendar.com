"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Alert, Button, Field, Input, Textarea } from "@/components/ui/form";
import { updateProfileAction, type AccountResult } from "./actions";

type Values = { name: string; bio: string; website: string } & Record<string, string>;
type SocialField = { key: string; label: string; placeholder: string };

export function ProfileForm({ initial, limits, social }: { initial: Values; limits: { name: number; bio: number; url: number }; social: SocialField[] }) {
  const router = useRouter();
  const [bio, setBio] = useState(initial.bio);
  const [result, setResult] = useState<AccountResult | null>(null);
  const [pending, start] = useTransition();
  const errors = result && !result.ok ? (result.fieldErrors ?? {}) : {};

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    start(async () => {
      const r = await updateProfileAction(form);
      setResult(r);
      if (r.ok) router.refresh(); // header avatar/name come from the session
      else if (r.code === "UNAUTHORIZED") router.push("/login?next=/account&expired=1");
    });
  }

  const err = (name: keyof Values) => (errors[name] ? { "aria-invalid": true as const, "aria-describedby": `p-${name}-error` } : {});

  return (
    <form onSubmit={submit} className="grid grid-cols-[minmax(0,1fr)] gap-5 sm:grid-cols-2" noValidate>
      <div className="sm:col-span-2">
        <Field label="Display name" htmlFor="p-name" error={errors.name} hint="Shown next to your comments.">
          <Input id="p-name" name="name" defaultValue={initial.name} required maxLength={limits.name} autoComplete="nickname" {...err("name")} />
        </Field>
      </div>
      <div className="sm:col-span-2">
        <Field label="Short bio" htmlFor="p-bio" optional error={errors.bio} hint={`${bio.length}/${limits.bio} characters`}>
          <Textarea id="p-bio" name="bio" rows={3} value={bio} onChange={(e) => setBio(e.target.value)} maxLength={limits.bio} {...err("bio")} />
        </Field>
      </div>
      <div className="sm:col-span-2">
        <Field label="Website" htmlFor="p-website" optional error={errors.website}>
          <Input id="p-website" name="website" type="url" inputMode="url" placeholder="https://example.com" defaultValue={initial.website} maxLength={limits.url} autoComplete="url" {...err("website")} />
        </Field>
      </div>
      <p className="text-sm font-medium text-fg sm:col-span-2">Social profiles</p>
      {social.map((f) => (
        <Field key={f.key} label={f.label} htmlFor={`p-${f.key}`} optional error={errors[f.key]}>
          <Input id={`p-${f.key}`} name={f.key} type="url" inputMode="url" placeholder={f.placeholder} defaultValue={initial[f.key] ?? ""} maxLength={limits.url} {...err(f.key)} />
        </Field>
      ))}
      <div className="flex flex-col gap-3 sm:col-span-2 sm:flex-row sm:items-center">
        <Button type="submit" loading={pending}>
          {pending ? "Saving…" : "Save profile"}
        </Button>
        {result && (
          <div className="min-w-0 flex-1">
            <Alert tone={result.ok ? "success" : "error"}>{result.ok ? result.message : result.error}</Alert>
          </div>
        )}
      </div>
    </form>
  );
}
