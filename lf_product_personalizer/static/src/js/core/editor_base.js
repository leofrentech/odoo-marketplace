/**
 * Minimal base for the editor classes, mounted by a public widget.
 *
 * It offers the same small API the editor code relies on (an event map,
 * cleanups, locked handlers), so the editor logic is identical on every
 * supported Odoo version.
 *
 * ``dynamicContent`` maps a selector to events:
 *   { ".o_lf_undo": { "t-on-click.prevent.withTarget": handler } }
 * Special selectors: _root, _document, _window. Modifiers: prevent, stop,
 * withTarget (the handler receives the element as second argument).
 */
export class EditorBase {
    dynamicContent = {};

    /**
     * @param {HTMLElement} el root element
     * @param {Object} services e.g. { notification, dialog }
     */
    constructor(el, services) {
        this.el = el;
        this.services = services;
        this._cleanups = [];
        this.isDestroyed = false;
    }

    setup() {}

    async willStart() {}

    start() {}

    /** Kept for API parity: callers await the promise directly. */
    waitFor(promise) {
        return promise;
    }

    registerCleanup(fn) {
        this._cleanups.push(fn);
    }

    /**
     * Ignore calls while ``fn`` is running; optionally disable the clicked
     * button meanwhile.
     */
    locked(fn, disableTarget = false) {
        let running = false;
        return async (ev, ...args) => {
            if (running) {
                return;
            }
            running = true;
            const button = disableTarget ? ev?.currentTarget : null;
            if (button) {
                button.disabled = true;
            }
            try {
                return await fn.call(this, ev, ...args);
            } finally {
                running = false;
                if (button) {
                    button.disabled = false;
                }
            }
        };
    }

    _nodesFor(selector) {
        if (selector === "_root") {
            return [this.el];
        }
        if (selector === "_document") {
            return [this.el.ownerDocument];
        }
        if (selector === "_window") {
            return [window];
        }
        return [...this.el.querySelectorAll(selector)];
    }

    bindDynamicContent() {
        for (const [selector, events] of Object.entries(this.dynamicContent)) {
            for (const [key, handler] of Object.entries(events)) {
                const [eventName, ...modifiers] = key.replace(/^t-on-/, "").split(".");
                const listener = (ev) => {
                    if (modifiers.includes("prevent")) {
                        ev.preventDefault();
                    }
                    if (modifiers.includes("stop")) {
                        ev.stopPropagation();
                    }
                    return modifiers.includes("withTarget")
                        ? handler.call(this, ev, ev.currentTarget)
                        : handler.call(this, ev);
                };
                for (const node of this._nodesFor(selector)) {
                    node.addEventListener(eventName, listener);
                    this._cleanups.push(() => node.removeEventListener(eventName, listener));
                }
            }
        }
    }

    destroy() {
        this.isDestroyed = true;
        for (const cleanup of this._cleanups.reverse()) {
            cleanup();
        }
        this._cleanups = [];
    }
}

/**
 * Build a public widget definition mounting ``EditorClass`` on ``selector``.
 *
 * @param {Object} publicWidget the public widget module
 * @param {typeof EditorBase} EditorClass
 */
export function editorWidget(publicWidget, EditorClass) {
    return publicWidget.Widget.extend({
        selector: EditorClass.selector,

        init() {
            this._super(...arguments);
            this.notification = this.bindService("notification");
            this.dialog = this.bindService("dialog");
        },

        async willStart() {
            await this._super(...arguments);
            this.editor = new EditorClass(this.el, {
                notification: this.notification,
                dialog: this.dialog,
            });
            this.editor.setup();
            await this.editor.willStart();
        },

        async start() {
            await this._super(...arguments);
            this.editor.start();
            this.editor.bindDynamicContent();
        },

        destroy() {
            this.editor?.destroy();
            this._super(...arguments);
        },
    });
}
