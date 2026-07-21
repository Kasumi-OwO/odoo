"""Create customer master records from imported legacy leads.

Run from an Odoo shell after upgrading the addon::

    .venv/bin/python odoo-bin shell -c odoo.conf -d DATABASE \
      < addons/factory_crm_followup/scripts/migrate_legacy_leads_to_partners.py

The migration is idempotent.  It uses the immutable legacy import key, links
each source lead to its customer, and archives only those source leads.  Active
reactivation opportunities are never touched.
"""


IMPORT_PREFIX = "wutong-crm-2011-2024"
BATCH_SIZE = 500


Lead = env["crm.lead"].with_context(
    active_test=False,
    mail_create_nosubscribe=True,
    tracking_disable=True,
)
Partner = env["res.partner"].with_context(
    active_test=False,
    mail_create_nosubscribe=True,
    tracking_disable=True,
)
source_leads = Lead.search(
    [
        ("legacy_import_key", "like", f"{IMPORT_PREFIX}:%"),
        ("type", "=", "lead"),
    ],
    order="id",
)
existing_partners = {
    partner.legacy_import_key: partner
    for partner in Partner.search(
        [("legacy_import_key", "like", f"{IMPORT_PREFIX}:%")]
    )
}


def partner_values(lead):
    return {
        "name": lead.legacy_buyer_nickname or lead.name,
        "is_company": False,
        "type": "contact",
        "active": True,
        "company_id": lead.company_id.id,
        "user_id": lead.user_id.id,
        "phone": lead.phone or lead.legacy_shipping_phone,
        "city": lead.city or lead.legacy_city,
        "is_factory_customer": True,
        "legacy_import_key": lead.legacy_import_key,
        "factory_source": lead.factory_source,
        "customer_type": lead.customer_type,
        "wechat": lead.wechat,
        "logo_customization": lead.logo_customization,
        "estimated_quantity": lead.estimated_quantity,
        "purchase_cycle": lead.purchase_cycle,
        "current_supplier": lead.current_supplier,
        "customer_concerns": lead.customer_concerns,
        "legacy_buyer_nickname": lead.legacy_buyer_nickname,
        "legacy_shipping_phone": lead.legacy_shipping_phone,
        "legacy_buyer_identity": lead.legacy_buyer_identity,
        "legacy_buyer_level": lead.legacy_buyer_level,
        "legacy_province": lead.legacy_province,
        "legacy_city": lead.legacy_city,
        "legacy_first_purchase_date": lead.legacy_first_purchase_date,
        "legacy_latest_purchase_date": lead.legacy_latest_purchase_date,
        "legacy_days_since_purchase": lead.legacy_days_since_purchase,
        "legacy_purchase_count": lead.legacy_purchase_count,
        "legacy_total_purchase_amount": lead.legacy_total_purchase_amount,
        "legacy_first_order_ad_driven": lead.legacy_first_order_ad_driven,
        "legacy_contact_name": lead.legacy_contact_name,
        "legacy_contact_details": lead.legacy_contact_details,
        "legacy_importance_level": lead.legacy_importance_level,
        "legacy_followup_method": lead.legacy_followup_method,
        "legacy_buyer_demand": lead.legacy_buyer_demand,
    }


created = linked = archived = 0
for offset in range(0, len(source_leads), BATCH_SIZE):
    leads = source_leads[offset : offset + BATCH_SIZE]
    missing = leads.filtered(lambda lead: lead.legacy_import_key not in existing_partners)
    if missing:
        partners = Partner.create([partner_values(lead) for lead in missing])
        existing_partners.update(
            {
                partner.legacy_import_key: partner
                for partner in partners
            }
        )
        created += len(partners)
    for lead in leads:
        partner = existing_partners[lead.legacy_import_key]
        if lead.partner_id != partner:
            lead.partner_id = partner
            linked += 1
    active_source_leads = leads.filtered("active")
    if active_source_leads:
        active_source_leads.write({"active": False})
        archived += len(active_source_leads)
    env.cr.commit()
    print(f"Processed {min(offset + BATCH_SIZE, len(source_leads))}/{len(source_leads)}")

partner_total = Partner.search_count(
    [("legacy_import_key", "like", f"{IMPORT_PREFIX}:%")]
)
active_source_total = Lead.search_count(
    [
        ("legacy_import_key", "like", f"{IMPORT_PREFIX}:%"),
        ("type", "=", "lead"),
        ("active", "=", True),
    ]
)
print(
    "MIGRATION_RESULT "
    f"created={created} linked={linked} archived={archived} "
    f"partners={partner_total} active_source_leads={active_source_total}"
)
