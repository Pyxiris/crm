# Copyright 2023 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    task_ids = fields.One2many("project.task", "lead_id")
    task_count = fields.Integer("#Task", compute="_compute_task_count")

    @api.depends("task_ids")
    def _compute_task_count(self):
        for lead in self:
            lead.task_count = len(lead.task_ids)

    def action_tasks(self):
        self.ensure_one()
        action = self.env.ref("project.action_view_task").sudo().read()[0]
        action.update(
            {
                "domain": [("lead_id", "=", self.id)],
                "context": {
                    **self.env.context,
                    "default_lead_id": self.id,
                    "default_name": self.name,
                    "default_project_id": self.env.company.crm_default_project_id.id,
                    "default_partner_id": self.partner_id.id,
                    "default_user_ids": [fields.Command.set(self.user_id.ids)],
                },
            }
        )
        return action
