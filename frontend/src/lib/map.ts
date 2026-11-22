import type { StyleSpecification } from "maplibre-gl";

/** CSS custom properties → colour strings MapLibre understands (it can't parse oklch or var()). */
export function tokenColours() {
  const style = getComputedStyle(document.documentElement);
  const ctx = document.createElement("canvas").getContext("2d");
  const read = (name: string) => {
    const raw = style.getPropertyValue(name).trim();
    if (!ctx || !raw) return raw || "gray";
    ctx.fillStyle = "#000";
    ctx.fillStyle = raw;
    return String(ctx.fillStyle);
  };
  return {
    ready: read("--positive"),
    attention: read("--caution"),
    expired: read("--destructive"),
    unknown: read("--muted-foreground"),
    cluster: read("--primary"),
    clusterText: read("--primary-foreground"),
    stroke: read("--background"),
    highlight: read("--color-hn-crimson"),
  };
}

/** OpenStreetMap raster tiles with attribution: the base map of every map in the app. */
export const OSM_STYLE: StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};
