from datetime import timedelta

from odoo import _, api, fields, models


CUSTOMER_GRADES = [
    ("a", "A - High Intent"),
    ("b", "B - Potential"),
    ("c", "C - Price Comparison"),
    ("d", "D - Invalid"),
]


class CrmLead(models.Model):
    _inherit = "crm.lead"

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

    asked_price = fields.Boolean(string="Asked About Price")
    asked_sample = fields.Boolean(string="Asked About Sample")
    asked_logo = fields.Boolean(string="Asked About Logo")
    asked_delivery = fields.Boolean(string="Asked About Delivery")
    asked_quantity = fields.Boolean(string="Discussed Quantity")
    recent_purchase_plan = fields.Boolean(string="Recent Purchase Plan")
    industry_match = fields.Boolean(string="Industry Match")
    price_only = fields.Boolean(string="Only Comparing Price")
    cold_response = fields.Boolean(string="Cold Response")
    invalid_customer = fields.Boolean(string="Invalid / Irrelevant Customer")

    automatic_grade = fields.Selection(
        CUSTOMER_GRADES,
        string="Automatic Grade",
        compute="_compute_customer_grade",
        store=True,
    )
    manual_grade = fields.Selection(
        CUSTOMER_GRADES,
        string="Manual Grade Override",
        tracking=True,
        help="Leave empty to use the grade calculated from customer signals.",
    )
    customer_grade = fields.Selection(
        CUSTOMER_GRADES,
        string="Customer Grade",
        compute="_compute_customer_grade",
        store=True,
        index=True,
        tracking=True,
    )
    followup_interval_days = fields.Integer(
        string="Recommended Follow-up Interval",
        compute="_compute_followup_schedule",
        store=True,
    )
    followup_ids = fields.One2many(
        "factory.crm.followup", "lead_id", string="Follow-up Records"
    )
    followup_count = fields.Integer(compute="_compute_followup_data", store=True)
    last_followup_date = fields.Date(
        string="Last Follow-up", compute="_compute_followup_data", store=True, index=True
    )
    next_followup_date = fields.Date(
        string="Next Follow-up", compute="_compute_followup_data", store=True, index=True
    )
    is_followup_overdue = fields.Boolean(string="Follow-up Overdue", index=True, copy=False)
    profile_complete = fields.Boolean(
        string="Profile Complete", compute="_compute_profile_complete", store=True
    )
    is_dormant = fields.Boolean(string="Dormant Customer", index=True, copy=False, tracking=True)
    dormant_date = fields.Date(string="Dormant Since", copy=False, readonly=True)
    next_repurchase_date = fields.Date(string="Next Repurchase Visit", tracking=True)
    sample_sent = fields.Boolean(string="Sample Sent", tracking=True)
    sample_tracking_number = fields.Char(string="Sample Tracking Number", tracking=True)
    sample_converted = fields.Boolean(string="Sample Converted", tracking=True)
    is_repeat_customer = fields.Boolean(string="Repeat Customer", tracking=True)
    validity_rate = fields.Float(
        string="Valid Lead Rate", compute="_compute_dashboard_indicators", store=True, aggregator="avg"
    )
    conversion_rate = fields.Float(
        string="Conversion Rate", compute="_compute_dashboard_indicators", store=True, aggregator="avg"
    )
    sample_sent_count = fields.Integer(
        string="Samples Sent", compute="_compute_dashboard_indicators", store=True
    )
    sample_conversion_rate = fields.Float(
        string="Sample Conversion Rate",
        compute="_compute_dashboard_indicators",
        store=True,
        aggregator="avg",
    )
    repeat_customer_count = fields.Integer(
        string="Repeat Customers", compute="_compute_dashboard_indicators", store=True
    )

    # Historical customer data imported from the legacy Wutong CRM export.  Keep
    # these values separate from the live sales fields: the source workbook can
    # contain contradictory dates and duplicate names or phone numbers, so an
    # import must preserve each original row without guessing or merging.
    legacy_import_key = fields.Char(string="Legacy Import Key", copy=False, readonly=True)
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
    legacy_total_purchase_amount = fields.Monetary(
        string="Cumulative Purchase Amount",
        currency_field="company_currency",
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

    @api.depends(
        "asked_price",
        "asked_sample",
        "asked_logo",
        "asked_delivery",
        "asked_quantity",
        "recent_purchase_plan",
        "industry_match",
        "current_supplier",
        "price_only",
        "cold_response",
        "invalid_customer",
        "manual_grade",
    )
    def _compute_customer_grade(self):
        for lead in self:
            if lead.invalid_customer:
                automatic = "d"
            elif any(
                (
                    lead.asked_price,
                    lead.asked_sample,
                    lead.asked_logo,
                    lead.asked_delivery,
                    lead.asked_quantity,
                    lead.recent_purchase_plan,
                )
            ):
                automatic = "a"
            elif lead.price_only or lead.cold_response:
                automatic = "c"
            elif lead.industry_match or lead.current_supplier:
                automatic = "b"
            else:
                automatic = "c"
            lead.automatic_grade = automatic
            lead.customer_grade = lead.manual_grade or automatic

    @api.depends("customer_grade")
    def _compute_followup_schedule(self):
        intervals = {"a": 3, "b": 7, "c": 30, "d": 0}
        for lead in self:
            lead.followup_interval_days = intervals.get(lead.customer_grade, 0)

    @api.depends("followup_ids.followup_date", "followup_ids.next_followup_date")
    def _compute_followup_data(self):
        for lead in self:
            followups = lead.followup_ids.sorted(
                key=lambda followup: (followup.followup_date, followup.id), reverse=True
            )
            lead.followup_count = len(followups)
            lead.last_followup_date = followups[:1].followup_date if followups else False
            lead.next_followup_date = followups[:1].next_followup_date if followups else False

    @api.depends("partner_name", "contact_name", "phone", "wechat")
    def _compute_profile_complete(self):
        for lead in self:
            lead.profile_complete = all(
                (lead.partner_name or lead.partner_id.name, lead.contact_name, lead.phone, lead.wechat)
            )

    @api.depends("customer_grade", "won_status", "sample_sent", "sample_converted", "is_repeat_customer")
    def _compute_dashboard_indicators(self):
        for lead in self:
            lead.validity_rate = 0.0 if lead.customer_grade == "d" else 1.0
            lead.conversion_rate = 1.0 if lead.won_status == "won" else 0.0
            lead.sample_sent_count = int(lead.sample_sent)
            lead.sample_conversion_rate = 1.0 if lead.sample_sent and lead.sample_converted else 0.0
            lead.repeat_customer_count = int(lead.is_repeat_customer)

    def _factory_activity_exists(self, summary):
        self.ensure_one()
        return bool(
            self.env["mail.activity"].search_count(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
        )

    def _schedule_factory_activity(self, summary, note):
        self.ensure_one()
        if not self.user_id or self._factory_activity_exists(summary):
            return
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=self.user_id.id,
            date_deadline=fields.Date.context_today(self),
            summary=summary,
            note=note,
        )

    @api.model
    def _cron_refresh_factory_followups(self):
        today = fields.Date.context_today(self)
        dormant_cutoff = today - timedelta(days=90)
        leads = self.sudo().search([("active", "=", True)])
        for lead in leads:
            reference_date = lead.last_followup_date or fields.Date.to_date(lead.create_date)
            reminder_days = {"a": 7, "b": 15}.get(lead.customer_grade)
            overdue = bool(
                reminder_days
                and reference_date
                and reference_date <= today - timedelta(days=reminder_days)
            )
            dormant = bool(
                lead.won_status != "won"
                and reference_date
                and reference_date <= dormant_cutoff
            )
            values = {"is_followup_overdue": overdue, "is_dormant": dormant}
            if dormant and not lead.is_dormant:
                values["dormant_date"] = today
            elif not dormant and lead.is_dormant:
                values["dormant_date"] = False
            lead.write(values)

            if overdue:
                lead._schedule_factory_activity(
                    _("Customer follow-up overdue"),
                    _(
                        "This %(grade)s-grade customer has not been followed up on time.",
                        grade=lead.customer_grade.upper(),
                    ),
                )
            if not lead.profile_complete and fields.Date.to_date(lead.create_date) <= today - timedelta(days=3):
                lead._schedule_factory_activity(
                    _("Complete new customer profile"),
                    _("The customer profile has been incomplete for at least 3 days."),
                )
            if lead.next_repurchase_date and lead.next_repurchase_date <= today:
                lead._schedule_factory_activity(
                    _("Customer repurchase visit"),
                    _("Contact this customer for the scheduled repurchase visit."),
                )
