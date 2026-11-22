"use client";

import { useState } from "react";
import { EllipsisIcon, FlaskConicalIcon, HistoryIcon, RefreshCwIcon } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError, type Integration, type RunKind } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

type Pending = { kind: RunKind; dry: boolean } | null;

/**
 * Sync buttons for one integration. Until the historical import has run, it is the main action; afterwards the main
 * action is a regular sync and re-running the historical import sits in the overflow menu behind a confirmation.
 */
export function SyncActions({
  integration,
  onQueued,
  size = "sm",
}: {
  integration: Integration;
  onQueued: () => void;
  size?: "sm" | "default";
}) {
  const [busy, setBusy] = useState<Pending>(null);
  const [confirmRerun, setConfirmRerun] = useState(false);
  const disabled = !integration.enabled || integration.running || busy !== null;
  const imported = Boolean(integration.historical_completed_at);

  async function trigger(kind: RunKind, dry: boolean, force = false) {
    setBusy({ kind, dry });
    try {
      await api.sync(integration.slug, { kind, dry_run: dry, force });
      toast.success(
        dry
          ? "Sprawdzenie w kolejce. Wynik pojawi się w historii."
          : kind === "historical"
            ? "Import całego zbioru w kolejce."
            : "Synchronizacja w kolejce.",
      );
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : String(e));
    } finally {
      setBusy(null);
      onQueued();
    }
  }

  const icon = (kind: RunKind, dry: boolean, Icon: typeof RefreshCwIcon) =>
    busy && busy.kind === kind && busy.dry === dry ? <Spinner data-icon="inline-start" /> : <Icon data-icon="inline-start" />;

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        {imported ? (
          <Button size={size} disabled={disabled} onClick={() => void trigger("periodic", false)}>
            {icon("periodic", false, RefreshCwIcon)}
            Synchronizuj teraz
          </Button>
        ) : (
          <Button size={size} variant="cta" disabled={disabled} onClick={() => void trigger("historical", false)}>
            {icon("historical", false, HistoryIcon)}
            Importuj cały zbiór
          </Button>
        )}
        <Button
          size={size}
          variant="ghost"
          disabled={disabled}
          title="Pobiera i sprawdza dane, ale niczego nie zapisuje."
          onClick={() => void trigger("periodic", true)}
        >
          {icon("periodic", true, FlaskConicalIcon)}
          Sprawdź bez zapisu
        </Button>
        {imported ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size={size === "sm" ? "icon-sm" : "icon"} variant="ghost" disabled={disabled} aria-label="Więcej akcji">
                <EllipsisIcon />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => setConfirmRerun(true)}>
                <HistoryIcon />
                Importuj cały zbiór ponownie…
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>

      <AlertDialog open={confirmRerun} onOpenChange={setConfirmRerun}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Zaimportować cały zbiór ponownie?</AlertDialogTitle>
            <AlertDialogDescription>
              Ostatni pełny import „{integration.name}” był {formatDateTime(integration.historical_completed_at)}. Ponowny
              import pobierze i zapisze wszystkie rekordy od nowa. Do bieżących zmian wystarczy „Synchronizuj teraz”.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Anuluj</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmRerun(false);
                void trigger("historical", false, true);
              }}
            >
              Importuj ponownie
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
