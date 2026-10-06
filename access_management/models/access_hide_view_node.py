from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import ValidationError

COLLECTED_VIEW_TYPES = ("form", "list", "kanban")
BUTTONS_XPATH = "//button[@type='object' or @type='action'][@name]"

# Kind of view node of each tab, by the field linking its lines to the rule
NODE_OPTION_BY_RULE_FIELD = {
    "access_rule_btn_id": "button",
    "access_rule_page_id": "page",
    "access_rule_id": "link",
}


class AccessHideViewNode(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _name = "access.hide.view.node"
    _description = "Access Hide View Nodes"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    access_rule_id = fields.Many2one("access.rule", "Access Rule", ondelete="cascade")
    model_id = fields.Many2one("ir.model", "Model", required=True, ondelete="cascade")
    view_node_id = fields.Many2one("view.node", "View Node")
    is_smart_button = fields.Boolean(
        "Is Smart Button?", related="view_node_id.is_smart_button"
    )

    access_rule_btn_id = fields.Many2one(
        "access.rule", "Hide Button Rule", ondelete="cascade"
    )
    access_rule_page_id = fields.Many2one(
        "access.rule", "Hide Page Rule", ondelete="cascade"
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    @api.constrains("model_id", "view_node_id")
    def _check_view_node_id(self):
        for line in self.filtered("view_node_id"):
            node_option = line._get_node_option()
            if line.view_node_id.model_id != line.model_id or (
                node_option and line.view_node_id.node_option != node_option
            ):
                raise ValidationError(
                    self.env._(
                        "%(node)s is not part of the views of %(model)s.",
                        node=line.view_node_id.display_name,
                        model=line.model_id.name,
                    )
                )

    @api.onchange("model_id", "access_rule_id")
    def _onchange_model_id_collect_view_nodes(self):
        """Collect the buttons, pages and links of the model's views, so they
        can be selected on the rule."""
        node_option = self._get_node_option()
        if self.view_node_id and (
            self.view_node_id.model_id != self.model_id
            or (node_option and self.view_node_id.node_option != node_option)
        ):
            self.view_node_id = False

        if not self.model_id or self.model_id.model not in self.env:
            return

        # sudo: collect the nodes of every view, whatever the groups of the
        # rule manager; only their names and labels are stored.
        model = self.env[self.model_id.model].sudo()
        views = self.env["ir.ui.view"].sudo().search([
            ("model", "=", model._name),
            ("type", "in", COLLECTED_VIEW_TYPES),
            ("mode", "=", "primary"),
        ])
        for view in views:
            view_info = model.get_view(view_id=view.id, view_type=view.type)
            arch = etree.fromstring(view_info["arch"])
            self._collect_links(arch)
            self._collect_buttons(arch, view.type)
            if view.type == "form":
                self._collect_smart_buttons(arch)
                self._collect_pages(arch)

        if node_option and not self.env["view.node"].search_count([
            ("model_id", "=", self.model_id.id),
            ("node_option", "=", node_option),
        ]):
            labels = {
                "button": self.env._("buttons"),
                "page": self.env._("pages"),
                "link": self.env._("links"),
            }
            return {"warning": {
                "title": self.env._("Nothing to hide"),
                "message": self.env._(
                    "The views of %(model)s have no %(nodes)s to hide.",
                    model=self.model_id.name,
                    nodes=labels[node_option],
                ),
            }}

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------

    def _get_node_option(self):
        """Kind of view node (button, page or link) the line hides."""
        if node_option := self.env.context.get("access_management_node_option"):
            return node_option
        for field_name, node_option in NODE_OPTION_BY_RULE_FIELD.items():
            if self[field_name]:
                return node_option
        return False

    def _ensure_view_node(
        self,
        node_option,
        node_string,
        name=False,
        button_type=False,
        is_smart_button=False,
    ):
        domain = [
            ("model_id", "=", self.model_id.id),
            ("node_option", "=", node_option),
            ("node_string", "=", node_string),
        ]
        if name:
            domain.append(("name", "=", name))
        if button_type:
            domain.append(("button_type", "=", button_type))

        view_node = self.env["view.node"].search(domain, limit=1)
        if not view_node:
            view_node = self.env["view.node"].create({
                "model_id": self.model_id.id,
                "node_option": node_option,
                "node_string": node_string,
                "name": name,
                "button_type": button_type,
                "is_smart_button": is_smart_button,
                "lang_code": self.env.lang,
            })
        elif is_smart_button and not view_node.is_smart_button:
            view_node.is_smart_button = True
        return view_node

    def _collect_links(self, arch):
        for link in arch.xpath("//a[@type][@name]"):
            text, name, link_type = link.text, link.get("name"), link.get("type")
            if text and "\n" not in text and name and link_type:
                self._ensure_view_node("link", text, name=name, button_type=link_type)

    def _collect_buttons(self, arch, view_type):
        for button in arch.xpath(BUTTONS_XPATH):
            string = button.get("string")
            text = button.text
            if not string and view_type == "kanban" and text and text[0] != "\n":
                string = text
            if not string and button.get("type") == "object":
                stat_texts = button.findall(".//*[@class='o_stat_text']")
                string = _join_texts(stat_texts)
            if string and button.get("name"):
                self._ensure_view_node(
                    "button",
                    string,
                    name=button.get("name"),
                    button_type=button.get("type"),
                )

    def _collect_smart_buttons(self, arch):
        for button_box in arch.xpath("//div[@class='oe_button_box']")[:1]:
            for button in button_box.xpath(f".{BUTTONS_XPATH}"):
                if string := _smart_button_string(button):
                    self._ensure_view_node(
                        "button",
                        string,
                        name=button.get("name"),
                        button_type=button.get("type"),
                        is_smart_button=True,
                    )

    def _collect_pages(self, arch):
        pages = arch.xpath("//page[@string]")
        if self.model_id.model == "res.config.settings":
            pages += arch.xpath("//app[@string]")
        for page in pages:
            self._ensure_view_node(
                "page", page.get("string"), name=page.get("name")
            )


def _join_texts(nodes):
    texts = (node.text.strip() for node in nodes if node.text)
    return " ".join(text for text in texts if text)


def _smart_button_string(button):
    """Label of a smart button: its statinfo field or its spans' texts."""
    if fields_ := button.findall("field"):
        return fields_[0].get("string") or button.get("string")
    spans = button.findall("span")
    if not spans and (divs := button.findall("div")):
        spans = divs[0].findall("span")
    return _join_texts(spans) or button.get("string")
