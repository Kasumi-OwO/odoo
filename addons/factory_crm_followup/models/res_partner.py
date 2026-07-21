from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_factory_customer = fields.Boolean(string="Factory Customer", index=True, copy=False)
    legacy_import_key = fields.Char(string="Legacy Import Key", index=True, copy=False)

    factory_source = fields.Selection(
        [
            ("ai", "AI Prospecting"),
            ("1688", "1688 Inquiry"),
            ("exhibition", "Exhibition"),
            ("referral", "Existing Customer Referral"),
            ("other", "Other"),
        ],
        string="Factory Lead Source",
        tracking=True,
    )
    customer_type = fields.Selection(
        [
            ("gift", "Gift Company"),
            ("wholesaler", "Outdoor Wholesaler"),
            ("ecommerce", "E-commerce Seller"),
            ("project", "Scenic Area / Project"),
            ("individual", "Individual Retail"),
        ],
        string="Customer Type",
        tracking=True,
    )
    wechat = fields.Char(string="WeChat", tracking=True)
    logo_customization = fields.Boolean(string="Needs Logo Customization", tracking=True)
    estimated_quantity = fields.Integer(string="Estimated Purchase Quantity", tracking=True)
    purchase_cycle = fields.Char(string="Purchase Cycle", tracking=True)
    current_supplier = fields.Char(string="Current Supplier", tracking=True)
    customer_concerns = fields.Text(string="Customer Concerns", tracking=True)

    legacy_buyer_nickname = fields.Char(string="Buyer Nickname", index=True)
    legacy_shipping_phone = fields.Char(string="Shipping Address Phone", index=True)
    legacy_buyer_identity = fields.Char(string="Buyer Identity")
    legacy_buyer_level = fields.Char(string="Buyer Level", index=True)
    legacy_province = fields.Char(string="Province")
    legacy_city = fields.Char(string="Legacy City")
    legacy_first_purchase_date = fields.Datetime(string="First Purchase Date")
    legacy_latest_purchase_date = fields.Datetime(string="Latest Purchase Date", index=True)
    legacy_days_since_purchase = fields.Integer(string="Days Since Last Purchase")
    legacy_purchase_count = fields.Integer(string="Purchase Count", aggregator="sum")
    factory_currency_id = fields.Many2one(
        "res.currency",
        string="Historical Purchase Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    legacy_total_purchase_amount = fields.Monetary(
        string="Cumulative Purchase Amount",
        currency_field="factory_currency_id",
        aggregator="sum",
    )
    legacy_first_order_ad_driven = fields.Boolean(string="First Order Ad-driven")
    legacy_contact_name = fields.Char(string="Legacy Contact Name")
    legacy_contact_details = fields.Char(string="Legacy Contact Details")
    legacy_importance_level = fields.Char(string="Importance Level")
    legacy_followup_method = fields.Char(string="Follow-up Method")
    legacy_buyer_demand = fields.Text(string="Buyer Demand")

    _legacy_import_key_unique = models.UniqueIndex(
        "(legacy_import_key) WHERE legacy_import_key IS NOT NULL"
    )

    def action_create_reactivation_opportunity(self):
        self.ensure_one()
        Lead = self.env["crm.lead"]
        opportunity = Lead.search(
            [
                ("partner_id", "=", self.id),
                ("type", "=", "opportunity"),
                ("active", "=", True),
                ("stage_id.is_won", "=", False),
                ("is_reactivation_opportunity", "=", True),
            ],
            limit=1,
        )
        if not opportunity:
            opportunity = Lead.create(
                {
                    "name": _("Reactivation - %s", self.name),
                    "type": "opportunity",
                    "partner_id": self.id,
                    "user_id": self.env.user.id,
                    "contact_name": self.name,
                    "phone": self.phone,
                    "wechat": self.wechat,
                    "factory_source": self.factory_source or "other",
                    "customer_type": self.customer_type,
                    "logo_customization": self.logo_customization,
                    "estimated_quantity": self.estimated_quantity,
                    "purchase_cycle": self.purchase_cycle,
                    "current_supplier": self.current_supplier,
                    "customer_concerns": self.customer_concerns,
                    "is_repeat_customer": self.legacy_purchase_count > 1,
                    "is_reactivation_opportunity": True,
                }
            )
            opportunity.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=_("Initial customer reactivation call"),
                user_id=self.env.user.id,
                date_deadline=fields.Date.context_today(self),
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Reactivation Opportunity"),
            "res_model": "crm.lead",
            "res_id": opportunity.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
