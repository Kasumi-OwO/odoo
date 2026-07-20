# Factory CRM Follow-up

This addon extends Odoo Community CRM for a folding-chair factory sales workflow.
It is isolated from the upstream `crm` addon so it can be carried between forks and
upgraded without patching core Odoo files.

## Included in the first version

- Factory lead source, customer type, WeChat and purchase-profile fields.
- Automatic A/B/C/D grading with a manual override.
- Recommended A/B/C/D follow-up cadence of 3/7/30/0 days.
- Mandatory, non-deletable-by-salesperson follow-up records containing the
  communication, intent, concern and next action date.
- Daily reminders for overdue A/B customers, incomplete 3-day-old profiles and
  scheduled repurchase visits.
- Automatic dormant flag after 90 days without a recorded interaction.
- Factory pipeline stages and sample tracking.
- Manager-only channel, grade, conversion, sample and repeat-customer analysis.
- Native Odoo import/export and chatter attachments remain available.
- Native CRM record rules keep salespeople on their own/unassigned customers while
  sales managers retain company-wide access.
- All 17 columns from the Wutong CRM historical-customer export are preserved in a
  dedicated purchase-history page. The source row key makes repeat imports safe.

## Install or upgrade

Back up the database first, then run against the intended database:

```bash
./odoo-bin server -c odoo.conf -d DATABASE -i factory_crm_followup --stop-after-init
./odoo-bin server -c odoo.conf -d DATABASE -u factory_crm_followup --stop-after-init
```

Use `-i` for the initial installation and `-u` after deploying a newer revision.
Do not run these commands against an unidentified database.

## Historical customer import

Convert the XLSX locally, then run the generated CSV through an Odoo shell:

```bash
python addons/factory_crm_followup/scripts/prepare_legacy_customers.py SOURCE.xlsx customers.csv
LEGACY_CRM_CSV=/absolute/path/customers.csv \
  python odoo-bin shell -c odoo.conf -d DATABASE \
  < addons/factory_crm_followup/scripts/import_legacy_customers.py
```

The importer preserves duplicate names, duplicate phone numbers and contradictory
purchase dates exactly as exported. It maps nickname, phone and city to the live
CRM search fields without merging source rows.

## Intentional first-version limits

WeChat messages are planned and recorded but not sent through a WeChat API. Bulk
email is available through native CRM. Automatic reassignment when an employee is
archived and a dedicated bulk activation-plan wizard are candidates for the next
iteration.
