"use client";

import { BracesIcon, CheckIcon, CopyIcon, DownloadIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { CodeBlock, ExternalLink } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { DeviceDetail } from "@/lib/api";

/** The device exactly as the API returns it (GET /api/devices/{id}), to read, copy or download. */
export function DeviceJson({ device }: { device: DeviceDetail }) {
  const [copied, setCopied] = useState(false);
  const json = useMemo(() => JSON.stringify(device, null, 2), [device]);
  const apiPath = `/api/devices/${encodeURIComponent(device.id)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Nie udało się skopiować do schowka.");
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${device.id}.json` });
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        {/* Close to the readiness and access badges beside it (text-xs, medium weight), a step taller */}
        <Button variant="outline" size="xs" className="font-medium">
          <BracesIcon data-icon="inline-start" />
          JSON
        </Button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] flex-col sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Dane urządzenia (JSON)</DialogTitle>
          <DialogDescription>
            Obiekt {device.id} tak, jak zwraca go API: <ExternalLink href={apiPath}>{apiPath}</ExternalLink>
          </DialogDescription>
        </DialogHeader>
        <CodeBlock value={device} className="max-h-none min-h-0 flex-1" />
        <DialogFooter>
          <Button type="button" variant="outline" onClick={download}>
            <DownloadIcon data-icon="inline-start" />
            Pobierz
          </Button>
          <Button type="button" onClick={copy}>
            {copied ? <CheckIcon data-icon="inline-start" /> : <CopyIcon data-icon="inline-start" />}
            {copied ? "Skopiowano" : "Kopiuj"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
