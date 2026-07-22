from odoo import _, api, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _factory_email_auth_disabled(self):
        return self.env["ir.config_parameter"].sudo().get_bool(
            "factory_crm_followup.no_email_user_management", default=True
        )

    @api.model_create_multi
    def create(self, vals_list):
        recordset = self
        if self._factory_email_auth_disabled():
            recordset = self.with_context(no_reset_password=True)
        users = super(ResUsers, recordset).create(vals_list)
        if self._factory_email_auth_disabled():
            internal_users = users.filtered(lambda user: not user.share)
            if internal_users:
                internal_users.write({"notification_type": "inbox"})
        return users

    def action_reset_password(self):
        if self._factory_email_auth_disabled():
            raise UserError(
                _(
                    "Email invitations and password reset are disabled. "
                    "Open the user's Security tab and use Change password instead."
                )
            )
        return super().action_reset_password()
