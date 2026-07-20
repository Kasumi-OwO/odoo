"""Import the prepared Wutong CRM CSV from an Odoo shell.

Usage::

    LEGACY_CRM_CSV=/path/customers.csv \
      .venv/bin/python odoo-bin shell -c odoo.conf -d Odoo \
      < addons/factory_crm_followup/scripts/import_legacy_customers.py

The source row is the identity.  Names and phone numbers are deliberately not
used for deduplication because valid duplicates exist in the source workbook.
"""

import csv
import os


EXPECTED_HEADERS = [
    "source_row",
    "买家昵称",
    "收货地址电话",
    "买家身份",
    "买家等级",
    "所在地-省份",
    "所在地-城市",
    "首次采购日期",
    "最近采购日期",
    "距上次采购（天）",
    "采购次数",
    "累计采购金额（元）",
    "首单是否广告引导",
    "联系名称",
    "联系方式",
    "重要等级",
    "跟进方式",
    "买家需求",
]
IMPORT_PREFIX = "wutong-crm-2011-2024"
BATCH_SIZE = 500


def integer(value):
    return int(value) if value else 0


def amount(value):
    return float(value) if value else 0.0


def values_from_row(row):
    nickname = row["买家昵称"].strip()
    contact_name = row["联系名称"].strip()
    identity = row["买家身份"].strip()
    customer_type = {
        "实体店/摊主": "wholesaler",
        "国内电商": "ecommerce",
        "跨境电商": "ecommerce",
        "微商": "ecommerce",
    }.get(identity, False)
    purchase_count = integer(row["采购次数"])
    source_row = integer(row["source_row"])
    return {
        "name": nickname or f"历史客户（源表第 {source_row} 行）",
        "type": "lead",
        "user_id": False,
        "contact_name": contact_name or nickname or False,
        "phone": row["收货地址电话"].strip() or False,
        "city": row["所在地-城市"].strip() or False,
        "customer_type": customer_type,
        "is_repeat_customer": purchase_count > 1,
        "legacy_import_key": f"{IMPORT_PREFIX}:{source_row}",
        "legacy_buyer_nickname": nickname or False,
        "legacy_shipping_phone": row["收货地址电话"].strip() or False,
        "legacy_buyer_identity": identity or False,
        "legacy_buyer_level": row["买家等级"].strip() or False,
        "legacy_province": row["所在地-省份"].strip() or False,
        "legacy_city": row["所在地-城市"].strip() or False,
        "legacy_first_purchase_date": row["首次采购日期"].strip() or False,
        "legacy_latest_purchase_date": row["最近采购日期"].strip() or False,
        "legacy_days_since_purchase": integer(row["距上次采购（天）"]),
        "legacy_purchase_count": purchase_count,
        "legacy_total_purchase_amount": amount(row["累计采购金额（元）"]),
        "legacy_first_order_ad_driven": row["首单是否广告引导"].strip() == "是",
        "legacy_contact_name": contact_name or False,
        "legacy_contact_details": row["联系方式"].strip() or False,
        "legacy_importance_level": row["重要等级"].strip() or False,
        "legacy_followup_method": row["跟进方式"].strip() or False,
        "legacy_buyer_demand": row["买家需求"].strip() or False,
    }


csv_path = os.environ.get("LEGACY_CRM_CSV")
if not csv_path:
    raise RuntimeError("LEGACY_CRM_CSV must point to the prepared UTF-8 CSV file")

Lead = env["crm.lead"].with_context(mail_create_nosubscribe=True, tracking_disable=True)
created = skipped = 0
batch = []
with open(csv_path, encoding="utf-8-sig", newline="") as source:
    reader = csv.DictReader(source)
    if reader.fieldnames != EXPECTED_HEADERS:
        raise RuntimeError(f"Unexpected CSV headers: {reader.fieldnames!r}")
    existing = set(
        Lead.search([("legacy_import_key", "like", f"{IMPORT_PREFIX}:%")]).mapped(
            "legacy_import_key"
        )
    )
    for row in reader:
        vals = values_from_row(row)
        if vals["legacy_import_key"] in existing:
            skipped += 1
            continue
        batch.append(vals)
        if len(batch) >= BATCH_SIZE:
            Lead.create(batch)
            env.cr.commit()
            created += len(batch)
            print(f"Imported {created} records")
            batch = []
    if batch:
        Lead.create(batch)
        env.cr.commit()
        created += len(batch)

total = Lead.search_count([("legacy_import_key", "like", f"{IMPORT_PREFIX}:%")])
print(f"IMPORT_RESULT created={created} skipped={skipped} total={total}")
