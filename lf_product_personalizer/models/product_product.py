from odoo import fields, models, api


class ProductProduct(models.Model):
    # ------------------------------------------------------------------
    # 1. PRIVATE ATTRIBUTES
    # ------------------------------------------------------------------

    _inherit = "product.product"

    # ------------------------------------------------------------------
    # 2. DEFAULT METHODS AND default_get
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 3. FIELD DECLARATIONS
    # ------------------------------------------------------------------

    design_config_ids = fields.One2many(
        string="Design Configurations",
        comodel_name="product.design.config",
        inverse_name="product_variant_id",
        compute="_compute_design_config_ids",
        inverse="_inverse_design_config_ids",
        readonly=False,
    )

    # ------------------------------------------------------------------
    # 4. COMPUTE, INVERSE AND SEARCH METHODS
    # ------------------------------------------------------------------

    @api.depends('product_tmpl_id.design_config_ids')
    def _compute_design_config_ids(self):
        for product in self:
            if not product.id:
                product.design_config_ids = False
                continue
            product.design_config_ids = product.product_tmpl_id.design_config_ids.filtered(
                lambda config_type: config_type.product_variant_id <= product
            )


    def _inverse_design_config_ids(self):
        for product in self:
            template = product.product_tmpl_id
            template.design_config_ids = (
                product.design_config_ids
                | template.design_config_ids.filtered(
                    lambda config_type: config_type.product_variant_id
                    and config_type.product_variant_id != product
                )
            )

    # ------------------------------------------------------------------
    # 5. SELECTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6. CONSTRAINTS METHODS AND ONCHANGE METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 7. CRUD METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. ACTION METHODS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 9. BUSINESS METHODS
    # ------------------------------------------------------------------
