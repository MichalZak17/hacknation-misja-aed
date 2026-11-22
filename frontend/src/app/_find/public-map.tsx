"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import type { GeoJSONSource, Map as MapLibreMap, MapMouseEvent, Marker, StyleSpecification } from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import { Spinner } from "@/components/ui/spinner";
import type { NearbyAed } from "@/lib/api";
import { OSM_STYLE, tokenColours } from "@/lib/map";

const POINTS_URL = "/api/devices/points";

// Start MapLibre's code and the points download (into the HTTP cache, ETag + no-cache) as soon as the page loads.
const maplibreModule = typeof window === "undefined" ? null : import("maplibre-gl");
if (typeof window !== "undefined") {
  void fetch(POINTS_URL)
    .then((r) => r.blob())
    .catch(() => undefined);
}

type MapLib = NonNullable<Awaited<typeof maplibreModule>>["default"];

export type Origin = { lat: number; lon: number; label: string };

function style(c: ReturnType<typeof tokenColours>): StyleSpecification {
  return {
    ...OSM_STYLE,
    sources: {
      ...OSM_STYLE.sources,
      aeds: { type: "geojson", data: POINTS_URL, cluster: true, clusterMaxZoom: 12, clusterRadius: 45 },
    },
    layers: [
      ...OSM_STYLE.layers,
      {
        id: "clusters",
        type: "circle",
        source: "aeds",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": c.cluster,
          "circle-opacity": 0.85,
          "circle-stroke-color": c.stroke,
          "circle-stroke-width": 2,
          "circle-radius": ["step", ["get", "point_count"], 14, 25, 18, 100, 24, 500, 30],
        },
      },
      {
        id: "cluster-count",
        type: "symbol",
        source: "aeds",
        filter: ["has", "point_count"],
        layout: { "text-field": ["get", "point_count_abbreviated"], "text-font": ["Noto Sans Bold"], "text-size": 12 },
        paint: { "text-color": c.clusterText },
      },
      {
        id: "points",
        type: "circle",
        source: "aeds",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": c.highlight,
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 4, 16, 7],
          "circle-stroke-color": c.stroke,
          "circle-stroke-width": 1.5,
        },
      },
    ],
  };
}

/** A numbered square for a result (the number matches the list), or the ringed dot for the searched place. */
function markerElement(kind: "result" | "origin", text = "") {
  const el = document.createElement("div");
  el.setAttribute("aria-hidden", "true");
  if (kind === "origin") {
    el.className = "size-5 rounded-full border-[3px] border-white bg-info shadow-[0_0_0_2px_var(--info)]";
  } else {
    el.className =
      "flex size-8 cursor-pointer items-center justify-center border-2 border-white bg-foreground font-sans text-sm font-bold text-background shadow-md";
    el.textContent = text;
  }
  return el;
}

