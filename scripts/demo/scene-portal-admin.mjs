// Scene 4, the dane.gov.pl administrator adds our harvester XML as a data source of the test institution: the portal
// validates the XML against its own schema, saves the source and imports the dataset.
//   MCOD_SESSION=<local_sessionid>   an admin session of the portal (minted in the mcod container, see README.md)
//   SAVE=1                           really save (otherwise stops before "Zapisz")
import { run, sleep } from "./lib.mjs";

const ADMIN = "https://admin.dane.hackstorm.eu";
const SID = process.env.MCOD_SESSION;
const SAVE = !!process.env.SAVE;
const NAME = process.env.DS_NAME ?? "Misja AED — defibrylatory AED w Polsce";
const XML = process.env.DS_XML ?? "https://misja-aed.hackstorm.eu/api/export/harvester.xml";
const INSTITUTION = "Misja AED - instytucja testowa";

await run(
  "portal-admin",
  async (s, page) => {
    await s.goto(ADMIN + "/harvester/datasource/");
    await sleep(800);
    await s.cap("Portal dane.gov.pl: panel administracyjny", "admin.dane.hackstorm.eu · źródła danych (harwester)");
    await sleep(2200);
    await s.click(page.locator("a.addlink, a[href$='/harvester/datasource/add/']").first());
    await page.waitForURL(/datasource\/add/);
    await page.waitForLoadState("networkidle");
    await s.park();
    await sleep(700);
    await s.cap("Nowe źródło: import automatyczny z pliku XML", "raz dodane, portal pobiera je codziennie sam");
    await s.type(page.locator("#id_name"), NAME, 40);
    const editor = page.frameLocator("iframe.cke_wysiwyg_frame").locator("body");
    await s.click(page.locator("iframe.cke_wysiwyg_frame"));
    await editor.pressSequentially("Ogólnopolski rejestr defibrylatorów AED z Misji AED.", { delay: 25 });
    await sleep(400);

    await s.hover(page.locator("#id_source_type"));
    await page.selectOption("#id_source_type", "xml");
    await sleep(900);
    await s.type(page.locator("#id_xml_url"), XML, 30);
    await sleep(500);

    await s.cap("Portal sprawdza nasz plik swoim schematem XSD", "ten sam walidator, którego używa dane.gov.pl");
    await s.click(page.locator(".validate-xml-btn"));
    await page.getByText(/XML Validation successful|Walidacja XML zakończona sukcesem|sukces/i).first().waitFor({ timeout: 90000 });
    await sleep(2200);
    await s.snap("validated");
    await s.click(page.locator("#myModal .modal-footer button"));
    await sleep(700);

    // institution: Django admin autocomplete (select2)
    await s.click(page.locator(".field-organization .select2-selection, .field-organization .select2-choice").first());
    await page.keyboard.type("Misja AED", { delay: 60 });
    await page.locator(".select2-results li", { hasText: INSTITUTION }).first().waitFor({ timeout: 15000 });
    await sleep(500);
    await s.click(page.locator(".select2-results li", { hasText: INSTITUTION }).first());
    await sleep(500);

    await s.hover(page.locator("#id_frequency_in_days"));
    await page.selectOption("#id_frequency_in_days", "1");
    await sleep(500);
    await s.hover(page.locator("#id_status"));
    await page.selectOption("#id_status", "active");
    await sleep(500);
    await s.type(page.locator("#id_emails"), "kontakt@misja-aed.hackstorm.eu", 30);
    await sleep(600);
    await s.cap("Instytucja, częstotliwość: codziennie, status: aktywne");
    await sleep(1500);
    await s.snap("filled");
    if (!SAVE) return;

    await s.click(page.locator("[name=_save]").first());
    await page.waitForLoadState("networkidle");
    await s.park();
    await sleep(800);
    await s.cap("Zapisane: portal od razu uruchamia import", "„Import data task was launched!”");
    await sleep(3000);

    // the new source: wait for the import to finish, then show it
    await s.click(page.getByRole("link", { name: NAME }).first());
    await page.waitForLoadState("networkidle");
    await s.park();
    await sleep(800);
    const importsTab = () => page.locator('a[href="#imports"]').first();
    // the import result is a green (ok) or red span in the Imports tab once the import has an end time
    const result = page.locator(".suit-tab-imports span[style*='color']").first();
    await s.click(importsTab());
    await sleep(1200);
    s.cutStart();
    for (let i = 0; i < 60 && !(await result.count()); i++) {
      await sleep(3000);
      await page.reload({ waitUntil: "networkidle" });
      await importsTab().click();
      await s.park();
    }
    await sleep(500);
    s.cutEnd();
    await s.cap("Import zakończony: zbiór i jego zasoby są już na portalu");
    await s.hover(result, 800).catch(() => {});
    await sleep(3000);
    const datasets = page.locator('a[href="#datasets"]').first();
    if (await datasets.count()) {
      await s.click(datasets);
      await sleep(3200);
    }
  },
  { cookies: SID ? [{ name: "local_sessionid", value: SID, domain: ".dane.hackstorm.eu", path: "/", secure: true }] : [] },
);
