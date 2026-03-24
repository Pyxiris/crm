# Copyright 2023 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields, models
from odoo.exceptions import UserError


class CrmCreateTAsk(models.TransientModel):
    _name = "crm.create.task"
    _description = "Wizard to create task"

    lead_id = fields.Many2one("crm.lead")
    task_name = fields.Char()
    description = fields.Html()

    def create_task(self):
        project = self.env.company.crm_default_project_id
        if not project:
            raise UserError(
                self.env._(
                    "Project not configured in settings, "
                    "please contact with your administrator."
                )
            )
        # Create task
        self.env["project.task"].sudo().create(self._get_data_create(project))

    def _get_data_create(self, project):
        """Get dict to create task"""
        return {
            "name": self.task_name,
            "project_id": project.id,
            "partner_id": self.lead_id.partner_id.id,
            "lead_id": self.lead_id.id,
            "description": self.description,
            "user_ids": [(6, 0, [])],
        }
