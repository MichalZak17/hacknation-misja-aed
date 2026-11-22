"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import type { Map as MapLibreMap, MapLayerMouseEvent } from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import { request, type DeviceListItem } from "@/lib/api";
import { OSM_STYLE, tokenColours } from "@/lib/map";

type Nearby = DeviceListItem & { distance_m: number };

/**
 * The device on a street-level map, highlighted, with the nearest other AEDs as small dots (click one to open it).
 * Scroll zoom needs Ctrl/⌘ so the map doesn't hijack scrolling the page.
 */
export function DeviceMap({ id, lat, lon, label }: { id: string; lat: number; lon: number; label: string }) {
  const container = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    let cancelled = false;
    let map: MapLibreMap | null = null;

    void (async () => {
      const maplibre = (await import("maplibre-gl")).default;
      if (cancelled || !container.current) return;
      const colours = tokenColours();
      map = new maplibre.Map({
        container: container.current,
        center: [lon, lat],
        zoom: 17,
        style: OSM_STYLE,
        attributionControl: { compact: true },
        cooperativeGestures: true,
      });
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");

      const nearby = await request<Nearby[]>(`/api/devices/nearest?lat=${lat}&lon=${lon}&limit=25`).catch(() => []);
      if (cancelled) return;
      const others: GeoJSON.FeatureCollection<GeoJSON.Point, { id: string }> = {
        type: "FeatureCollection",
        features: nearby
          .filter((d) => d.id !== id)
          .map((d) => ({ type: "Feature", geometry: { type: "Point", coordinates: [d.lon, d.lat] }, properties: { id: d.id } })),
      };

      const addLayers = () => {
        if (!map) return;
        map.addSource("others", { type: "geojson", data: others });
        map.addLayer({
          id: "others",
          type: "circle",
          source: "others",
          paint: {
            "circle-color": colours.unknown,
            "circle-radius": 5,
            "circle-stroke-color": colours.stroke,
            "circle-stroke-width": 1.5,
          },
        });
        map.addSource("device", {
          type: "geojson",
          data: { type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties: {} },
        });
        map.addLayer({
          id: "device-halo",
          type: "circle",
          source: "device",
          paint: { "circle-color": colours.highlight, "circle-opacity": 0.18, "circle-radius": 22 },
        });
        map.addLayer({
          id: "device",
          type: "circle",
          source: "device",
          paint: {
            "circle-color": colours.highlight,
            "circle-radius": 9,
            "circle-stroke-color": colours.stroke,
            "circle-stroke-width": 3,
          },
        });
        map.on("click", "others", (e: MapLayerMouseEvent) => {
          const other = e.features?.[0]?.properties?.id as string | undefined;
          if (other) router.push(`/devices/${encodeURIComponent(other)}`);
        });
        map.on("mouseenter", "others", () => map && (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "others", () => map && (map.getCanvas().style.cursor = ""));
      };
      if (map.isStyleLoaded()) addLayers();
      else map.once("load", addLayers);
    })();

    return () => {
      cancelled = true;
      map?.remove();
    };
    // Rebuilt on a theme switch so the point colours follow the tokens
  }, [id, lat, lon, router, resolvedTheme]);

  return (
    <div
      ref={container}
      className="h-[min(60svh,28rem)] w-full bg-muted ring-1 ring-border"
      role="region"
      aria-label={`Mapa: ${label}, z najbliższymi innymi AED`}
    />
  );
}
