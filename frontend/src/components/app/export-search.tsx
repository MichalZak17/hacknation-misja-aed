"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeftIcon,
  CopyIcon,
  DownloadIcon,
  ExternalLinkIcon,
  FileIcon,
  FileJsonIcon,
  FileSpreadsheetIcon,
  FileTextIcon,
  GlobeIcon,
  MapIcon,
  SearchIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "@/components/ui/command";
import { Kbd } from "@/components/ui/kbd";
import { api, type ExportResource } from "@/lib/api";
import { copyText } from "@/lib/clipboard";
import { formatBytes } from "@/lib/format";
import { useApi } from "@/lib/use-api";

type Entry = {
  path: string;
  label: string;
  hint: string;
  group: "Zasoby" | "Dokumenty uzupełniające" | "Metadane i harvester";
  keywords: string[];
  icon: React.ComponentType<{ className?: string }>;
};

/** Words people type for a format that are not in its title (Polish and English). */
const ALIASES: Record<string, string[]> = {
  csv: ["arkusz", "excel", "tabela", "rekordy"],
  geojson: ["mapa", "gis", "qgis", "geometria", "punkty"],
  json: ["api", "rekordy"],
  jsonld: ["linked data", "schema.org", "rdf", "5 gwiazdek"],
  xlsx: ["słownik", "schemat", "excel", "zakres danych", "wzorcowy"],
  txt: ["słownik", "schemat", "dokument", "opis pól"],
};

const ICONS: Record<string, Entry["icon"]> = {
  csv: FileSpreadsheetIcon,
  xlsx: FileSpreadsheetIcon,
  geojson: MapIcon,
  json: FileJsonIcon,
  jsonld: FileJsonIcon,
  txt: FileTextIcon,
};

/** Endpoints that are not listed as resources in dataset.json but belong to the publication. */
const METADATA: Entry[] = [
  {
    path: "/api/export/dataset.json",
    label: "dataset.json",
    hint: "Metadane zbioru w kształcie dane.gov.pl",
    group: "Metadane i harvester",
    keywords: ["metadane", "dataset", "opis zbioru", "licencja", "kategorie"],
    icon: FileJsonIcon,
  },
  {
    path: "/api/export/harvester.xml",
    label: "harvester.xml",
    hint: "Źródło danych XML do zarejestrowania na dane.gov.pl",
    group: "Metadane i harvester",
    keywords: ["harvester", "xml", "dane.gov.pl", "import", "źródło danych"],
    icon: GlobeIcon,
  },
  {
    path: "/api/export/harvester.md5",
    label: "harvester.md5",
    hint: "Suma kontrolna pliku harvester.xml",
    group: "Metadane i harvester",
    keywords: ["md5", "suma kontrolna", "checksum", "harvester"],
    icon: FileIcon,
  },
];

function toEntry(r: ExportResource, group: Entry["group"]): Entry {
  const format = r.media_type === "api" ? "api" : r.format.toLowerCase();
  return {
    path: r.path,
    label: `${format.toUpperCase()} · ${r.title}`,
    hint: `${r.media_type === "api" ? "API na żywo" : formatBytes(r.file_size)} · ${r.content_type}`,
    group,
    keywords: [format, r.title, r.description, r.content_type, r.path, ...(ALIASES[format] ?? [])],
    icon: ICONS[format] ?? FileIcon,
  };
}

