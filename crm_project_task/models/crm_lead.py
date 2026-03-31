# Copyright 2023 Moduon Team S.L.
# Copyright 2026 Liam Noonan
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, fields, models
from odoo.fields import Domain


class CrmLead(models.Model):
    _inherit = "crm.lead"

    task_ids = fields.One2many("project.task", "lead_id")
    task_count = fields.Integer(
        "#Task", compute_sudo=True, compute="_compute_task_count"
    )

    @api.depends("task_ids")
    def _compute_task_count(self):
        for lead in self:
            lead.task_count = len(lead.task_ids)

    def action_create_task(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm_project_task.action_new_task"
        )
        action["context"] = self._get_default_context()
        action["context"]["search_default_lead_id"] = self.id
        return action

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm_project_task.action_crm_lead_related_tasks"
        )
        ctx = self._get_default_context()
        action["context"] = {
            "search_default_open_tasks": 1,
            **ctx,
        }
        action["domain"] = Domain.AND(
            [[("lead_id", "=", self.id)], self._get_lead_task_domain()]
        )
        return action

    def _get_default_context(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        return {
            "default_name": self.name,
            "default_lead_id": self.id,
            "default_project_id": company.crm_default_project_id.id,
            "default_partner_id": self.partner_id.id,
            "default_user_ids": [fields.Command.set(self.user_id.ids)],
            "crm_project_task_sudo": True,
        }

    def _get_lead_task_domain(self):
        return []

    def _merge_get_fields_specific(self):
        fields_info = super()._merge_get_fields_specific()
        # If a res.company.crm_default_project_id in Company1 is set to a project in
        # Company2, this sudo prevents a user with access only to Company1 from
        # merging leads that have linked tasks in Company2. He will get an access error
        # if he tries. Not including the sudo would result in the tasks on the merged
        # lead to simply loose their connection to the merge target lead, which would
        # be worse.
        fields_info["task_ids"] = lambda fname, leads: [
            (4, task.id) for task in leads.sudo().mapped("task_ids")
        ]
        return fields_info
