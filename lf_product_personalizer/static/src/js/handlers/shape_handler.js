import { _t } from "@web/core/l10n/translation";
import { ObjectUtils } from "../utils/object_utils";
import { EDITOR_SIZE } from "../utils/fabric_loader";

function regularPolygon(sides, radius, rotation = -Math.PI / 2) {
    return Array.from({ length: sides }, (_, i) => ({
        x: radius + radius * Math.cos(rotation + (2 * Math.PI * i) / sides),
        y: radius + radius * Math.sin(rotation + (2 * Math.PI * i) / sides),
    }));
}

function star(points, outer, inner) {
    return Array.from({ length: points * 2 }, (_, i) => {
        const radius = i % 2 ? inner : outer;
        const angle = (Math.PI * i) / points - Math.PI / 2;
        return { x: outer + radius * Math.cos(angle), y: outer + radius * Math.sin(angle) };
    });
}

export class ShapeHandler {
    constructor(editor) {
        this.editor = editor;
    }

    static get shapes() {
        return [
            { id: "rect", name: _t("Rectangle"), icon: "fa-square" },
            { id: "circle", name: _t("Circle"), icon: "fa-circle" },
            { id: "triangle", name: _t("Triangle"), icon: "fa-play fa-rotate-270" },
            { id: "star", name: _t("Star"), icon: "fa-star" },
            { id: "heart", name: _t("Heart"), icon: "fa-heart" },
            { id: "diamond", name: _t("Diamond"), icon: "fa-square fa-rotate-45" },
            { id: "hexagon", name: _t("Hexagon"), icon: "fa-stop-circle-o" },
            { id: "arrow", name: _t("Arrow"), icon: "fa-long-arrow-right" },
            { id: "line", name: _t("Line"), icon: "fa-minus" },
        ];
    }

    add(shapeId, { fill, stroke }) {
        const fabric = window.fabric;
        const props = { fill, stroke, strokeWidth: 0, strokeUniform: true };
        const name = ShapeHandler.shapes.find((shape) => shape.id === shapeId)?.name || shapeId;
        let obj;
        switch (shapeId) {
            case "rect":
                obj = new fabric.Rect({ ...props, width: 160, height: 100, rx: 6, ry: 6 });
                break;
            case "circle":
                obj = new fabric.Circle({ ...props, radius: 60 });
                break;
            case "triangle":
                obj = new fabric.Triangle({ ...props, width: 130, height: 115 });
                break;
            case "star":
                obj = new fabric.Polygon(star(5, 65, 28), props);
                break;
            case "heart":
                obj = new fabric.Path(
                    "M 50,30 C 50,20 40,10 30,10 C 20,10 10,20 10,30 C 10,50 30,70 50,90 " +
                        "C 70,70 90,50 90,30 C 90,20 80,10 70,10 C 60,10 50,20 50,30 Z",
                    { ...props, scaleX: 1.4, scaleY: 1.4 }
                );
                break;
            case "diamond":
                obj = new fabric.Polygon(regularPolygon(4, 65), props);
                break;
            case "hexagon":
                obj = new fabric.Polygon(regularPolygon(6, 60), props);
                break;
            case "arrow":
                obj = new fabric.Path("M 0,20 L 90,20 L 90,0 L 130,35 L 90,70 L 90,50 L 0,50 Z", props);
                break;
            case "line":
                obj = new fabric.Line([0, 0, 180, 0], { stroke: fill, strokeWidth: 6, strokeUniform: true });
                break;
            default:
                return null;
        }
        obj.set({ lfLabel: name });
        const zone = this.editor.canvasManager.zone;
        ObjectUtils.center(obj, zone, EDITOR_SIZE);
        ObjectUtils.fit(obj, zone, EDITOR_SIZE);
        this.editor.canvasManager.canvas.add(obj);
        this.editor.canvasManager.canvas.setActiveObject(obj);
        this.editor.canvasManager.canvas.requestRenderAll();
        return obj;
    }

    update(obj, props) {
        if (!obj) {
            return;
        }
        if (obj.type === "line" && props.fill) {
            props = { stroke: props.fill };
        }
        obj.set(props);
        this.editor.canvasManager.canvas.requestRenderAll();
        this.editor.canvasManager.canvas.fire("object:modified", { target: obj });
    }
}
