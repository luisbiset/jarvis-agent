import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from aghuse_assistant.agents import select
from aghuse_assistant.api import RunService
from aghuse_assistant.policy import can_execute
from aghuse_assistant.runtime import RunStatus


class ArchitectureCoreTests(unittest.TestCase):
    def test_runs_are_independent_and_have_technical_states(self):
        service = RunService()
        run = service.create({"project": "aghuse", "operation": "ANALYZE", "objective": "investigar"})
        self.assertEqual(run["status"], RunStatus.CREATED)
        self.assertEqual(set(RunStatus), {RunStatus.CREATED, RunStatus.RUNNING, RunStatus.WAITING_INPUT, RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED})

    def test_policy_denies_mutation_outside_implement(self):
        self.assertFalse(can_execute("ANALYZE", "edit_files"))
        self.assertTrue(can_execute("IMPLEMENT", "edit_files"))

    def test_agents_are_selected_by_capability(self):
        self.assertEqual({agent.name for agent in select("VALIDATE")}, {"backend", "database", "frontend", "qa", "architecture"})

    def test_maintenance_is_assigned_only_to_assistant_agent(self):
        self.assertEqual({agent.name for agent in select("MANUTENCAO")}, {"aghuse_assistant"})
        self.assertTrue(can_execute("MANUTENCAO", "edit_files"))
