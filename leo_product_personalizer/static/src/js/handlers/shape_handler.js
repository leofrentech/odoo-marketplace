/** @odoo-module **/

// Shape Handler - Creates and manipulates shapes on the Fabric canvas

export class ShapeHandler {
    /**
     * @param {fabric.Canvas} fabricCanvas - Fabric.js canvas instance
     * @param {Object|null} zone - Optional restricted zone
     */
    constructor(fabricCanvas, zone) {
        this.fabricCanvas = fabricCanvas;
        this.zone = zone;
    }

    /** Get predefined shape list */
    static getShapesData() {
        return [
            { id: 'rect', name: 'Rectangle', icon: 'fa-square', faClass: 'fa fa-square' },
            { id: 'circle', name: 'Circle', icon: 'fa-circle', faClass: 'fa fa-circle' },
            { id: 'triangle', name: 'Triangle', icon: 'fa-play', faClass: 'fa fa-play' },
            { id: 'star', name: 'Star', icon: 'fa-star', faClass: 'fa fa-star' },
            { id: 'heart', name: 'Heart', icon: 'fa-heart', faClass: 'fa fa-heart' },
            { id: 'diamond', name: 'Diamond', icon: 'fa-diamond', faClass: 'fa fa-diamond' },
            { id: 'ellipse', name: 'Ellipse', icon: 'fa-ellipsis-h', faClass: 'fa fa-ellipsis-h' },
            { id: 'polygon', name: 'Pentagon', icon: 'fa-certificate', faClass: 'fa fa-certificate' },
            { id: 'hexagon', name: 'Hexagon', icon: 'fa-circle', faClass: 'fa fa-circle' },
            { id: 'arrow', name: 'Arrow', icon: 'fa-arrow-right', faClass: 'fa fa-arrow-right' },
            { id: 'square', name: 'Square', icon: 'fa-square', faClass: 'fa fa-square' },
            { id: 'line', name: 'Line', icon: 'fa-minus', faClass: 'fa fa-minus' },
        ];
    }

    /**
     * Add a new shape to the canvas
     * @param {string} shapeType
     * @param {Object} options
     */
    addShape(shapeType, options = {}) {
        let left = 100, top = 100;

        if (this.zone) {
            left = this.zone.bound_x + this.zone.width / 2;
            top = this.zone.bound_y + this.zone.height / 2;
        }

        const props = {
            left,
            top,
            fill: options.fill || '#3b82f6',
            stroke: options.stroke || '#1e40af',
            strokeWidth: options.strokeWidth || 2,
            ...options
        };

        const shape = this._createShape(shapeType, props);
        if (!shape) return null;

        try { shape.__label = this._getShapeNameById(shapeType); } catch (e) {}

        this.fabricCanvas.add(shape);
        this.fabricCanvas.setActiveObject(shape);
        this.fabricCanvas.renderAll();

        return shape;
    }

    /**
     * Create shape instance based on type
     * @private
     */
    _createShape(shapeType, props) {
        switch (shapeType) {
            case 'rect':
                return new fabric.Rect({ ...props, width: 100, height: 70 });
            case 'square':
                return new fabric.Rect({ ...props, width: 100, height: 100 });
            case 'circle':
                return new fabric.Circle({ ...props, radius: 50 });
            case 'ellipse':
                return new fabric.Ellipse({ ...props, rx: 60, ry: 40 });
            case 'triangle':
                return new fabric.Triangle({ ...props, width: 100, height: 100 });
            case 'line':
                return new fabric.Line([50, 50, 200, 50], { ...props, fill: null, strokeWidth: 4 });
            case 'polygon':
                return new fabric.Polygon([
                    { x: 50, y: 0 }, { x: 100, y: 38 }, { x: 82, y: 100 },
                    { x: 18, y: 100 }, { x: 0, y: 38 }
                ], props);
            case 'star':
                return this._createStar(props);
            case 'heart':
                return new fabric.Path(
                    'M 50,30 C 50,20 40,10 30,10 C 20,10 10,20 10,30 C 10,50 30,70 50,90 C 70,70 90,50 90,30 C 90,20 80,10 70,10 C 60,10 50,20 50,30 Z',
                    { ...props, scaleX: 0.8, scaleY: 0.8 }
                );
            case 'arrow':
                return new fabric.Path(
                    'M 10,50 L 60,50 L 60,30 L 90,55 L 60,80 L 60,60 L 10,60 Z',
                    props
                );
            case 'hexagon':
                return this._createHexagon(props);
            case 'diamond':
                return new fabric.Polygon(
                    [
                        { x: 50, y: 0 }, { x: 100, y: 50 },
                        { x: 50, y: 100 }, { x: 0, y: 50 }
                    ],
                    props
                );
            default:
                return null;
        }
    }

    /**
     * Create a star shape
     * @private
     */
    _createStar(props) {
        const pts = [];
        for (let i = 0; i < 10; i++) {
            const r = i % 2 ? 25 : 50;
            const a = (i * Math.PI) / 5;
            pts.push({
                x: 50 + r * Math.sin(a),
                y: 50 - r * Math.cos(a)
            });
        }
        return new fabric.Polygon(pts, props);
    }

    /**
     * Create a hexagon shape
     * @private
     */
    _createHexagon(props) {
        const pts = [];
        for (let i = 0; i < 6; i++) {
            pts.push({
                x: 50 + 50 * Math.cos((Math.PI / 3) * i),
                y: 50 + 50 * Math.sin((Math.PI / 3) * i)
            });
        }
        return new fabric.Polygon(pts, props);
    }

    /**
     * Get readable name for shape ID
     * @private
     */
    _getShapeNameById(shapeId) {
        const shape = ShapeHandler.getShapesData().find(s => s.id === shapeId);
        return shape ? shape.name : shapeId;
    }

    /**
     * Update shape properties (color, stroke, etc.)
     */
    updateShapeProperty(shapeObj, property, value) {
        if (!shapeObj) return;
        if (shapeObj.type === 'i-text' || shapeObj.type === 'text' || shapeObj.type === 'image') return;

        shapeObj.set(property, value);
        this.fabricCanvas.renderAll();
    }

    /** Update restricted zone */
    updateZone(zone) {
        this.zone = zone;
    }
}