function download(path: string) {
  const a = document.createElement("a");
  a.href = path;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/**
 * Navbar search over the published exports (Ctrl/⌘ K): pick a file, then download it, copy its stable link or open
 * it. The list comes from dataset.json, so it is the same set of resources the portal imports.
 */
export function ExportSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<Entry | null>(null);
  // Fetched on first open only, and kept afterwards.
  const [wanted, setWanted] = useState(false);
  const dataset = useApi(wanted ? "dataset" : null, api.dataset);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setWanted(true);
        setOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const entries = useMemo(() => {
    const d = dataset.data;
    const files = d
      ? [...d.resources.map((r) => toEntry(r, "Zasoby")), ...d.supplements.map((r) => toEntry(r, "Dokumenty uzupełniające"))]
      : [];
    return [...files, ...METADATA];
  }, [dataset.data]);

  const groups = useMemo(() => {
    const by = new Map<Entry["group"], Entry[]>();
    for (const e of entries) by.set(e.group, [...(by.get(e.group) ?? []), e]);
    return [...by.entries()];
  }, [entries]);

  function setDialog(next: boolean) {
    setOpen(next);
    if (next) setWanted(true);
    else {
      setPicked(null);
      setQuery("");
    }
  }

  function back() {
    setPicked(null);
    setQuery("");
  }

  async function copy(path: string) {
    const link = new URL(path, window.location.origin).toString();
    if (await copyText(link)) toast.success("Skopiowano link do schowka.");
    else toast.error(`Nie udało się skopiować linku: ${link}`);
  }

  function act(fn: () => void) {
    fn();
    setDialog(false);
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setDialog(true)}
        aria-label="Szukaj eksportów (Ctrl+K)"
        aria-haspopup="dialog"
        className="gap-2 text-muted-foreground"
      >
        <SearchIcon data-icon="inline-start" aria-hidden />
        <span className="hidden md:inline">Szukaj eksportów…</span>
        <Kbd className="hidden md:inline-flex" aria-hidden>
          Ctrl K
        </Kbd>
      </Button>
      <CommandDialog
        open={open}
        onOpenChange={setDialog}
        title="Szukaj eksportów"
        description="Wyszukaj plik eksportu, a potem pobierz go, skopiuj link albo otwórz."
      >
        <Command loop>
          <CommandInput
            value={query}
            onValueChange={setQuery}
            placeholder={picked ? `${picked.label}: wybierz akcję…` : "Format, nazwa lub słowo, np. mapa, słownik, harvester…"}
            onKeyDown={(e) => {
              if (picked && e.key === "Backspace" && !query) {
                e.preventDefault();
                back();
              }
            }}
          />
          <CommandList>
            <CommandEmpty>
              {dataset.loading && !picked ? "Wczytuję listę eksportów…" : "Nic nie pasuje do zapytania."}
            </CommandEmpty>
            {picked ? (
              <CommandGroup heading={picked.label}>
                <CommandItem value="pobierz download" onSelect={() => act(() => download(picked.path))}>
                  <DownloadIcon aria-hidden />
                  Pobierz plik
                </CommandItem>
                <CommandItem value="kopiuj link copy" onSelect={() => act(() => void copy(picked.path))}>
                  <CopyIcon aria-hidden />
                  Kopiuj stały link
                </CommandItem>
                <CommandItem
                  value="otwórz w nowej karcie open"
                  onSelect={() => act(() => window.open(picked.path, "_blank", "noopener"))}
                >
                  <ExternalLinkIcon aria-hidden />
                  Otwórz w nowej karcie
                </CommandItem>
                <CommandItem value="wróć back" onSelect={back}>
                  <ArrowLeftIcon aria-hidden />
                  Wróć do listy
                  <CommandShortcut>⌫</CommandShortcut>
                </CommandItem>
              </CommandGroup>
            ) : (
              <>
                {groups.map(([heading, items]) => (
                  <CommandGroup key={heading} heading={heading}>
                    {items.map((e) => (
                      <CommandItem
                        key={e.path}
                        value={`${e.label} ${e.path}`}
                        keywords={e.keywords}
                        onSelect={() => {
                          setPicked(e);
                          setQuery("");
                        }}
                      >
                        <e.icon aria-hidden />
                        <span className="flex min-w-0 flex-col">
                          <span className="truncate">{e.label}</span>
                          <span className="truncate text-xs text-muted-foreground">{e.hint}</span>
                        </span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                ))}
                <CommandGroup heading="Strony">
                  <CommandItem
                    value="strona otwartych danych eksport"
                    keywords={["dane do pobrania", "publikacja", "dane.gov.pl", "słownik danych"]}
                    onSelect={() => act(() => router.push("/export"))}
                  >
                    <GlobeIcon aria-hidden />
                    Strona „Dane do pobrania”
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
