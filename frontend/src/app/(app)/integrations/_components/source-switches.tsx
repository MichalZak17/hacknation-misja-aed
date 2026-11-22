"use client";

import { useId, useState } from "react";
import { toast } from "sonner";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { api, ApiError, type Integration } from "@/lib/api";

/**
 * The on/off switches an admin flips (PATCH /api/integrations/{slug}). The interval is declared on the connector class,
 * so it is part of the periodic switch's label rather than a field of its own.
 */
export function SourceSwitches({ integration, onSaved }: { integration: Integration; onSaved: () => void }) {
  const id = useId();
  const [saving, setSaving] = useState(false);

  async function patch(body: Parameters<typeof api.updateIntegration>[1], ok: string) {
    setSaving(true);
    try {
      await api.updateIntegration(integration.slug, body);
      toast.success(ok);
      onSaved();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
      <div className="flex items-center gap-2">
        <Switch
          id={`${id}-enabled`}
          checked={integration.enabled}
          disabled={saving}
          onCheckedChange={(checked) =>
            void patch({ enabled: checked }, checked ? "Źródło włączone." : "Źródło wyłączone.")
          }
        />
        <Label htmlFor={`${id}-enabled`}>Włączone</Label>
      </div>
      <div className="flex items-center gap-2">
        <Switch
          id={`${id}-periodic`}
          checked={integration.periodic_enabled}
          disabled={saving || !integration.enabled}
          onCheckedChange={(checked) =>
            void patch(
              { periodic_enabled: checked },
              checked ? "Automatyczna synchronizacja włączona." : "Automatyczna synchronizacja wyłączona.",
            )
          }
        />
        <Label htmlFor={`${id}-periodic`} title="Interwał jest ustawiony w kodzie konektora.">
          Automatycznie co {integration.sync_interval_hours} godz.
        </Label>
      </div>
    </div>
  );
}
