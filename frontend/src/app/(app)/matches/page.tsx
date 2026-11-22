"use client";

import Link from "next/link";
import { useState } from "react";
import { CheckIcon, XIcon } from "lucide-react";
import { toast } from "sonner";

import {
  AccessBadge,
  EmptyState,
  ErrorAlert,
  LoadingRows,
  PageHeader,
  Pager,
  ReadinessBadge,
} from "@/components/app/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { api, ApiError, type DeviceListItem, type Match } from "@/lib/api";
import { formatDate, formatDistance, formatRelative } from "@/lib/format";
import { useApi } from "@/lib/use-api";

const LIMIT = 20;
type Status = "pending" | "accepted" | "rejected";

export default function MatchesPage() {
  const [status, setStatus] = useState<Status>("pending");
  const [offset, setOffset] = useState(0);
  const matches = useApi(`matches:${status}:${offset}`, () => api.matches({ status, limit: LIMIT, offset }));

  return (
    <>
      <PageHeader
        title="Duplikaty"
        actions={
          <SegmentedControl<Status>
            label="Status kandydatów"
            value={status}
            onValueChange={(v) => {
              setStatus(v);
              setOffset(0);
            }}
            options={[
              { value: "pending", label: "Do decyzji" },
              { value: "accepted", label: "Scalone" },
              { value: "rejected", label: "Odrzucone" },
            ]}
          />
        }
      />
      {matches.error ? <ErrorAlert error={matches.error} /> : null}
      {!matches.data ? (
        <LoadingRows rows={6} />
      ) : matches.data.items.length === 0 ? (
        <EmptyState
          title={status === "pending" ? "Nic do sprawdzenia" : "Brak pozycji"}
          description={status === "pending" ? "Wszystkie kandydatury rozstrzygnięte." : undefined}
        />
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {matches.data.items.map((m) => (
              <li key={m.id}>
                <MatchCard match={m} onDone={() => void matches.reload()} />
              </li>
            ))}
          </ul>
          <Pager count={matches.data.count} limit={LIMIT} offset={offset} onChange={setOffset} />
        </>
      )}
    </>
  );
}

function MatchCard({ match: m, onDone }: { match: Match; onDone: () => void }) {
  const [busy, setBusy] = useState<"accept" | "reject" | null>(null);

  async function decide(action: "accept" | "reject") {
    setBusy(action);
    try {
      await (action === "accept" ? api.acceptMatch(m.id) : api.rejectMatch(m.id));
      toast.success(action === "accept" ? "Scalono urządzenia." : "Oznaczono jako różne urządzenia.");
      onDone();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="bg-card ring-1 ring-border" aria-label={`Kandydat #${m.id}, odległość ${formatDistance(m.distance_m)}`}>
      <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-2">
        <span className="type-label text-subtle-foreground">#{m.id}</span>
        <Badge variant="info">{formatDistance(m.distance_m)}</Badge>
        {m.reason ? <span className="type-caption text-muted-foreground">{m.reason}</span> : null}
        <span className="type-caption ml-auto text-subtle-foreground">{formatRelative(m.created_at)}</span>
      </div>
      <div className="grid grid-cols-1 gap-px bg-border md:grid-cols-2">
        <DeviceSide label="Urządzenie A (zostaje)" device={m.device_a} />
        <DeviceSide label="Urządzenie B (zostanie dołączone)" device={m.device_b} />
      </div>
      {m.status === "pending" ? (
        <div className="flex flex-wrap justify-end gap-2 border-t border-border bg-canvas px-4 py-3">
          <Button variant="outline" size="sm" disabled={busy !== null} onClick={() => void decide("reject")}>
            <XIcon data-icon="inline-start" />
            To różne urządzenia
          </Button>
          <Button size="sm" disabled={busy !== null} onClick={() => void decide("accept")}>
            <CheckIcon data-icon="inline-start" />
            Scal w jedno
          </Button>
        </div>
      ) : (
        <div className="border-t border-border bg-canvas px-4 py-2">
          <Badge variant={m.status === "accepted" ? "positive" : "secondary"}>
            {m.status === "accepted" ? "Scalone" : "Odrzucone"}
          </Badge>
        </div>
      )}
    </article>
  );
}

function DeviceSide({ label, device: d }: { label: string; device: DeviceListItem }) {
  return (
    <div className="bg-card p-4">
      <div className="type-label text-subtle-foreground">{label}</div>
      <Link
        href={`/devices/${encodeURIComponent(d.id)}`}
        className="type-h4 mt-1 block text-link hover:text-link-hover hover:underline"
      >
        {d.name ?? d.address ?? d.id}
      </Link>
      <p className="type-caption text-muted-foreground">
        {[d.address, d.city].filter(Boolean).join(", ") || "brak adresu"}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <ReadinessBadge value={d.readiness} />
        <AccessBadge value={d.access} />
      </div>
      <p className="type-micro mt-2 text-subtle-foreground">
        <span className="font-mono">{d.id}</span> · źródła: {d.sources.join(", ") || "—"} · weryfikacja{" "}
        {formatDate(d.verified_on)} · {d.lat.toFixed(5)}, {d.lon.toFixed(5)}
      </p>
    </div>
  );
}
