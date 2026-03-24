# Copyright 2023 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestCrmProjectTask(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.user.company_id
        cls.company_2 = cls.env["res.company"].create({"name": "Second Company"})
        cls.user_salesman = mail_new_test_user(
            cls.env,
            login="user_test",
            name="User Test",
            email="user_test@test.example.com",
            company_id=cls.company.id,
            groups="sales_team.group_sale_salesman",
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner Test",
            }
        )
        cls.lead = cls.env["crm.lead"].create(
            {
                "name": "Test Lead",
                "type": "lead",
                "partner_id": cls.partner.id,
                "user_id": cls.user_salesman.id,
            }
        )
        cls.lead_2 = cls.env["crm.lead"].create(
            {
                "name": "Other Lead",
                "type": "lead",
                "company_id": cls.company_2.id,
            }
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Project",
                "description": "Test Description",
            }
        )
        cls.project_2 = cls.env["project.project"].create(
            {
                "name": "Second Project",
                "description": "Second Description",
            }
        )
        cls.company.crm_default_project_id = cls.project

    def test_action_create_task_with_project_task_create(self):
        """Users with Project / User get the direct task form action."""
        action = self.lead.action_create_task()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "project.task")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["context"]["default_name"], self.lead.name)
        self.assertEqual(action["context"]["default_lead_id"], self.lead.id)
        self.assertEqual(action["context"]["default_project_id"], self.project.id)
        self.assertEqual(action["context"]["default_partner_id"], self.partner.id)
        self.assertEqual(
            action["context"]["default_user_ids"],
            [fields.Command.set(self.user_salesman.ids)],
        )
        self.assertNotIn("crm_project_task_sudo", action["context"])

    def test_action_create_task_without_project_task_create_opens_wizard(self):
        """Users without Project / User get the wizard
        (native task form needs project rights)."""
        action = self.lead.with_user(self.user_salesman).action_create_task()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "crm.create.task")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action.get("target"), "new")
        self.assertEqual(action["context"]["default_lead_id"], self.lead.id)
        self.assertEqual(action["context"]["default_name"], self.lead.name)

    def test_wizard_create_task_creates_linked_task(self):
        wizard = (
            self.env["crm.create.task"]
            .with_user(self.user_salesman)
            .create(
                {
                    "lead_id": self.lead.id,
                    "task_name": "Wizard Task",
                    "description": "<p>Desc</p>",
                }
            )
        )
        wizard.create_task()

        task = self.env["project.task"].search(
            [("lead_id", "=", self.lead.id), ("name", "=", "Wizard Task")]
        )
        self.assertEqual(len(task), 1)
        self.assertEqual(task.project_id, self.project)
        self.assertEqual(task.partner_id, self.partner)
        self.assertEqual(task.description, "<p>Desc</p>")

    def test_wizard_create_task_unsubscribes_only_creator(self):
        private_project = self.env["project.project"].create(
            {
                "name": "Private CRM Project",
                "privacy_visibility": "followers",
            }
        )
        self.company.crm_default_project_id = private_project
        other_follower = self.env["res.partner"].create({"name": "Other Follower"})
        wizard = (
            self.env["crm.create.task"]
            .with_user(self.user_salesman)
            .create(
                {
                    "lead_id": self.lead.id,
                    "task_name": "Private Wizard Task",
                }
            )
        )
        wizard.create_task()
        task = self.env["project.task"].search(
            [("lead_id", "=", self.lead.id), ("name", "=", "Private Wizard Task")]
        )
        task.message_subscribe(other_follower.ids)
        self.assertNotIn(self.user_salesman.partner_id, task.message_partner_ids)
        self.assertIn(other_follower, task.message_partner_ids)
        with self.assertRaises(AccessError):
            task.with_user(self.user_salesman).read(["name"])

    def test_wizard_create_task_raises_without_default_project(self):
        self.company.crm_default_project_id = False
        wizard = self.env["crm.create.task"].create(
            {
                "lead_id": self.lead.id,
                "task_name": "No Project",
            }
        )
        with self.assertRaises(UserError):
            wizard.create_task()

    def test_get_default_context_uses_lead_company_project(self):
        self.company_2.crm_default_project_id = self.project_2

        context = self.lead_2._get_default_context()

        self.assertEqual(context["default_name"], self.lead_2.name)
        self.assertEqual(context["default_lead_id"], self.lead_2.id)
        self.assertEqual(context["default_project_id"], self.project_2.id)
        self.assertEqual(context["default_partner_id"], self.lead_2.partner_id.id)
        self.assertEqual(
            context["default_user_ids"], [fields.Command.set(self.lead_2.user_id.ids)]
        )
        self.assertNotIn("crm_project_task_sudo", context)

    def test_action_view_tasks(self):
        task = self.env["project.task"].create(
            {
                "name": "Task Test",
                "lead_id": self.lead.id,
                "project_id": self.project.id,
            }
        )

        action = self.lead.action_view_tasks()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "project.task")
        self.assertEqual(action["context"]["search_default_open_tasks"], 1)
        self.assertEqual(action["context"]["default_lead_id"], self.lead.id)
        self.assertEqual(action["context"]["default_project_id"], self.project.id)
        self.assertEqual(action["context"]["default_partner_id"], self.partner.id)
        self.assertNotIn("create", action["context"])
        self.assertEqual(
            list(action["domain"]),
            [("lead_id", "=", self.lead.id)],
            "The base module returns only the lead_id domain.",
        )

        tasks = self.env["project.task"].search(action["domain"])
        self.assertEqual(tasks, self.lead.task_ids)
        self.assertIn(task, tasks)

    def test_action_view_tasks_disables_create_without_project_rights(self):
        """Users without Project / User must not see New on related task views."""
        self.env["project.task"].create(
            {
                "name": "Task Test",
                "lead_id": self.lead.id,
                "project_id": self.project.id,
            }
        )

        action = self.lead.with_user(self.user_salesman).action_view_tasks()

        self.assertFalse(action["context"]["create"])

    def test_task_count_computed_from_related_tasks(self):
        self.assertEqual(self.lead.task_count, 0)
        self.env["project.task"].create(
            {"name": "Task 1", "lead_id": self.lead.id, "project_id": self.project.id}
        )
        self.env["project.task"].create(
            {"name": "Task 2", "lead_id": self.lead.id, "project_id": self.project.id}
        )
        self.lead.invalidate_recordset(["task_ids", "task_count"])
        self.assertEqual(self.lead.task_count, 2)

    def test_project_task_get_sudo_env_always_sudo(self):
        task_model = self.env["project.task"].with_user(self.user_salesman)
        returned_model = task_model._get_sudo_env_with_context()
        self.assertTrue(returned_model.env.su)
        self.assertEqual(returned_model.env.uid, self.user_salesman.id)

    def test_project_task_get_sudo_env_merges_default_context(self):
        task_model = (
            self.env["project.task"]
            .with_user(self.user_salesman)
            .with_context(
                default_name="Preserved task",
                default_project_id=self.project.id,
                custom_context_key="extra",
            )
        )
        sudo_task_model = task_model._get_sudo_env_with_context()

        self.assertTrue(sudo_task_model.env.su)
        self.assertEqual(
            sudo_task_model.env.context.get("default_name"), "Preserved task"
        )
        self.assertEqual(
            sudo_task_model.env.context.get("default_project_id"), self.project.id
        )
        self.assertEqual(
            sudo_task_model.env.context.get("custom_context_key"),
            "extra",
        )

    def test_project_task_default_get_uses_sudo_when_default_lead_id(self):
        defaults = (
            self.env["project.task"]
            .with_user(self.user_salesman)
            .with_context(
                default_lead_id=self.lead.id,
                default_name="Preserved task",
                default_project_id=self.project.id,
                default_partner_id=self.partner.id,
            )
            .default_get(["name", "project_id", "partner_id"])
        )

        self.assertEqual(defaults["name"], "Preserved task")
        self.assertEqual(defaults["project_id"], self.project.id)
        self.assertEqual(defaults["partner_id"], self.partner.id)

    def test_project_task_default_get_without_lead_id_context(self):
        defaults = (
            self.env["project.task"]
            .with_user(self.user_salesman)
            .with_context(
                default_name="Regular context task",
                default_project_id=self.project.id,
            )
            .default_get(["name", "project_id"])
        )
        self.assertEqual(defaults["name"], "Regular context task")
        self.assertEqual(defaults["project_id"], self.project.id)

    def test_merge_get_fields_specific_keeps_tasks_linked(self):
        task_1 = self.env["project.task"].create(
            {
                "name": "Merge Task 1",
                "lead_id": self.lead.id,
                "project_id": self.project.id,
            }
        )
        task_2 = self.env["project.task"].create(
            {
                "name": "Merge Task 2",
                "lead_id": self.lead.id,
                "project_id": self.project.id,
            }
        )
        fields_info = self.lead._merge_get_fields_specific()
        self.assertIn("task_ids", fields_info)

        task_commands = fields_info["task_ids"]("task_ids", self.lead)
        linked_ids = {command[1] for command in task_commands if command[0] == 4}
        self.assertSetEqual(linked_ids, {task_1.id, task_2.id})

    def test_res_config_settings_related_default_project(self):
        self.company.crm_default_project_id = self.project
        settings = self.env["res.config.settings"].create(
            {"company_id": self.company.id}
        )
        self.assertEqual(settings.crm_default_project_id, self.project)

        settings.crm_default_project_id = self.project_2
        self.assertEqual(self.company.crm_default_project_id, self.project_2)
