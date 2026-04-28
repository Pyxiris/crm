# Copyright 2023 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    lead_id = fields.Many2one("crm.lead")

    @api.model
    def _get_sudo_env_with_context(self):
        """Helper to create a sudo environment preserving default_ context keys."""
        if not self.env.context.get("crm_project_task_sudo"):
            return self

        original_context = self.env.context
        sudo_self = self.sudo()

        # Filter and re-inject default_ keys into the sudo'd environment's context
        default_context_keys = {
            k: v for k, v in original_context.items() if k.startswith("default_")
        }
        return sudo_self.with_context(**default_context_keys)

    @api.model
    def default_get(self, fields):
        # We use sudo to get defaults because the user may not actually have
        # permission to read them
        self = self._get_sudo_env_with_context()
        return super().default_get(fields)

    def action_open_parent_lead(self):
        return {
            "name": self.env._("Parent Lead"),
            "view_mode": "form",
            "res_model": "crm.lead",
            "res_id": self.lead_id.id,
            "type": "ir.actions.act_window",
            "context": self.env.context,
        }
