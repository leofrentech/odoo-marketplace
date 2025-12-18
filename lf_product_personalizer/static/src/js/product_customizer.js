/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

// Core Modules
import { CanvasManager } from './core/canvas_manager';
import { HistoryManager } from './core/history_manager';
import { StateManager } from './core/state_manager';

// Handlers
import { TextHandler } from './handlers/text_handler';
import { ImageHandler } from './handlers/image_handler';
import { ShapeHandler } from './handlers/shape_handler';
import { LayerHandler } from './handlers/layer_handler';

// UI Controllers
import { MenuController } from './ui/menu_controller';
import { ControlsUpdater } from './ui/controls_updater';

// Utilities
import { ObjectUtils } from './utils/object_utils';
import { PreviewGenerator } from './utils/preview_generator';


/**
 * Main Editor Controller for Product Personalization Page
 */
publicWidget.registry.ProductPersonalizationEditor = publicWidget.Widget.extend({
    selector: '.o_product_personalize_page',

    events: {
        // Text
        'click #add_text_button': '_onClickAddText',
        'change #text_font_family': '_onChangeTextProperty',
        'change #text_font_size': '_onChangeTextProperty',
        'change #text_color': '_onChangeTextProperty',
        'click #text_bold': '_onClickTextStyle',
        'click #text_italic': '_onClickTextStyle',
        'click #text_underline': '_onClickTextStyle',

        // Images
        'click #add_image_button': '_onClickAddImage',

        // Shapes
        'click .shape-item': '_onShapeSelect',
        'change #shape_fill_color': '_onChangeShapeProperty',
        'change #shape_stroke_color': '_onChangeShapeProperty',
        'change #shape_stroke_width': '_onChangeShapeProperty',

        // Preset colors
        'click .preset-color': '_onClickPresetColor',

        // Navigation
        'click .menu-item': '_onMenuItemClick',

        // Design Type Switching
        'change #design_type_selector': '_onDesignTypeChange',

        // Variant switching
        'click .variant-item': '_onVariantChange',

        // Quantity
        'change #product_qty': '_onChangeQty',

        // Undo / Redo
        'click #undo_button': '_onClickUndo',
        'click #redo_button': '_onClickRedo',

        // Preview & Download
        'click #preview_designs_button': '_onClickPreviewDesigns',
        'click #download_designs_button': '_onClickDownloadDesigns',
        'click .download-format-btn': '_onClickDownloadFormat',

        // Add to cart
        'click #add_to_cart_personalized': '_onClickAddToCartPersonalized',
    },

    /**
     * Entry point for personalization page
     */
    start() {
        const self = this;

        self.canvasManager = new CanvasManager();
        self.stateManager = new StateManager();
        self.editMode = false;
        self.editLineId = null;
        self.editVariantId = null;

        return this._super.apply(this, arguments).then(() => {
            // Load initial config
            self.editMode = self.$('#edit_mode').val() === 'true';
            self.editLineId = parseInt(self.$('#line_id').val()) || null;
            self.editVariantId = parseInt(self.$('#edit_variant_id').val()) || null;

            // Load product data & initialize
            return self._loadProductData()
                .then(() => self._initializeCanvas())
                .then(() => self.editMode ? self._loadEditModeData() : null)
                .then(() => {
                    self._initializeHandlers();
                    self._initializeUI();
                    self._setupEventListeners();
                    self._setupKeyboardShortcuts();
                    self._initDesignTypeSelector();
                });
        });
    },

    /** Setup canvas, history, and layers */
    _initializeCanvas() {
        this.canvasManager.initialize();
        const canvas = this.canvasManager.getCanvas();

        this.historyManager = new HistoryManager(canvas, this.canvasManager.zoneRect);
        this.layerHandler = new LayerHandler(canvas, this.canvasManager.zoneRect);
    },

    /** Initialize text, image, and shape handlers */
    _initializeHandlers() {
        const canvas = this.canvasManager.getCanvas();

        this.textHandler = new TextHandler(canvas, this.canvasManager.zone);
        this.imageHandler = new ImageHandler(canvas, this.canvasManager.zone);
        this.shapeHandler = new ShapeHandler(canvas, this.canvasManager.zone);
    },

    /** Create UI controllers */
    _initializeUI() {
        this.menuController = new MenuController(this.$el);
        this.controlsUpdater = new ControlsUpdater(this.$el);
    },

    /**
     * Load product & design configuration from backend
     */
    _loadProductData() {
        const productId = parseInt(this.$('#product_id').val());
        const variantId = this.editMode ? this.editVariantId : null;

        return rpc('/shop/product_personalization_data', {
            product_id: productId,
            variant_id: variantId,
        })
            .then(data => {
                if (data.error) throw new Error(data.error);
                this.stateManager.setProductData(data);
                return data;
            })
            .catch(error => {
                console.error("Load product data failed:", error);
                alert("Failed to load product data.");
                throw error;
            });
    },

    /**
     * Load saved JSON when editing existing personalization
     */
    _loadEditModeData() {
        return rpc('/shop/cart/get_line_personalization', {
            line_id: this.editLineId,
        })
            .then(result => {
                if (!result.success) return;

                // Prepare JSON for each design type
                if (result.designs) {
                    Object.entries(result.designs).forEach(([type, design]) => {
                        try {
                            if (typeof design.personalized_json === 'string') {
                                design.json = JSON.parse(design.personalized_json);
                            } else if (typeof design.personalized_json === 'object') {
                                design.json = design.personalized_json;
                            } else if (typeof design.json === 'string') {
                                design.json = JSON.parse(design.json);
                            } else {
                                design.json = { objects: [] };
                            }
                        } catch {
                            design.json = { objects: [] };
                        }

                        // Map background image url
                        if (design.product_image_url) {
                            design.backgroundImageUrl = design.product_image_url;
                        }
                    });

                    this.stateManager.setDesignData(result.designs);
                }
            })
            .catch(err => {
                console.error("Failed loading edit mode JSON:", err);
            });
    },

    /** Bind Fabric.js canvas events */
    _setupEventListeners() {
        const canvas = this.canvasManager.getCanvas();
        const self = this;

        canvas.on('selection:created', () => self._onSelection());
        canvas.on('selection:updated', () => self._onSelection());
        canvas.on('selection:cleared', () => self._onSelectionCleared());

        canvas.on('object:added', e => self._onObjectAdded(e));
        canvas.on('object:modified', e => self._onObjectModified(e));
        canvas.on('object:removed', () => self._onObjectRemoved());

        canvas.on('object:moving', e => self._onObjectMoving(e));
        canvas.on('object:scaling', e => self._onObjectScaling(e));
        canvas.on('object:rotating', e => self._onObjectRotating(e));

        canvas.on('after:render', () => self.canvasManager.ensureZoneOnTop());
    },

    /**
     * Update UI when an object is selected
     */
    _onSelection() {
        const obj = this.canvasManager.getCanvas().getActiveObject();

        this.controlsUpdater.updateControls(obj, this.canvasManager.zoneRect);
        this.layerHandler.renderLayersList(
            this.$('#layers_list'),
            obj => this._selectObject(obj)
        );

        const isText = obj.type === 'i-text' || obj.type === 'text';
        const isImage = obj.type === 'image';
        const isShape = !isText && !isImage;

        this.menuController.autoSwitchPanel(isText, isImage, isShape);
    },

    /** Clear control visibility */
    _onSelectionCleared() {
        this.controlsUpdater.hideControls();
        this.layerHandler.renderLayersList(
            this.$('#layers_list'),
            obj => this._selectObject(obj)
        );
    },

    /**
     * After object added to canvas
     */
    _onObjectAdded(e) {
        const obj = e.target;
        if (!obj || obj.isZoneRect) return;

        if (!this.historyManager.isUndoRedoAction) {
            this.historyManager.saveState();
        }

        this._positionNewObject(obj);
        this.layerHandler.assignLayerId(obj);
        this.layerHandler.renderLayersList(this.$('#layers_list'), o => this._selectObject(o));
    },

    /** Position new object and scale inside zone */
    _positionNewObject(obj) {
        if (this.historyManager.isUndoRedoAction) return;

        setTimeout(() => {
            if (this.canvasManager.zone && !obj.isZoneRect) {
                ObjectUtils.positionInZoneCenter(obj, this.canvasManager.zone);
                ObjectUtils.scaleToFitZone(obj, this.canvasManager.zone);
            }

            if (this.canvasManager.zoneRect) {
                this.canvasManager.getCanvas().bringToFront(this.canvasManager.zoneRect);
            }

            this.canvasManager.getCanvas().renderAll();
        }, 10);
    },

    /** After scaling */
    _onObjectScaling(e) {
        const obj = e.target;
        if (!obj || obj.isZoneRect) return;

        this.canvasManager.clampObjectToZone(obj);

        if (obj.type === 'i-text' || obj.type === 'text') {
            this.textHandler.updateFontSizeOnScale(obj);
            this.controlsUpdater.updateControls(obj, this.canvasManager.zoneRect);
        }
    },

    /** After modify */
    _onObjectModified(e) {
        const obj = e.target;
        if (!obj || obj.isZoneRect) return;

        if (!this.historyManager.isUndoRedoAction) {
            this.historyManager.saveState();
        }

        this.canvasManager.clampObjectToZone(obj);

        this.layerHandler.renderLayersList(
            this.$('#layers_list'),
            o => this._selectObject(o)
        );
    },

    /** After removal */
    _onObjectRemoved() {
        if (!this.historyManager.isUndoRedoAction) {
            this.historyManager.saveState();
        }
        this.layerHandler.renderLayersList(
            this.$('#layers_list'),
            obj => this._selectObject(obj)
        );
    },

    /** Clamp object during movement */
    _onObjectMoving(e) {
        const obj = e.target;
        if (!obj || obj.isZoneRect) return;
        this.canvasManager.clampObjectToZone(obj);
    },

    /** Clamp while rotating */
    _onObjectRotating(e) {
        const obj = e.target;
        if (!obj || obj.isZoneRect) return;
        this.canvasManager.clampObjectToZone(obj);
    },

    /** Add Delete, Ctrl+Z, Ctrl+Y support */
    _setupKeyboardShortcuts() {
        const self = this;

        $(document).on('keydown', function (e) {
            if ($(e.target).is('input, textarea')) return;

            const obj = self.canvasManager.getCanvas().getActiveObject();

            if ((e.key === 'Delete' || e.key === 'Backspace') && obj) {
                e.preventDefault();
                self.canvasManager.getCanvas().remove(obj);
                self.canvasManager.getCanvas().renderAll();
            }

            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'z') {
                    e.preventDefault();
                    e.shiftKey ? self._onClickRedo() : self._onClickUndo();
                } else if (e.key === 'y') {
                    e.preventDefault();
                    self._onClickRedo();
                }
            }
        });
    },

    /** Add new text */
    _onClickAddText() {
        const text = this.$('#personalization_text').val().trim();
        const obj = this.textHandler.addText(text);
        if (obj) {
            this.canvasManager.clampObjectToZone(obj);
            this.$('#personalization_text').val('');
        }
    },

    /** Toggle bold/italic/underline */
    _onClickTextStyle(ev) {
        const styleMap = {
            'text_bold': 'bold',
            'text_italic': 'italic',
            'text_underline': 'underline',
        };

        const obj = this.canvasManager.getCanvas().getActiveObject();
        const style = styleMap[ev.target.id];

        if (style) {
            this.textHandler.toggleTextStyle(obj, style);
            $(ev.currentTarget).toggleClass('active');
        }
    },

    /** Update font/fill properties */
    _onChangeTextProperty(ev) {
        const obj = this.canvasManager.getCanvas().getActiveObject();
        const map = {
            'text_font_family': ['fontFamily', ev.target.value],
            'text_font_size': ['fontSize', parseInt(ev.target.value)],
            'text_color': ['fill', ev.target.value],
        };

        const prop = map[ev.target.id];
        if (prop) this.textHandler.updateTextProperty(obj, prop[0], prop[1]);
    },

    /** Upload image into canvas */
    _onClickAddImage() {
        const files = $('#personalization_image_upload')[0].files;
        this.imageHandler.addImages(files);
        $('#personalization_image_upload').val('');
    },

    /** Add shape to canvas */
    _onShapeSelect(ev) {
        this.$('.shape-item').removeClass('active');
        $(ev.currentTarget).addClass('active');

        const type = $(ev.currentTarget).data('shape-id');
        this.shapeHandler.addShape(type);
    },

    /** Update shape fill/stroke/width */
    _onChangeShapeProperty(ev) {
        const obj = this.canvasManager.getCanvas().getActiveObject();
        const map = {
            'shape_fill_color': ['fill', ev.target.value],
            'shape_stroke_color': ['stroke', ev.target.value],
            'shape_stroke_width': ['strokeWidth', parseInt(ev.target.value)],
        };

        const prop = map[ev.target.id];
        if (prop) this.shapeHandler.updateShapeProperty(obj, prop[0], prop[1]);
    },

    /** Apply preset color to text or shape */
    _onClickPresetColor(ev) {
        const color = $(ev.currentTarget).data('color');
        const obj = this.canvasManager.getCanvas().getActiveObject();
        if (!obj) return;

        if (obj.type === 'i-text' || obj.type === 'text') {
            this.textHandler.updateTextProperty(obj, 'fill', color);
            $('#text_color').val(color);
        } else if (obj.type !== 'image') {
            this.shapeHandler.updateShapeProperty(obj, 'fill', color);
            $('#shape_fill_color').val(color);
        }
    },

    /** Switch menu panel */
    _onMenuItemClick(ev) {
        const type = $(ev.currentTarget).data('menu');
        this.menuController.switchToPanel(type);
        this.controlsUpdater.hideControls();
    },

    /** Build selector + load initial design type */
    _initDesignTypeSelector() {
        const pdata = this.stateManager.getProductData();

        if (pdata.variants?.length) {
            this.menuController.renderVariantGrid(pdata.variants, this.stateManager.getActiveVariant());

            if (this.editMode) {
                this.$('.menu-item[data-menu="variant"]').css({
                    opacity: 0.5,
                    'pointer-events': 'none',
                    cursor: 'not-allowed',
                });
            }
        }

        // Shapes
        this.menuController.renderShapesGrid(ShapeHandler.getShapesData());

        // Design types
        const types = pdata.design_types || [];
        const defaultType = pdata.default_design_type || types[0];

        this.menuController.initializeDesignTypeSelector(types, defaultType);
        this.stateManager.setActiveDesignType(defaultType);

        this._loadDesignType(defaultType);
    },

    /** Save old and load new design type */
    _onDesignTypeChange(ev) {
        const newType = ev.target.value;
        if (!newType || newType === this.stateManager.getActiveDesignType()) return;

        this._saveCurrentSideState();
        this.stateManager.setActiveDesignType(newType);
        this._loadDesignType(newType);
    },

    /** Save current side JSON */
    _saveCurrentSideState() {
        const type = this.stateManager.getActiveDesignType();
        if (!type) return;

        const json = ObjectUtils.serializeCanvas(this.canvasManager.getCanvas());
        this.stateManager.saveDesignState(type, json);
    },

    /**
     * Load background + zone + saved objects
     */
    _loadDesignType(designType) {
        const pdata = this.stateManager.getProductData();
        const side = pdata.designs?.[designType];

        this.canvasManager.clear();

        let bgUrl = side?.image_url || pdata.fallback_image_url || null;

        const loadSide = () => {
            if (side?.is_restricted_area) {
                const zone = {
                    bound_x: parseFloat(side.bound_x) || 0,
                    bound_y: parseFloat(side.bound_y) || 0,
                    width: parseFloat(side.bound_width || side.width) || 0,
                    height: parseFloat(side.bound_height || side.height) || 0,
                };
                this.canvasManager.setZone(zone);
                this._updateHandlersZone();
            } else {
                this.canvasManager.setZone(null);
                this._updateHandlersZone();
            }
            this._restoreSavedJson(designType);
        };

        if (bgUrl) {
            this.canvasManager.setBackgroundFromUrl(bgUrl, loadSide);
        } else {
            this.canvasManager.getCanvas().setBackgroundImage(null, () =>
                this.canvasManager.getCanvas().renderAll()
            );
            loadSide();
        }
    },

    /** Refresh handler references after zone changes */
    _updateHandlersZone() {
        this.textHandler.updateZone(this.canvasManager.zone);
        this.imageHandler.updateZone(this.canvasManager.zone);
        this.shapeHandler.updateZone(this.canvasManager.zone);
        this.historyManager.updateZoneRect(this.canvasManager.zoneRect);
        this.layerHandler.updateZoneRect(this.canvasManager.zoneRect);
    },

    /**
     * Load saved JSON objects into canvas
     */
    _restoreSavedJson(designType) {
        const canvas = this.canvasManager.getCanvas();
        this.historyManager.isUndoRedoAction = true;

        try {
            // Remove existing non-zone objects
            canvas.getObjects().forEach(o => {
                if (!o.isZoneRect) canvas.remove(o);
            });

            const saved = this.stateManager.getDesignState(designType);

            if (saved?.json) {
                let json = saved.json;
                if (typeof json === 'string') json = JSON.parse(json);

                ObjectUtils.restoreCanvas(canvas, json, () => {
                    if (this.canvasManager.zoneRect) canvas.bringToFront(this.canvasManager.zoneRect);
                    canvas.renderAll();

                    this.layerHandler.assignLayerIds();
                    this.layerHandler.renderLayersList(this.$('#layers_list'), o => this._selectObject(o));

                    this.historyManager.isUndoRedoAction = false;

                    setTimeout(() => {
                        this.historyManager.reset();
                        this.historyManager.saveState();
                    }, 100);
                });
            } else {
                if (this.canvasManager.zoneRect) canvas.bringToFront(this.canvasManager.zoneRect);
                canvas.renderAll();
                this.historyManager.isUndoRedoAction = false;

                setTimeout(() => {
                    this.historyManager.reset();
                    this.historyManager.saveState();
                }, 100);
            }
        } catch (e) {
            console.error("Restore JSON failed:", designType, e);
            this.historyManager.isUndoRedoAction = false;
        }
    },

    /** Set object active */
    _selectObject(obj) {
        const canvas = this.canvasManager.getCanvas();
        canvas.discardActiveObject();
        canvas.setActiveObject(obj);
        canvas.renderAll();

        this.controlsUpdater.updateControls(obj, this.canvasManager.zoneRect);
        this.layerHandler.renderLayersList(this.$('#layers_list'), o => this._selectObject(o));
    },

    /** Enforce min quantity of 1 */
    _onChangeQty(ev) {
        const qty = parseInt(ev.target.value) || 1;
        $('#product_qty').val(Math.max(1, qty));
    },

    /** Change product variant */
    _onVariantChange(ev) {
        if (this.editMode) {
            alert("Cannot change variant while editing.");
            return;
        }

        const newVariantId = parseInt($(ev.currentTarget).data('variant-id'));
        if (!newVariantId || newVariantId === this.stateManager.getActiveVariant()) return;

        this._saveCurrentSideState();
        this.canvasManager.clear();
        this.stateManager.setActiveVariant(newVariantId);
        this.stateManager.clearDesignData();

        return rpc('/shop/product_personalization_data', {
            product_id: parseInt(this.$('#product_id').val()),
            variant_id: newVariantId,
        })
            .then(data => {
                if (data.error) return alert(data.error);

                this.stateManager.setProductData(data);
                this.menuController.renderVariantGrid(data.variants, newVariantId);

                const types = data.design_types || [];
                const defaultType = data.default_design_type || types[0];
                this.menuController.initializeDesignTypeSelector(types, defaultType);
                this.stateManager.setActiveDesignType(defaultType);

                if (defaultType) this._loadDesignType(defaultType);
            })
            .catch(err => {
                console.error("Variant load failed:", err);
                alert("Failed to load variant.");
            });
    },

    /** Build JSON + preview for each side and submit */
    async _onClickAddToCartPersonalized() {
        const canvas = this.canvasManager.getCanvas();
        const variantId = this.stateManager.getActiveVariant();

        if (!canvas || !variantId) {
            alert("Canvas not ready or no variant selected");
            return;
        }

        this._saveCurrentSideState();

        const pdata = this.stateManager.getProductData();
        const designTypes = pdata.design_types || [];
        const allData = this.stateManager.getAllDesignData();

        const designs = {};

        for (const dt of designTypes) {
            const cfg = pdata.designs[dt];
            const bg = cfg?.image_url || pdata.fallback_image_url;

            const saved = this.stateManager.getDesignState(dt);
            const json = saved?.json?.objects?.length
                ? saved.json
                : { objects: [] };

            const preview = await PreviewGenerator.generatePreview(dt, allData, pdata);

            designs[dt] = {
                json: JSON.stringify(json),
                preview: preview,
                background_url: bg,
            };
        }

        const qty = parseInt($('#product_qty').val() || 1);

        if (this.editMode && this.editLineId) {
            // Update existing line
            rpc('/shop/cart/update_line_personalization', {
                line_id: this.editLineId,
                add_qty: qty,
                designs: designs,
            })
                .then(res => res?.success ? window.location.href = "/shop/cart" : alert(res.error))
                .catch(err => {
                    console.error("Update error:", err);
                    alert("Failed to update design");
                });

        } else {
            // Add new line
            rpc('/shop/cart/update_personalization', {
                variant_id: variantId,
                add_qty: qty,
                designs: designs,
            })
                .then(res => res?.success ? window.location.href = "/shop/cart" : alert(res.error))
                .catch(err => {
                    console.error("Add error:", err);
                    alert("Failed to add product");
                });
        }
    },

    /**
     * Undo last action
     */
    _onClickUndo: function () {
        const self = this;
        this.historyManager.undo(() => {
            self.canvasManager.getCanvas().getObjects().forEach(obj => {
                if (obj !== self.canvasManager.zoneRect && !obj.isZoneRect) {
                    self.canvasManager.clampObjectToZone(obj);
                }
            });
        });

        this.controlsUpdater.updateHistoryButtons(
            this.historyManager.canUndo(),
            this.historyManager.canRedo()
        );
    },

    /**
     * Redo last undone action
     */
    _onClickRedo: function () {
        const self = this;
        this.historyManager.redo(() => {
            self.canvasManager.getCanvas().getObjects().forEach(obj => {
                if (obj !== self.canvasManager.zoneRect && !obj.isZoneRect) {
                    self.canvasManager.clampObjectToZone(obj);
                }
            });
        });

        this.controlsUpdater.updateHistoryButtons(
            this.historyManager.canUndo(),
            this.historyManager.canRedo()
        );
    },


    /** Show preview modal of all design sides */
    _onClickPreviewDesigns() {
        const pdata = this.stateManager.getProductData();
        const designTypes = pdata.design_types || [];

        this._saveCurrentSideState();

        const $grid = $('#preview_grid');
        $grid.empty();

        const previews = designTypes.map(dt =>
            PreviewGenerator.generatePreview(dt, this.stateManager.getAllDesignData(), pdata)
                .then(url => {
                    const label = dt.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    return this._buildPreviewCard(label, url);
                })
        );

        Promise.all(previews)
            .then(cols => {
                cols.forEach(col => $grid.append(col));
                $('#preview_personalization_modal').modal('show');
            })
            .catch(err => {
                console.error("Preview generation error:", err);
                alert("Failed to generate previews");
            });
    },

    /** Build preview card */
    _buildPreviewCard(label, imgUrl) {
        const $col = $('<div class="col-12 col-md-6 mb-3"></div>');
        const $card = $('<div class="card h-100"></div>');
        const $body = $('<div class="card-body d-flex flex-column"></div>');

        $body.append(`<strong class="card-title mb-2">${label}</strong>`);

        const $imgWrapper = $(
            `<div class="flex-fill d-flex align-items-center justify-content-center"
                style="height:500px;background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;">
             </div>`
        );

        const $img = $(`<img class="img-fluid rounded" style="max-height:100%;max-width:100%;object-fit:contain;">`);
        $img.attr('src', imgUrl);

        $imgWrapper.append($img);
        $body.append($imgWrapper);
        $card.append($body);
        $col.append($card);

        return $col;
    },

    /** Show preview images in download modal */
    _onClickDownloadDesigns() {
        const pdata = this.stateManager.getProductData();
        const designTypes = pdata.design_types || [];

        this._saveCurrentSideState();

        const $grid = $('#download_preview_grid');
        $grid.empty();

        const previews = designTypes.map(dt =>
            PreviewGenerator.generatePreview(dt, this.stateManager.getAllDesignData(), pdata)
                .then(url => {
                    const label = dt.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    return this._buildDownloadCard(label, dt, url);
                })
        );

        Promise.all(previews)
            .then(cols => {
                cols.forEach(c => $grid.append(c));
                $('#download_personalization_modal').modal('show');
            })
            .catch(err => {
                console.error("Download preview error:", err);
                alert("Failed to generate previews");
            });
    },

    /** Build card for download modal */
    _buildDownloadCard(label, designType, imgUrl) {
        const $col = $('<div class="col-12 col-md-6 mb-3"></div>');
        const $card = $('<div class="card h-100"></div>');
        const $body = $('<div class="card-body d-flex flex-column"></div>');

        $body.append(`<strong class="card-title mb-2">${label}</strong>`);

        const $imgWrapper = $(
            `<div class="flex-fill d-flex align-items-center justify-content-center"
                style="height:500px;background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;">
            </div>`
        );

        const $img = $(`<img class="img-fluid rounded" style="max-height:100%;max-width:100%;object-fit:contain;">`);
        $img.attr('src', imgUrl).attr('data-design-type', designType);

        $imgWrapper.append($img);
        $body.append($imgWrapper);
        $card.append($body);
        $col.append($card);

        return $col;
    },

    /** Download selected format for all design sides */
    _onClickDownloadFormat(ev) {
        const btn = $(ev.currentTarget);
        const format = btn.data('format');

        if (!format) {
            alert("Invalid format.");
            return;
        }

        btn.prop('disabled', true).html(`<i class="fa fa-spinner fa-spin"></i> Downloading...`);

        const pdata = this.stateManager.getProductData();
        const designTypes = pdata.design_types || [];
        const allData = this.stateManager.getAllDesignData();

        let completed = 0;

        designTypes.forEach(dt => {
            PreviewGenerator.generatePreview(dt, allData, pdata)
                .then(url => PreviewGenerator.downloadImageAs(url, dt, format))
                .then(() => {
                    completed++;
                    if (completed === designTypes.length) {
                        setTimeout(() => {
                            $('#download_personalization_modal').modal('hide');

                            $('.download-format-btn').prop('disabled', false).each(function () {
                                const fmt = $(this).data('format');
                                let label = 'PNG';
                                if (fmt === 'jpeg') label = 'JPG';
                                if (fmt === 'webp') label = 'WebP';

                                $(this).html(
                                    `<i class="fa fa-file-image-o fa-2x d-block mb-2"></i>Download as ${label}`
                                );
                            });

                        }, 300);
                    }
                });
        });
    },
});