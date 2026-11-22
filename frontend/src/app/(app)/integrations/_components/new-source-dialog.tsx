"use client";

import { useState } from "react";
import { PlusIcon } from "lucide-react";
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
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError } from "@/lib/api";

type Details = {
  name: string;
  publisher: string;
  homepage_url: string;
  attribution: string;
};

const EMPTY: Details = { name: "", publisher: "", homepage_url: "", attribution: "" };

/**
 * "Nowy dysponent": an operator whose CSV/XLSX files an admin uploads. The file follows the reference schema, so the
 * source needs no configuration. Feeds we download from a URL are connector classes in code, not created here.
 */
export function NewSourceDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [details, setDetails] = useState<Details>(EMPTY);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<Details>) => setDetails((d) => ({ ...d, ...patch }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrors([]);
    try {
      const body = Object.fromEntries(Object.entries(details).map(([k, v]) => [k, v.trim()])) as Details;
      const created = await api.createIntegration({ ...body, connector: "operator_file" });
      toast.success(`Dodano dysponenta „${created.name}”. Wgraj plik na jego stronie.`);
      setOpen(false);
      setDetails(EMPTY);
      onCreated();
    } catch (err) {
      setErrors([err instanceof ApiError ? err.detail : String(err)]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setDetails(EMPTY);
          setErrors([]);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">
          <PlusIcon data-icon="inline-start" />
          Dodaj dysponenta
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-2xl">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Nowy dysponent</DialogTitle>
            <DialogDescription>
              Dysponent przekazuje plik CSV lub XLSX we wzorcowym zakresie danych, a administrator wgrywa go na stronie
              źródła. Plik przechodzi ten sam proces co inne źródła: test, walidacja, zapis i scalanie.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="grid gap-4 sm:grid-cols-2">
            <Field className="sm:col-span-2">
              <FieldLabel htmlFor="ns-name">Nazwa</FieldLabel>
              <Input id="ns-name" required value={details.name} onChange={(e) => set({ name: e.target.value })} />
            </Field>
            <Field>
              <FieldLabel htmlFor="ns-publisher">Dysponent / wydawca</FieldLabel>
              <Input id="ns-publisher" value={details.publisher} onChange={(e) => set({ publisher: e.target.value })} />
            </Field>
            <Field>
              <FieldLabel htmlFor="ns-homepage">Strona dysponenta</FieldLabel>
              <Input
                id="ns-homepage"
                type="url"
                value={details.homepage_url}
                onChange={(e) => set({ homepage_url: e.target.value })}
              />
            </Field>
            <Field className="sm:col-span-2">
              <FieldLabel htmlFor="ns-attribution">Atrybucja</FieldLabel>
              <Input
                id="ns-attribution"
                value={details.attribution}
                onChange={(e) => set({ attribution: e.target.value })}
              />
              <FieldDescription>Tekst, który musi towarzyszyć danym, np. „Gmina Miasto Krosno”.</FieldDescription>
            </Field>
          </FieldGroup>
          <Problems errors={errors} />
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Anuluj
              </Button>
            </DialogClose>
            <Button type="submit" disabled={busy || !details.name.trim()}>
              {busy ? <Spinner data-icon="inline-start" /> : null}
              Dodaj dysponenta
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
