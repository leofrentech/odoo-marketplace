/**
 * Load the fonts offered in the editor (Google Fonts or uploaded files) so the
 * canvas measures and draws text with the right font. Device fonts need no
 * loading.
 */
const loaded = new Map();

/** Add a stylesheet once and resolve when the browser has parsed it. */
function addStylesheet(url) {
    const existing = document.querySelector(`link[data-lf-font="${CSS.escape(url)}"]`);
    if (existing) {
        return existing.lfLoaded;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = url;
    link.dataset.lfFont = url;
    link.lfLoaded = new Promise((resolve) => {
        link.onload = resolve;
        link.onerror = resolve;
    });
    document.head.appendChild(link);
    return link.lfLoaded;
}

function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise((resolve) => setTimeout(resolve, ms))]);
}

async function loadFont(font) {
    if (font.source === "google" && font.url) {
        // The @font-face rules must exist before asking the browser to load
        // the font, otherwise document.fonts.load() resolves with nothing.
        await withTimeout(addStylesheet(font.url), 5000);
    } else if (font.source === "upload" && font.url) {
        try {
            const face = new FontFace(font.family, `url("${font.url}")`);
            document.fonts.add(await face.load());
        } catch {
            return;
        }
    }
    try {
        await withTimeout(
            Promise.all([
                document.fonts.load(`40px "${font.family}"`),
                document.fonts.load(`bold 40px "${font.family}"`),
            ]),
            5000
        );
    } catch {
        // The browser falls back on a default font.
    }
    // Fabric caches character widths per font: drop measures taken earlier.
    window.fabric?.util?.clearFabricFontCache?.(font.family);
}

export function loadFonts(fonts) {
    return Promise.all(
        (fonts || []).map((font) => {
            if (!loaded.has(font.family)) {
                loaded.set(font.family, loadFont(font));
            }
            return loaded.get(font.family);
        })
    );
}
