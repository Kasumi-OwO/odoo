{
    "name": "Factory CRM Follow-up",
    "version": "19.5.1.2.0",
    "category": "Sales/CRM",
    "summary": "Customer grading, traceable follow-ups and factory sales reminders",
    "author": "Kasumi",
    "depends": ["crm"],
    "data": [
        "security/ir.access.csv",
        "data/crm_stage_data.xml",
        "data/ir_cron_data.xml",
        "views/factory_crm_followup_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
    ],
    "application": False,
    "installable": True,
    "license": "LGPL-3",
}
