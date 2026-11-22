/**
 * Copies text to the clipboard. `navigator.clipboard` exists only in a secure context (https or localhost), so over
 * plain http on another host (e.g. a LAN or Tailscale address) it falls back to a hidden textarea and
 * `execCommand("copy")`, which still works inside a click handler. Returns whether the copy succeeded.
 */
export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Permission denied or document not focused: try the fallback below.
    }
  }
  return copyWithTextarea(text);
}

function copyWithTextarea(text: string): boolean {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "0";
  textarea.style.opacity = "0";
  // Inside an open modal the focus trap would pull focus back from an element outside it, so stay in the dialog.
  const host = document.activeElement?.closest('[role="dialog"]') ?? document.body;
  const previous = document.activeElement as HTMLElement | null;
  host.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  textarea.remove();
  previous?.focus();
  return ok;
}
