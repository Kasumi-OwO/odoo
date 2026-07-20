from datetime import timedelta

from psycopg2.errors import UniqueViolation

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFactoryCrmFollowup(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lead = cls.env["crm.lead"].create(
            {
                "name": "Outdoor Chair Buyer",
                "partner_name": "Example Buyer Ltd",
                "contact_name": "Zhang San",
                "phone": "13800000000",
                "wechat": "buyer_wechat",
                "factory_source": "1688",
                "customer_type": "wholesaler",
                "user_id": cls.env.user.id,
            }
        )
        cls.sales_user = mail_new_test_user(
            cls.env,
            login="factory_sales_user",
            name="Factory Sales User",
            groups="sales_team.group_sale_salesman",
        )
        cls.sales_manager = mail_new_test_user(
            cls.env,
            login="factory_sales_manager",
            name="Factory Sales Manager",
            groups="sales_team.group_sale_manager",
        )

    def test_grade_and_manual_override(self):
        self.assertEqual(self.lead.customer_grade, "c")
        self.lead.industry_match = True
        self.assertEqual(self.lead.customer_grade, "b")
        self.lead.asked_sample = True
        self.assertEqual(self.lead.customer_grade, "a")
        self.assertEqual(self.lead.followup_interval_days, 3)
        self.lead.manual_grade = "d"
        self.assertEqual(self.lead.automatic_grade, "a")
        self.assertEqual(self.lead.customer_grade, "d")

    def test_legacy_purchase_fields_preserve_source_data(self):
        legacy = self.env["crm.lead"].create(
            {
                "name": "Legacy buyer",
                "legacy_import_key": "wutong-2",
                "legacy_buyer_nickname": "买家甲",
                "legacy_shipping_phone": "13800000001",
                "legacy_first_purchase_date": "2024-09-24 16:34:00",
                "legacy_latest_purchase_date": "2022-07-18 03:10:29",
                "legacy_purchase_count": 1,
                "legacy_total_purchase_amount": 177,
            }
        )
        self.assertGreater(legacy.legacy_first_purchase_date, legacy.legacy_latest_purchase_date)
        self.assertEqual(legacy.legacy_total_purchase_amount, 177)
        with self.assertRaises(UniqueViolation), self.cr.savepoint():
            legacy.copy({"legacy_import_key": "wutong-2"})

    def test_followup_trace_updates_lead(self):
        today = fields.Date.context_today(self.lead)
        self.env["factory.crm.followup"].create(
            {
                "lead_id": self.lead.id,
                "communication_content": "Customer asked for a delivery estimate.",
                "customer_intent": "high",
                "customer_concern": "Delivery time",
                "next_followup_date": today + timedelta(days=3),
            }
        )
        self.assertEqual(self.lead.followup_count, 1)
        self.assertEqual(self.lead.last_followup_date, today)
        self.assertEqual(self.lead.next_followup_date, today + timedelta(days=3))
        self.assertEqual(self.lead.customer_grade, "a")
        self.assertEqual(self.lead.customer_concerns, "Delivery time")

    def test_cron_marks_overdue_and_dormant_without_duplicate_activity(self):
        old_date = fields.Date.context_today(self.lead) - timedelta(days=100)
        self.env["factory.crm.followup"].create(
            {
                "lead_id": self.lead.id,
                "followup_date": old_date,
                "communication_content": "Old conversation",
                "customer_intent": "high",
                "customer_concern": "Price",
                "next_followup_date": old_date + timedelta(days=3),
            }
        )
        self.env["crm.lead"]._cron_refresh_factory_followups()
        self.assertTrue(self.lead.is_followup_overdue)
        self.assertTrue(self.lead.is_dormant)
        activities = self.lead.activity_ids.filtered(
            lambda activity: activity.summary == "Customer follow-up overdue"
        )
        self.assertEqual(len(activities), 1)
        self.env["crm.lead"]._cron_refresh_factory_followups()
        self.assertEqual(
            len(
                self.lead.activity_ids.filtered(
                    lambda activity: activity.summary == "Customer follow-up overdue"
                )
            ),
            1,
        )

    def test_salesperson_data_isolation_and_immutable_trace(self):
        lead_domain = [("id", "=", self.lead.id)]
        self.assertFalse(self.env["crm.lead"].with_user(self.sales_user).search(lead_domain))
        self.assertTrue(self.env["crm.lead"].with_user(self.sales_manager).search(lead_domain))

        own_lead = self.env["crm.lead"].with_user(self.sales_user).create(
            {"name": "Salesperson Customer", "user_id": self.sales_user.id}
        )
        followup = self.env["factory.crm.followup"].with_user(self.sales_user).create(
            {
                "lead_id": own_lead.id,
                "communication_content": "Initial contact",
                "customer_intent": "medium",
                "customer_concern": "Minimum order quantity",
                "next_followup_date": fields.Date.context_today(own_lead) + timedelta(days=7),
            }
        )
        with self.assertRaises(AccessError):
            followup.with_user(self.sales_user).unlink()
        followup.with_user(self.sales_manager).unlink()
