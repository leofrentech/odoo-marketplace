/**
 * Small DOM helpers shared by the personalization interactions.
 */

/**
 * Create an element with optional classes, attributes and text.
 * Text is always set through textContent (never parsed as HTML).
 */
export function el(tag, { classes = "", attrs = {}, text = null } = {}) {
    const node = document.createElement(tag);
    if (classes) {
        node.className = classes;
    }
    for (const [name, value] of Object.entries(attrs)) {
        if (value !== false && value !== null && value !== undefined) {
            node.setAttribute(name, value === true ? "" : value);
        }
    }
    if (text !== null) {
        node.textContent = text;
    }
    return node;
}

/**
 * Odoo icon (Material Symbols, the icon font of Odoo 20).
 *
 * @param {string} name icon name, e.g. "delete"
 * @param {string} [classes] extra classes, e.g. "oi-filled oi-2x"
 */
export function icon(name, classes = "") {
    return el("i", {
        classes: `oi ${classes}`.trim(),
        attrs: { "data-icon": name, role: "img", "aria-hidden": "true" },
    });
}

/** Format an amount with the website currency information. */
export function formatPrice(amount, currency) {
    const value = Number(amount || 0).toFixed(currency?.digits ?? 2);
    const symbol = currency?.symbol || "";
    return currency?.position === "before" ? `${symbol} ${value}` : `${value} ${symbol}`;
}

export function showModal(modalEl) {
    window.Modal.getOrCreateInstance(modalEl).show();
}

export function hideModal(modalEl) {
    window.Modal.getOrCreateInstance(modalEl).hide();
}

/** Trigger the download of a data URL. */
export function downloadDataUrl(dataUrl, filename) {
    const link = el("a", { attrs: { href: dataUrl, download: filename } });
    document.body.appendChild(link);
    link.click();
    link.remove();
}

export function slugify(text) {
    return (text || "design").toString().toLowerCase().replace(/[^\w]+/g, "-").replace(/^-|-$/g, "");
}

/** Read the image natural size of a data URL / URL. */
export function imageSize(src) {
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
        img.onerror = () => resolve({ width: 0, height: 0 });
        img.src = src;
    });
}

export function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
    });
}

/** sessionStorage access that never throws (private mode, blocked storage). */
export const safeSession = {
    get(key) {
        try {
            return JSON.parse(window.sessionStorage.getItem(key) || "null");
        } catch {
            return null;
        }
    },
    set(key, value) {
        try {
            window.sessionStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch {
            return false;
        }
    },
    remove(key) {
        try {
            window.sessionStorage.removeItem(key);
        } catch {
            // ignore
        }
    },
};
