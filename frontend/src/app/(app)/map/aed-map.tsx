"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import type { GeoJSONSource, Map as MapLibreMap, MapLayerMouseEvent, StyleSpecification } from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import { ErrorAlert, ReadinessBadge } from "@/components/app/ui";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError, type Readiness } from "@/lib/api";
import { ACCESS_LABEL, formatNumber, label, READINESS_LABEL } from "@/lib/format";
import { OSM_STYLE, tokenColours } from "@/lib/map";

const READINESS: Readiness[] = ["ready", "attention", "expired", "unknown"];
const POINTS_URL = "/api/devices/points";

// Start both big downloads as soon as this module loads, while the session check is still running: MapLibre's code,
// and the points into the HTTP cache (ETag + no-cache), where the map's worker revalidates them with a 304 instead of
// downloading ~280 KB again. The body is read as a blob, never parsed: parsing happens in MapLibre's worker.
const maplibreModule = typeof window === "undefined" ? null : import("maplibre-gl");
if (typeof window !== "undefined") {
  void fetch(POINTS_URL)
    .then((r) => r.blob())
    .catch(() => undefined);
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** `#lat,lon,zoom` from the device page, else all of Poland. */
function initialView(): { center: [number, number]; zoom: number } {
  const m = /^#(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:,(\d+(?:\.\d+)?))?$/.exec(window.location.hash);
  if (m) return { center: [Number(m[2]), Number(m[1])], zoom: m[3] ? Number(m[3]) : 16 };
  return { center: [19.4, 52.05], zoom: 5.4 };
}

/** The base map plus the AED layers, in one style: MapLibre's worker fetches and parses the points from the URL
 * (off the main thread) as soon as the style is read, and the cluster font starts loading at the same time. */
function aedStyle(colours: ReturnType<typeof tokenColours>): StyleSpecification {
  return {
    ...OSM_STYLE,
    sources: {
      ...OSM_STYLE.sources,
      aeds: { type: "geojson", data: POINTS_URL, cluster: true, clusterMaxZoom: 13, clusterRadius: 45 },
    },
    layers: [
      ...OSM_STYLE.layers,
      {
        id: "clusters",
        type: "circle",
        source: "aeds",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": colours.cluster,
          "circle-opacity": 0.85,
          "circle-stroke-color": colours.stroke,
          "circle-stroke-width": 2,
          "circle-radius": ["step", ["get", "point_count"], 14, 25, 18, 100, 24, 500, 30],
        },
      },
      {
        id: "cluster-count",
        type: "symbol",
        source: "aeds",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Noto Sans Bold"],
          "text-size": 12,
        },
        paint: { "text-color": colours.clusterText },
      },
      {
        id: "points",
        type: "circle",
        source: "aeds",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": [
            "match",
            ["get", "readiness"],
            "ready",
            colours.ready,
            "attention",
            colours.attention,
            "expired",
            colours.expired,
            colours.unknown,
          ],
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 4, 16, 8],
          "circle-stroke-color": colours.stroke,
          "circle-stroke-width": 1.5,
        },
      },
    ],
  };
}

