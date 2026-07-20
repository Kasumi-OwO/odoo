from odoo import api, fields, models


class FactoryCrmFollowup(models.Model):
    _name = "factory.crm.followup"
    _description = "Factory CRM Follow-up Record"
    _order = "followup_date desc, id desc"
    _check_company_auto = True

    lead_id = fields.Many2one(
        "crm.lead", string="Customer / Lead", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="lead_id.company_id", store=True, index=True)
    user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    followup_date = fields.Date(
        string="Communication Date", required=True, default=fields.Date.context_today, index=True
    )
    communication_content = fields.Text(string="Communication Content", required=True)
    customer_intent = fields.Selection(
        [
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("invalid", "Invalid"),
        ],
        string="Customer Intent",
        required=True,
    )
    customer_concern = fields.Text(string="Customer Concern", required=True)
    next_followup_date = fields.Date(string="Next Follow-up", required=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            values = {"customer_concerns": record.customer_concern, "is_dormant": False, "dormant_date": False}
            if record.customer_intent == "high":
                values["recent_purchase_plan"] = True
            elif record.customer_intent == "medium":
                values["industry_match"] = True
            elif record.customer_intent == "low":
                values["cold_response"] = True
            elif record.customer_intent == "invalid":
                values["invalid_customer"] = True
            record.lead_id.write(values)
        return records
