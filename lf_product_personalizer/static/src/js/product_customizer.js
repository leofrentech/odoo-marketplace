import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { CanvasManager } from "./core/canvas_manager";
import { HistoryManager } from "./core/history_manager";
import { StateManager } from "./core/state_manager";
import { TextHandler } from "./handlers/text_handler";
import { ImageHandler } from "./handlers/image_handler";
import { ShapeHandler } from "./handlers/shape_handler";
import { LayerHandler } from "./handlers/layer_handler";
import { MenuController } from "./ui/menu_controller";
import { ControlsUpdater } from "./ui/controls_updater";
import { loadFabric } from "./utils/fabric_loader";
import { loadFonts } from "./utils/font_loader";
import { ObjectUtils, isImage, isText, isUserObject } from "./utils/object_utils";
import { PreviewGenerator } from "./utils/preview_generator";
import {
    downloadDataUrl,
    el,
    formatPrice,
    hideModal,
    safeSession,
    showModal,
    slugify,
} from "./utils/dom_utils";

/**
 * Full-page design editor (/shop/personalize/<product>).
 */
export class ProductPersonalizer extends Interaction {
    static selector = ".o_lf_personalizer";

    dynamicContent = {
        _document: { "t-on-keydown.noUpdate": this.onKeydown },
        _window: { "t-on-beforeunload.noUpdate": this.onBeforeUnload },
        ".o_lf_tools": { "t-on-click.noUpdate": this.onToolClick },
        ".o_lf_areas": { "t-on-click.noUpdate": this.onAreaClick },
        ".o_lf_undo": { "t-on-click.noUpdate": () => this.history.undo() },
        ".o_lf_redo": { "t-on-click.noUpdate": () => this.history.redo() },
        ".o_lf_add_to_cart": { "t-on-click.noUpdate": this.locked(this.onAddToCart, true) },
        ".o_lf_preview": { "t-on-click.noUpdate": this.locked(this.onPreview) },
        ".o_lf_download": { "t-on-click.noUpdate": this.locked(this.onDownload) },
        ".o_lf_save_design": { "t-on-click.noUpdate": this.onSaveDesign },
        ".o_lf_share": { "t-on-click.noUpdate": this.onShare },
        ".o_lf_save_preset": { "t-on-click.noUpdate": this.onSavePreset },
        ".o_lf_clear": { "t-on-click.noUpdate": this.onClear },
        ".o_lf_name_form": { "t-on-submit.prevent.noUpdate": this.onNameSubmit },
        ".o_lf_quantity": { "t-on-change.noUpdate": this.onQuantityChange },
        // Text
        ".o_lf_add_text": { "t-on-click.noUpdate": this.onAddText },
        ".o_lf_text_input": { "t-on-keydown.noUpdate": this.onTextInputKeydown },
        ".o_lf_text_edit": { "t-on-input.noUpdate": this.onTextEdit },
        ".o_lf_font": { "t-on-change.noUpdate": this.onFontChange },
        ".o_lf_font_size": { "t-on-change.noUpdate": this.onFontSizeChange },
        ".o_lf_style": { "t-on-click.noUpdate.withTarget": this.onTextStyle },
        ".o_lf_align": { "t-on-click.noUpdate.withTarget": this.onTextAlign },
        ".o_lf_panels": {
            "t-on-click.noUpdate": this.onPanelClick,
            "t-on-input.noUpdate": this.onPanelInput,
        },
        // Images
        ".o_lf_upload": { "t-on-change.noUpdate": this.onUpload },
        ".o_lf_dropzone": {
            "t-on-dragover.prevent.noUpdate": (ev) => ev.currentTarget.classList.add("o_lf_dragover"),
            "t-on-dragleave.noUpdate": (ev) => ev.currentTarget.classList.remove("o_lf_dragover"),
            "t-on-drop.prevent.noUpdate": this.onDrop,
        },
        ".o_lf_image_op": { "t-on-click.noUpdate.withTarget": this.onImageOperation },
        ".o_lf_image_filter": { "t-on-input.noUpdate.withTarget": this.onImageFilter },
        ".o_lf_clipart_search": { "t-on-input.noUpdate": this.onClipartSearch },
        ".o_lf_stroke_width": { "t-on-input.noUpdate": this.onStrokeWidth },
    };

