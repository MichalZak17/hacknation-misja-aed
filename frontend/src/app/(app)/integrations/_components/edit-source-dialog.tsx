"use client";

import { useState } from "react";
import { PencilIcon } from "lucide-react";
import { toast } from "sonner";

import { Problems } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, type Integration, type IntegrationUpdate } from "@/lib/api";

async function save(slug: string, body: IntegrationUpdate): Promise<string[]> {
  try {
    await api.updateIntegration(slug, body);
    return [];
  } catch (err) {
    return [err instanceof ApiError ? err.detail : String(err)];
  }
}

/** "Edytuj" on the source facts: everything that describes where the data comes from. */
export function EditSourceDetails({ integration: i, onSaved }: { integration: Integration; onSaved: () => void }) {
  const initial = {
    name: i.name,
    description: i.description,
    publisher: i.publisher,
    source_url: i.source_url,
    homepage_url: i.homepage_url,
    attribution: i.attribution,
  };
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<typeof initial>) => setValues((v) => ({ ...v, ...patch }));
  // Operator files are uploaded, not fetched: they have no data URL to edit
  const fetched = !i.accepts_upload;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const changed = Object.fromEntries(
      Object.entries(values)
        .map(([k, v]) => [k, v.trim()])
        .filter(([k, v]) => v !== initial[k as keyof typeof initial]),
    );
    const problems = Object.keys(changed).length ? await save(i.slug, changed) : [];
    setBusy(false);
    setErrors(problems);
    if (problems.length) return;
    toast.success("Zapisano opis źródła.");
    setOpen(false);
    onSaved();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          setValues(initial);
          setErrors([]);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <PencilIcon data-icon="inline-start" />
          Edytuj
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-2xl">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Edytuj opis źródła</DialogTitle>
            <DialogDescription>
              {fetched && i.source_url !== values.source_url.trim()
                ? "Nowy adres zostanie użyty przy następnej synchronizacji. Najpierw uruchom „Sprawdź bez zapisu”."
                : "Opis źródła, wydawca, adres danych i atrybucja."}
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="grid gap-4 sm:grid-cols-2">
            <Field className="sm:col-span-2">
              <FieldLabel htmlFor="ed-name">Nazwa</FieldLabel>
              <Input id="ed-name" required value={values.name} onChange={(e) => set({ name: e.target.value })} />
            </Field>
            <Field className="sm:col-span-2">
              <FieldLabel htmlFor="ed-description">Opis</FieldLabel>
              <Textarea
                id="ed-description"
                rows={3}
                value={values.description}
                onChange={(e) => set({ description: e.target.value })}
              />
            </Field>
            {fetched ? (
              <Field className="sm:col-span-2">
                <FieldLabel htmlFor="ed-url">Adres danych</FieldLabel>
                <Input
                  id="ed-url"
                  type="url"
                  required={!i.config.url}
                  value={values.source_url}
                  onChange={(e) => set({ source_url: e.target.value })}
                />
              </Field>
            ) : null}
            <Field>
              <FieldLabel htmlFor="ed-publisher">Wydawca</FieldLabel>
              <Input id="ed-publisher" value={values.publisher} onChange={(e) => set({ publisher: e.target.value })} />
            </Field>
            <Field>
              <FieldLabel htmlFor="ed-homepage">Strona wydawcy</FieldLabel>
              <Input
                id="ed-homepage"
                type="url"
                value={values.homepage_url}
                onChange={(e) => set({ homepage_url: e.target.value })}
              />
            </Field>
            <Field className="sm:col-span-2">
              <FieldLabel htmlFor="ed-attribution">Atrybucja</FieldLabel>
              <Input
                id="ed-attribution"
                value={values.attribution}
                onChange={(e) => set({ attribution: e.target.value })}
              />
            </Field>
          </FieldGroup>
          <Problems errors={errors} />
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Anuluj
              </Button>
            </DialogClose>
            <Button type="submit" disabled={busy || !values.name.trim()}>
              {busy ? <Spinner data-icon="inline-start" /> : null}
              Zapisz zmiany
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
