/**
 * Load the fonts offered in the editor (Google Fonts or uploaded files) so the
 * canvas renders with the right font. Device fonts need no loading.
 */
const loaded = new Set();

function addStylesheet(url) {
    if (document.querySelector(`link[data-lf-font="${CSS.escape(url)}"]`)) {
        return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = url;
    link.dataset.lfFont = url;
    document.head.appendChild(link);
}

async function loadFont(font) {
    if (loaded.has(font.family)) {
        return;
    }
    if (font.source === "google" && font.url) {
        addStylesheet(font.url);
    } else if (font.source === "upload" && font.url) {
        try {
            const face = new FontFace(font.family, `url("${font.url}")`);
            document.fonts.add(await face.load());
        } catch {
            return;
        }
    }
    try {
        // Wait (max 3s) until the font can be used by the canvas.
        await Promise.race([
            Promise.all([
                document.fonts.load(`40px "${font.family}"`),
                document.fonts.load(`bold 40px "${font.family}"`),
            ]),
            new Promise((resolve) => setTimeout(resolve, 3000)),
        ]);
    } catch {
        // The browser falls back on a default font.
    }
    loaded.add(font.family);
}

export function loadFonts(fonts) {
    return Promise.all((fonts || []).map(loadFont));
}

/** Families used by a canvas JSON, to load before rendering it. */
export function fontsOfDesign(json, fonts) {
    const families = new Set(
        (json?.objects || []).filter((obj) => obj.fontFamily).map((obj) => obj.fontFamily)
    );
    return (fonts || []).filter((font) => families.has(font.family));
}