export function AedMap() {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const { resolvedTheme } = useTheme();
  const [error, setError] = useState<ApiError | null>(null);
  const [counts, setCounts] = useState<Record<Readiness, number> | null>(null);
  const [pointsLoaded, setPointsLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let map: MapLibreMap | null = null;

    // Same population as the map (active devices), already cached server-side: no need to count 18k points here
    api
      .stats()
      .then((s) => !cancelled && setCounts(s.by_readiness))
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e : new ApiError(0, String(e))));

    void (async () => {
      const maplibre = (await (maplibreModule ?? import("maplibre-gl"))).default;
      if (cancelled || !container.current) return;
      map = new maplibre.Map({
        container: container.current,
        ...initialView(),
        attributionControl: { compact: false },
        style: aedStyle(tokenColours()),
      });
      mapRef.current = map;
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new maplibre.GeolocateControl({ trackUserLocation: false }), "top-right");
      map.addControl(new maplibre.ScaleControl({ unit: "metric" }), "bottom-left");

      const onSourceData = (e: { sourceId?: string }) => {
        if (e.sourceId !== "aeds" || !map?.isSourceLoaded("aeds")) return;
        setPointsLoaded(true);
        map.off("sourcedata", onSourceData);
      };
      map.on("sourcedata", onSourceData);
      map.on("error", (e: { error?: { status?: number; message?: string }; sourceId?: string }) => {
        if (e.sourceId !== "aeds" || cancelled) return;
        setError(new ApiError(e.error?.status ?? 0, e.error?.message ?? "Nie udało się pobrać punktów."));
      });

      map.on("click", "clusters", async (e: MapLayerMouseEvent) => {
        const feature = e.features?.[0];
        if (!feature || !map) return;
        const source = map.getSource("aeds") as GeoJSONSource;
        const zoom = await source.getClusterExpansionZoom(feature.properties.cluster_id as number);
        map.easeTo({ center: (feature.geometry as GeoJSON.Point).coordinates as [number, number], zoom });
      });
      map.on("click", "points", (e: MapLayerMouseEvent) => {
        const feature = e.features?.[0];
        if (!feature || !map) return;
        const p = feature.properties as { id: string; readiness: string; access: string };
        const html = `
          <div style="font-family: var(--font-sans); min-width: 12rem">
            <div style="font-family: var(--font-mono); font-size: 0.75rem">${escapeHtml(p.id)}</div>
            <div style="margin-top: 0.25rem">${escapeHtml(label(READINESS_LABEL, p.readiness))} · ${escapeHtml(label(ACCESS_LABEL, p.access))}</div>
            <a href="/devices/${encodeURIComponent(p.id)}" style="display: inline-block; margin-top: 0.5rem; color: var(--link); font-weight: 600">Szczegóły urządzenia →</a>
          </div>`;
        new maplibre.Popup({ closeButton: true, maxWidth: "18rem" })
          .setLngLat((feature.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(html)
          .addTo(map);
      });
      for (const layer of ["clusters", "points"]) {
        map.on("mouseenter", layer, () => map && (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", layer, () => map && (map.getCanvas().style.cursor = ""));
      }
    })();

    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  // Day / night: re-read the tokens and repaint.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("points")) return;
    const frame = requestAnimationFrame(() => {
      const c = tokenColours();
      map.setPaintProperty("points", "circle-color", [
        "match",
        ["get", "readiness"],
        "ready",
        c.ready,
        "attention",
        c.attention,
        "expired",
        c.expired,
        c.unknown,
      ]);
      map.setPaintProperty("points", "circle-stroke-color", c.stroke);
      map.setPaintProperty("clusters", "circle-color", c.cluster);
      map.setPaintProperty("clusters", "circle-stroke-color", c.stroke);
      map.setPaintProperty("cluster-count", "text-color", c.clusterText);
    });
    return () => cancelAnimationFrame(frame);
  }, [resolvedTheme]);

  return (
    <div className="flex flex-col gap-3">
      {error ? <ErrorAlert error={error} title="Nie udało się wczytać punktów" /> : null}
      <div className="flex flex-wrap items-center gap-3" aria-live="polite">
        {counts
          ? READINESS.map((r) => (
              <span key={r} className="inline-flex items-center gap-1.5">
                <ReadinessBadge value={r} />
                <span className="type-caption tabular-nums text-muted-foreground">{formatNumber(counts[r])}</span>
              </span>
            ))
          : null}
        {!pointsLoaded && !error ? (
          <span className="type-caption inline-flex items-center gap-2 text-muted-foreground">
            <Spinner /> Wczytywanie punktów…
          </span>
        ) : null}
      </div>
      <div
        ref={container}
        className="h-[min(72svh,48rem)] w-full bg-muted ring-1 ring-border"
        role="region"
        aria-label="Mapa defibrylatorów AED"
      />
      <p className="type-micro text-subtle-foreground">
        Kolor punktu = gotowość urządzenia. Liczba w kółku = liczba urządzeń w grupie; kliknij, by przybliżyć. Lista
        urządzeń z filtrami jest w zakładce Urządzenia.
      </p>
    </div>
  );
}