export function PublicMap({
  origin,
  results,
  selected,
  onPick,
  onSelect,
}: {
  origin: Origin | null;
  results: NearbyAed[];
  selected: string | null;
  onPick: (lat: number, lon: number) => void;
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const libRef = useRef<MapLib | null>(null);
  const markers = useRef<Marker[]>([]);
  const onPickRef = useRef(onPick);
  const onSelectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [pointsLoaded, setPointsLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    onPickRef.current = onPick;
    onSelectRef.current = onSelect;
  });

  useEffect(() => {
    let cancelled = false;
    let map: MapLibreMap | null = null;
    void (async () => {
      const maplibre = (await (maplibreModule ?? import("maplibre-gl"))).default;
      if (cancelled || !container.current) return;
      libRef.current = maplibre;
      map = new maplibre.Map({
        container: container.current,
        center: [19.4, 52.05],
        zoom: 5.2,
        attributionControl: { compact: true },
        style: style(tokenColours()),
        cooperativeGestures: false,
      });
      mapRef.current = map;
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new maplibre.ScaleControl({ unit: "metric" }), "bottom-left");
      map.on("load", () => !cancelled && setReady(true));
      const onSourceData = (e: { sourceId?: string }) => {
        if (e.sourceId !== "aeds" || !map?.isSourceLoaded("aeds")) return;
        setPointsLoaded(true);
        map.off("sourcedata", onSourceData);
      };
      map.on("sourcedata", onSourceData);
      // Only a points download that never succeeded counts (an aborted request during a style change does not)
      map.on("error", (e: { sourceId?: string; error?: { name?: string } }) => {
        if (cancelled || e.sourceId !== "aeds" || e.error?.name === "AbortError") return;
        if (!map?.isSourceLoaded("aeds")) setFailed(true);
      });
      map.on("click", async (e: MapMouseEvent) => {
        if (!map) return;
        const cluster = map.queryRenderedFeatures(e.point, { layers: ["clusters"] })[0];
        if (cluster) {
          const source = map.getSource("aeds") as GeoJSONSource;
          const zoom = await source.getClusterExpansionZoom(cluster.properties.cluster_id as number);
          map.easeTo({ center: (cluster.geometry as GeoJSON.Point).coordinates as [number, number], zoom });
          return;
        }
        onPickRef.current(e.lngLat.lat, e.lngLat.lng);
      });
      map.on("mouseenter", "clusters", () => map && (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "clusters", () => map && (map.getCanvas().style.cursor = ""));
      map.getCanvas().style.cursor = "crosshair";
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  // The searched place and the numbered results; fit them all in view.
  useEffect(() => {
    const map = mapRef.current;
    const maplibre = libRef.current;
    if (!map || !maplibre || !ready) return;
    for (const m of markers.current) m.remove();
    markers.current = [];
    if (!origin) return;
    markers.current.push(new maplibre.Marker({ element: markerElement("origin") }).setLngLat([origin.lon, origin.lat]).addTo(map));
    const bounds = new maplibre.LngLatBounds([origin.lon, origin.lat], [origin.lon, origin.lat]);
    results.forEach((r, i) => {
      const el = markerElement("result", String(i + 1));
      el.addEventListener("click", (event) => {
        event.stopPropagation();
        onSelectRef.current(r.aed.id);
      });
      markers.current.push(new maplibre.Marker({ element: el }).setLngLat([r.aed.lon, r.aed.lat]).addTo(map));
      bounds.extend([r.aed.lon, r.aed.lat]);
    });
    map.fitBounds(bounds, { padding: 56, maxZoom: 17, duration: 600 });
  }, [origin, results, ready]);

  // A result chosen in the list: fly to it and mark its number.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    results.forEach((r, i) => {
      const el = markers.current[i + 1]?.getElement();
      if (!el) return;
      const on = r.aed.id === selected;
      el.classList.toggle("bg-hn-crimson", on);
      el.classList.toggle("text-white", on);
      el.classList.toggle("bg-foreground", !on);
      el.classList.toggle("text-background", !on);
      el.style.zIndex = on ? "2" : "";
      if (on) map.flyTo({ center: [r.aed.lon, r.aed.lat], zoom: Math.max(map.getZoom(), 17), duration: 600 });
    });
  }, [selected, results, ready]);

  // Day / night: re-read the tokens and repaint.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const frame = requestAnimationFrame(() => {
      const c = tokenColours();
      map.setPaintProperty("points", "circle-color", c.highlight);
      map.setPaintProperty("points", "circle-stroke-color", c.stroke);
      map.setPaintProperty("clusters", "circle-color", c.cluster);
      map.setPaintProperty("clusters", "circle-stroke-color", c.stroke);
      map.setPaintProperty("cluster-count", "text-color", c.clusterText);
    });
    return () => cancelAnimationFrame(frame);
  }, [resolvedTheme, ready]);

  return (
    <div className="relative h-full min-h-[22rem] w-full">
      <div
        ref={container}
        className="h-full w-full bg-muted"
        role="region"
        aria-label="Mapa defibrylatorów AED. Kliknij lub dotknij, aby wyszukać AED w pobliżu tego miejsca. Ta sama lista najbliższych AED jest dostępna obok mapy."
      />
      {!pointsLoaded ? (
        <div
          className="type-caption absolute top-2 left-2 inline-flex items-center gap-2 bg-background/95 px-2 py-1 text-muted-foreground shadow-sm"
          role="status"
        >
          {failed ? (
            "Nie udało się wczytać punktów na mapę. Wyszukiwanie najbliższych AED nadal działa."
          ) : (
            <>
              <Spinner /> Wczytywanie punktów…
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
