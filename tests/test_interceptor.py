from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.jarvis_interceptor import intercept, is_technical, task_ids


class InterceptorTest(unittest.TestCase):
    def test_classifies_technical_messages_and_extracts_task(self):
        self.assertTrue(is_technical("corrigir o DAO da tarefa 55968"))
        self.assertEqual(task_ids("corrigir tarefa 55968 e #55969"), [55968, 55969])

    def test_non_technical_message_does_not_require_rag(self):
        with tempfile.TemporaryDirectory() as directory:
            result = intercept("olá", database=Path(directory) / "missing.db", policy=Path("contracts/rag-policy.json"))
        self.assertFalse(result["required"])
        self.assertEqual(result["reason"], "non_technical_message")

    def test_missing_index_blocks_technical_message(self):
        with tempfile.TemporaryDirectory() as directory:
            result = intercept("implementar teste no DAO", database=Path(directory) / "missing.db", policy=Path("contracts/rag-policy.json"))
        self.assertTrue(result["required"])
        self.assertTrue(result["blocked"])
        self.assertEqual(result["reason"], "rag_index_not_found")

    def test_explicit_bypass_is_auditable(self):
        with tempfile.TemporaryDirectory() as directory:
            result = intercept("implementar teste no DAO", database=Path(directory) / "missing.db", policy=Path("contracts/rag-policy.json"), bypass="índice ainda não provisionado")
        self.assertTrue(result["bypassed"])
        self.assertFalse(result["blocked"])
        self.assertTrue(result["message_hash"])


if __name__ == "__main__":
    unittest.main()