    setup() {
        const ds = this.el.dataset;
        this.productId = parseInt(ds.productId);
        this.variantId = parseInt(ds.variantId) || null;
        this.lineId = parseInt(ds.lineId) || null;
        this.designId = parseInt(ds.designId) || null;
        this.accessToken = ds.accessToken || null;
        this.revision = ds.revision === "1";
        this.state = new StateManager();
        this.dirty = false;
        this.submitting = false;
        this.savedDesignId = this.designId;
        this.shareUrl = null;
        this.pendingNameAction = null;
        this.storageKey = `lf_personalizer_draft_${this.productId}`;
    }

    async willStart() {
        const [data] = await Promise.all([this.fetchData(this.variantId), loadFabric()]);
        this.state.setData(data);
        this.state.loadDesigns(data.designs);
        await loadFonts(this.state.settings.fonts);
    }

    start() {
        this.menu = new MenuController(this.el);
        this.controls = new ControlsUpdater(this.el);
        this.canvasManager = new CanvasManager(this.el.querySelector(".o_lf_canvas_wrapper"));
        this.canvasManager.initialize();
        this.registerCleanup(() => {
            clearTimeout(this.changeTimer);
            clearTimeout(this.draftTimer);
            this.canvasManager.dispose();
        });
        this.history = new HistoryManager(this.canvasManager, () => this.onCanvasChanged(false));
        this.textHandler = new TextHandler(this);
        this.imageHandler = new ImageHandler(this);
        this.shapeHandler = new ShapeHandler(this);
        this.layerHandler = new LayerHandler(
            this,
            this.el.querySelector(".o_lf_layers"),
            this.el.querySelector(".o_lf_layers_empty")
        );
        this.bindCanvasEvents();
        this.renderSidebar();
        this.restoreDraft();
        this.waitFor(this.loadArea(this.state.activeAreaKey));
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------

    fetchData(variantId) {
        return rpc("/shop/personalize/data", {
            product_id: this.productId,
            variant_id: variantId,
            line_id: this.lineId,
            design_id: this.designId,
            access_token: this.accessToken,
            revision: this.revision,
        });
    }

    get canvas() {
        return this.canvasManager.canvas;
    }

    get activeObject() {
        const obj = this.canvas.getActiveObject();
        return isUserObject(obj) ? obj : null;
    }

    notify(message, type = "info") {
        this.services.notification.add(message, { type });
    }

    renderSidebar() {
        const { settings } = this.state;
        const data = this.state.data;
        this.menu.renderFonts(settings.fonts);
        this.menu.renderPalettes(settings.palette, !this.isCustomPalette());
        this.menu.renderShapes();
        this.menu.renderCliparts(data.cliparts);
        this.menu.renderPresets(data.presets);
        this.menu.renderVariants(data.variants, data.active_variant_id);
        this.menu.applyToolSettings(settings, data);
        this.renderAreas();
        const maxLength = settings.max_text_length || "";
        for (const input of this.el.querySelectorAll(".o_lf_text_input, .o_lf_text_edit")) {
            if (maxLength) {
                input.maxLength = maxLength;
            } else {
                input.removeAttribute("maxlength");
            }
        }
        for (const node of this.el.querySelectorAll(".o_lf_manager_only")) {
            node.classList.toggle("d-none", !data.can_manage_presets);
        }
    }

    isCustomPalette() {
        return Boolean(this.state.data.settings.palette_is_custom);
    }

    renderAreas() {
        const customized = new Set(this.state.customizedAreas().map((area) => area.key));
        this.menu.renderAreas(this.state.areas, this.state.activeAreaKey, this.state.data.pricing, customized);
        this.renderPrice();
    }

    renderPrice() {
        const { pricing } = this.state.data;
        const customized = this.state.customizedAreas();
        let amount = customized.length ? pricing.fee || 0 : 0;
        for (const area of customized) {
            amount += pricing.areas?.[area.key] || 0;
        }
        const info = this.el.querySelector(".o_lf_price_info");
        info.textContent = amount
            ? _t("Personalization: +%s per item", formatPrice(amount, pricing.currency))
            : "";
    }

    // ------------------------------------------------------------------
    // Areas
    // ------------------------------------------------------------------

    saveActiveArea() {
        if (this.state.activeAreaKey && this.canvas) {
            this.imageHandler.cancelCrop();
            this.state.setDesign(this.state.activeAreaKey, ObjectUtils.serialize(this.canvas));
        }
    }

    async loadArea(key) {
        const area = this.state.areaByKey(key);
        if (!area) {
            return;
        }
        this.state.activeAreaKey = key;
        this.history.restoring = true;
        try {
            this.canvasManager.clearObjects();
            this.canvasManager.setZone(PreviewGenerator.zoneOf(area));
            await this.canvasManager.setBackground(area.image_url);
            await ObjectUtils.restore(this.canvas, this.state.getDesign(key));
            this.canvasManager.keepZoneOnTop();
            this.canvas.requestRenderAll();
        } finally {
            this.history.restoring = false;
        }
        this.el.querySelector(".o_lf_loading")?.remove();
        this.el.querySelector(".o_lf_hint").classList.toggle("d-none", !this.canvasManager.zone);
        this.history.reset();
        this.renderAreas();
        this.onSelectionChanged();
        this.controls.updateHistory(false, false);
    }

    onAreaClick(ev) {
        const button = ev.target.closest(".o_lf_area");
        if (!button || button.dataset.area === this.state.activeAreaKey) {
            return;
        }
        this.saveActiveArea();
        this.waitFor(this.loadArea(button.dataset.area));
    }

    async switchVariant(variantId) {
        if (this.lineId) {
            this.notify(
                this.revision
                    ? _t("The variant of an order cannot be changed here.")
                    : _t("Remove this item from your cart to choose another variant."),
                "warning"
            );
            return;
        }
        this.saveActiveArea();
        const data = await this.waitFor(this.fetchData(variantId));
        this.variantId = variantId;
        // Keep the designs made so far for areas shared by both variants.
        data.designs = {};
        this.state.setData(data);
        this.renderSidebar();
        await this.loadArea(this.state.activeAreaKey);
    }

    // ------------------------------------------------------------------
    // Canvas events
    // ------------------------------------------------------------------

    bindCanvasEvents() {
        const canvas = this.canvas;
        const onSelection = () => this.onSelectionChanged();
        canvas.on("selection:created", onSelection);
        canvas.on("selection:updated", onSelection);
        canvas.on("selection:cleared", onSelection);
        canvas.on("object:added", (ev) => {
            if (isUserObject(ev.target)) {
                this.canvasManager.keepZoneOnTop();
                this.onCanvasChanged();
            }
        });
        canvas.on("object:removed", (ev) => {
            if (isUserObject(ev.target)) {
                this.onCanvasChanged();
            }
        });
        canvas.on("object:modified", (ev) => {
            if (isUserObject(ev.target)) {
                this.textHandler.bakeScale(ev.target);
                this.canvasManager.clampToZone(ev.target);
                this.onCanvasChanged();
            }
        });
        const clamp = (ev) => this.canvasManager.clampToZone(ev.target);
        canvas.on("object:moving", clamp);
        canvas.on("object:scaling", clamp);
        canvas.on("object:rotating", clamp);
        canvas.on("text:changed", (ev) => {
            const max = this.state.settings.max_text_length;
            if (max && ev.target.text.length > max) {
                ev.target.set("text", ev.target.text.slice(0, max));
                ev.target.exitEditing?.();
                this.notify(_t("Texts are limited to %s characters.", max), "warning");
            }
            this.onSelectionChanged();
        });
    }

    /** Called after any change of the objects of the current area. */
    onCanvasChanged(saveHistory = true) {
        if (this.history.restoring) {
            return;
        }
        if (saveHistory) {
            this.history.save();
        }
        this.dirty = true;
        this.state.setDesign(this.state.activeAreaKey, ObjectUtils.serialize(this.canvas));
        this.controls.updateHistory(this.history.canUndo(), this.history.canRedo());
        this.layerHandler.render();
        this.renderAreas();
        this.saveDraft();
    }

    onSelectionChanged() {
        const obj = this.activeObject;
        this.controls.update(obj, isImage(obj) ? this.imageHandler.adjustmentValues(obj) : null);
        this.layerHandler.render();
        if (!obj || this.imageHandler.isCropping) {
            return;
        }
        const panel = isText(obj) ? "text" : isImage(obj) ? (obj.lfClipart ? "clipart" : "image") : "shape";
        const tool = this.el.querySelector(`.o_lf_tool[data-panel="${panel}"]`);
        if (tool && !tool.classList.contains("d-none") && this.menu.activePanel !== "layers") {
            this.menu.showPanel(panel);
        }
    }

    selectObject(obj) {
        this.canvas.setActiveObject(obj);
        this.canvas.requestRenderAll();
        this.onSelectionChanged();
    }

    onKeydown(ev) {
        if (ev.target.closest("input, textarea, select, [contenteditable]") || this.activeObject?.isEditing) {
            return;
        }
        const mod = ev.ctrlKey || ev.metaKey;
        if (mod && ev.key.toLowerCase() === "z") {
            ev.preventDefault();
            this.waitFor(ev.shiftKey ? this.history.redo() : this.history.undo());
        } else if (mod && ev.key.toLowerCase() === "y") {
            ev.preventDefault();
            this.waitFor(this.history.redo());
        } else if ((ev.key === "Delete" || ev.key === "Backspace") && this.activeObject) {
            ev.preventDefault();
            this.canvas.remove(this.activeObject);
            this.canvas.discardActiveObject();
            this.canvas.requestRenderAll();
        }
    }

    onBeforeUnload(ev) {
        if (this.dirty && !this.submitting) {
            ev.preventDefault();
            ev.returnValue = "";
        }
    }

    onToolClick(ev) {
        const tool = ev.target.closest(".o_lf_tool");
        if (tool) {
            this.menu.showPanel(tool.dataset.panel);
            if (tool.dataset.panel === "layers") {
                this.layerHandler.render();
            }
        }
    }

    // ------------------------------------------------------------------
    // Panels (delegated clicks on generated tiles and swatches)
    // ------------------------------------------------------------------

    onPanelClick(ev) {
        const swatch = ev.target.closest(".o_lf_swatch[data-color]");
        if (swatch) {
            this.applyColor(swatch.closest(".o_lf_palette").dataset.target, swatch.dataset.color);
            return;
        }
        const shape = ev.target.closest(".o_lf_shape");
        if (shape) {
            const palette = this.state.settings.palette;
            this.shapeHandler.add(shape.dataset.shape, { fill: palette[2] || palette[0], stroke: palette[0] });
            return;
        }
        const clipart = ev.target.closest(".o_lf_clipart");
        if (clipart) {
            this.waitFor(
                this.imageHandler.addFromUrl(clipart.dataset.url, clipart.dataset.name, { lfClipart: true })
            );
            return;
        }
        const preset = ev.target.closest(".o_lf_preset");
        if (preset) {
            this.applyPreset(parseInt(preset.dataset.preset));
            return;
        }
        const variant = ev.target.closest(".o_lf_variant");
        if (variant) {
            this.switchVariant(parseInt(variant.dataset.variant));
        }
    }

    onPanelInput(ev) {
        if (ev.target.classList.contains("o_lf_color_input")) {
            this.applyColor(ev.target.closest(".o_lf_palette").dataset.target, ev.target.value);
        }
    }

    applyColor(target, color) {
        const obj = this.activeObject;
        if (!obj) {
            return;
        }
        if (target === "text") {
            this.textHandler.update(obj, { fill: color });
        } else if (target === "fill") {
            this.shapeHandler.update(obj, { fill: color });
        } else if (target === "stroke") {
            const width = obj.strokeWidth || 3;
            this.shapeHandler.update(obj, { stroke: color, strokeWidth: width });
        }
        this.onSelectionChanged();
    }

    applyPreset(presetId) {
        const preset = this.state.data.presets.find((p) => p.id === presetId);
        if (!preset) {
            return;
        }
        const apply = () => {
            this.state.loadDesigns(preset.designs);
            this.waitFor(this.loadArea(this.state.activeAreaKey)).then(() => this.onCanvasChanged());
        };
        if (this.state.customizedAreas().length) {
            this.services.dialog.add(ConfirmationDialog, {
                title: _t("Use this design?"),
                body: _t("Your current design will be replaced."),
                confirmLabel: _t("Replace"),
                confirm: apply,
                cancel: () => {},
            });
        } else {
            apply();
        }
    }

    // ------------------------------------------------------------------
    // Text
    // ------------------------------------------------------------------

    defaultTextStyle() {
        const { fonts, palette } = this.state.settings;
        return { fontFamily: fonts[0]?.family || "Arial", fill: palette[0] || "#000000" };
    }

    onAddText() {
        const input = this.el.querySelector(".o_lf_text_input");
        const text = input.value.trim();
        if (!text) {
            input.focus();
            this.notify(_t("Type your text first."), "warning");
            return;
        }
        this.textHandler.add(text, this.defaultTextStyle());
        input.value = "";
    }

    onTextInputKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.onAddText();
        }
    }

    onTextEdit(ev) {
        const obj = this.activeObject;
        if (isText(obj)) {
            obj.set({ text: ev.target.value, lfLabel: ev.target.value });
            this.canvasManager.clampToZone(obj);
            this.canvas.requestRenderAll();
            this.onCanvasChanged();
        }
    }

    onFontChange(ev) {
        this.textHandler.update(this.activeObject, { fontFamily: ev.target.value });
    }

    onFontSizeChange(ev) {
        const size = Math.max(8, Math.min(300, parseInt(ev.target.value) || 40));
        this.textHandler.update(this.activeObject, { fontSize: size });
    }

    onTextStyle(ev, button) {
        this.textHandler.toggleStyle(this.activeObject, button.dataset.style);
        this.onSelectionChanged();
    }

    onTextAlign(ev, button) {
        this.textHandler.update(this.activeObject, { textAlign: button.dataset.align });
        this.onSelectionChanged();
    }

    // ------------------------------------------------------------------
    // Images & shapes
    // ------------------------------------------------------------------

    async onUpload(ev) {
        const files = [...ev.target.files];
        ev.target.value = "";
        await this.waitFor(this.imageHandler.addFiles(files));
    }

    async onDrop(ev) {
        ev.currentTarget.classList.remove("o_lf_dragover");
        await this.waitFor(this.imageHandler.addFiles([...(ev.dataTransfer?.files || [])]));
    }

    onImageOperation(ev, button) {
        const op = button.dataset.op;
        const label = this.el.querySelector(".o_lf_crop_label");
        if (op === "crop") {
            if (this.imageHandler.isCropping) {
                this.imageHandler.applyCrop();
                label.textContent = _t("Crop");
            } else if (this.imageHandler.startCrop(this.activeObject)) {
                label.textContent = _t("Apply crop");
            }
            return;
        }
        this.imageHandler.operate(this.activeObject, op);
        this.onSelectionChanged();
    }

    onImageFilter(ev, input) {
        this.imageHandler.setAdjustment(this.activeObject, input.dataset.op, input.value);
        this.scheduleChange();
    }

    onStrokeWidth(ev) {
        const obj = this.activeObject;
        if (obj && !isText(obj) && !isImage(obj)) {
            obj.set({ strokeWidth: parseInt(ev.target.value) || 0 });
            this.canvas.requestRenderAll();
            this.scheduleChange();
        }
    }

    scheduleChange() {
        clearTimeout(this.changeTimer);
        this.changeTimer = setTimeout(() => this.onCanvasChanged(), 300);
    }

    onClipartSearch(ev) {
        this.menu.renderCliparts(this.state.data.cliparts, ev.target.value);
    }

    onQuantityChange(ev) {
        ev.target.value = Math.max(1, parseInt(ev.target.value) || 1);
    }

    onClear() {
        if (!this.canvas.getObjects().some(isUserObject)) {
            return;
        }
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Clear this side?"),
            body: _t("Everything you added on this side will be removed."),
            confirmLabel: _t("Clear"),
            confirm: () => {
                this.canvasManager.clearObjects();
                this.onCanvasChanged();
            },
            cancel: () => {},
        });
    }

    // ------------------------------------------------------------------
    // Exports
    // ------------------------------------------------------------------

    /** Payload for the cart: json + preview + print files, for every area. */
    async buildCartPayload() {
        this.saveActiveArea();
        const scale = this.state.settings.print_scale || 4;
        const designs = {};
        for (const area of this.state.areas) {
            const json = this.state.getDesign(area.key);
            const customized = !ObjectUtils.isEmpty(json);
            designs[area.key] = {
                json,
                preview: customized ? await PreviewGenerator.preview(area, json) : null,
                print: customized ? await PreviewGenerator.print(area, json, scale) : null,
                svg: customized ? await PreviewGenerator.svg(area, json) : null,
            };
        }
        return designs;
    }

    validate() {
        this.saveActiveArea();
        if (!this.state.customizedAreas().length) {
            this.notify(_t("Add some text or an image to your design first."), "warning");
            return false;
        }
        const missing = this.state.areas.filter(
            (area) => area.is_required && ObjectUtils.isEmpty(this.state.getDesign(area.key))
        );
        if (missing.length) {
            this.notify(
                _t("Please personalize: %s", missing.map((area) => area.name).join(", ")),
                "warning"
            );
            this.waitFor(this.loadArea(missing[0].key));
            return false;
        }
        return true;
    }

    async onAddToCart() {
        if (!this.validate()) {
            return;
        }
        const quantity = parseInt(this.el.querySelector(".o_lf_quantity")?.value) || 1;
        const designs = await this.waitFor(this.buildCartPayload());
        if (this.revision) {
            const result = await this.waitFor(
                rpc("/shop/personalize/revise", {
                    line_id: this.lineId,
                    access_token: this.accessToken,
                    designs,
                })
            );
            if (result.error) {
                this.notify(result.error, "danger");
                return;
            }
            this.submitting = true;
            redirect(result.redirect_url);
            return;
        }
        const result = await this.waitFor(
            this.lineId
                ? rpc("/shop/personalize/update", { line_id: this.lineId, quantity, designs })
                : rpc("/shop/personalize/add", {
                      product_id: this.productId,
                      variant_id: this.state.data.active_variant_id,
                      quantity,
                      designs,
                  })
        );
        if (result.error) {
            this.notify(result.error, "danger");
            return;
        }
        this.submitting = true;
        safeSession.remove(this.storageKey);
        redirect("/shop/cart");
    }

    async onPreview() {
        this.saveActiveArea();
        const grid = this.el.querySelector(".o_lf_preview_grid");
        const cards = [];
        for (const area of this.state.areas) {
            const url = await this.waitFor(PreviewGenerator.preview(area, this.state.getDesign(area.key)));
            const col = el("div", { classes: "col-12 col-md-6" });
            const figure = el("figure", { classes: "figure w-100 text-center" });
            figure.append(
                el("img", { classes: "figure-img img-fluid rounded border", attrs: { src: url, alt: area.name } }),
                el("figcaption", { classes: "figure-caption", text: area.name })
            );
            col.appendChild(figure);
            cards.push(col);
        }
        grid.replaceChildren(...cards);
        showModal(this.el.querySelector(".o_lf_preview_modal"));
    }

    async onDownload() {
        this.saveActiveArea();
        const areas = this.state.customizedAreas();
        if (!areas.length) {
            this.notify(_t("Add some text or an image to your design first."), "warning");
            return;
        }
        for (const area of areas) {
            const url = await this.waitFor(PreviewGenerator.preview(area, this.state.getDesign(area.key)));
            downloadDataUrl(url, `${slugify(this.state.data.product_name)}-${slugify(area.name)}.jpg`);
        }
    }

    async firstPreview() {
        const area = this.state.customizedAreas()[0];
        return area ? PreviewGenerator.preview(area, this.state.getDesign(area.key)) : null;
    }

    // ------------------------------------------------------------------
    // Save to account / share / template
    // ------------------------------------------------------------------

    askName(title, defaultValue, action) {
        this.pendingNameAction = action;
        const modal = this.el.querySelector(".o_lf_name_modal");
        modal.querySelector(".o_lf_name_title").textContent = title;
        const input = modal.querySelector(".o_lf_name_input");
        input.value = defaultValue || "";
        showModal(modal);
        modal.addEventListener("shown.bs.modal", () => input.select(), { once: true });
    }

    async onNameSubmit() {
        const modal = this.el.querySelector(".o_lf_name_modal");
        const name = modal.querySelector(".o_lf_name_input").value.trim();
        if (!name) {
            return;
        }
        hideModal(modal);
        const action = this.pendingNameAction;
        this.pendingNameAction = null;
        await action?.(name);
    }

    onSaveDesign() {
        this.saveActiveArea();
        if (!this.state.customizedAreas().length) {
            this.notify(_t("Add some text or an image to your design first."), "warning");
            return;
        }
        if (this.state.data.is_public_user) {
            this.saveDraft(true);
            this.submitting = true;
            redirect(this.state.data.login_url);
            return;
        }
        this.askName(_t("Name your design"), this.state.data.product_name, async (name) => {
            const result = await this.waitFor(
                rpc("/shop/personalize/save_design", {
                    product_id: this.productId,
                    variant_id: this.state.data.active_variant_id,
                    design_id: this.savedDesignId,
                    name,
                    designs: this.state.exportDesigns(),
                    preview: await this.firstPreview(),
                })
            );
            if (result.error) {
                this.notify(result.error, "danger");
                return;
            }
            this.savedDesignId = result.design_id;
            this.shareUrl = result.share_url;
            this.dirty = false;
            safeSession.remove(this.storageKey);
            this.el.querySelector(".o_lf_share").classList.remove("d-none");
            this.notify(_t("Design saved in your account (My Designs)."), "success");
        });
    }

    async onShare() {
        if (!this.shareUrl) {
            return;
        }
        try {
            await browser.navigator.clipboard.writeText(this.shareUrl);
            this.notify(_t("Link copied: anyone with it can open this design."), "success");
        } catch {
            this.notify(this.shareUrl, "info");
        }
    }

    onSavePreset() {
        this.saveActiveArea();
        if (!this.state.customizedAreas().length) {
            this.notify(_t("Add some text or an image to your design first."), "warning");
            return;
        }
        this.askName(_t("Name this template"), "", async (name) => {
            const result = await this.waitFor(
                rpc("/shop/personalize/save_preset", {
                    product_id: this.productId,
                    variant_id: this.state.data.active_variant_id,
                    name,
                    designs: this.state.exportDesigns(),
                    preview: await this.firstPreview(),
                })
            );
            if (result.error) {
                this.notify(result.error, "danger");
                return;
            }
            this.notify(_t("Template saved: customers can now start from it."), "success");
        });
    }

    // ------------------------------------------------------------------
    // Draft kept in the browser (e.g. while the visitor signs in)
    // ------------------------------------------------------------------

    saveDraft(force = false) {
        if (this.lineId || this.designId) {
            return;
        }
        clearTimeout(this.draftTimer);
        const write = () =>
            safeSession.set(this.storageKey, {
                variant_id: this.state.data.active_variant_id,
                designs: this.state.exportDesigns(),
            });
        if (force) {
            write();
        } else {
            this.draftTimer = setTimeout(write, 1000);
        }
    }

    restoreDraft() {
        if (this.lineId || this.designId) {
            return;
        }
        const draft = safeSession.get(this.storageKey);
        if (draft?.designs && Object.keys(draft.designs).length) {
            if (draft.variant_id === this.state.data.active_variant_id) {
                this.state.loadDesigns(draft.designs);
                this.notify(_t("We restored the design you were working on."), "info");
            }
        }
    }
}

registry.category("public.interactions").add("lf_product_personalizer.editor", ProductPersonalizer);
