from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from rag.chunkers import chunk_text
from rag.indexer import RagIndex
from rag.retriever import retrieve, load_reranker
from rag.security import safe_text
from rag.taxonomy import classify
from rag.semantic import cosine

ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    spec = importlib.util.spec_from_file_location("jarvis_runtime_rag_test", ROOT / "scripts/jarvis_runtime.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


RUNTIME = load_runtime()


class RagTest(unittest.TestCase):
    def policy(self) -> dict:
        return json.loads((ROOT / "contracts/rag-policy.json").read_text(encoding="utf-8"))

    def test_java_chunking_preserves_symbol_and_lines(self):
        chunks = chunk_text("src/Foo.java", "public class Foo {\n  public int calcularTotal() {\n    return 1;\n  }\n}\n")
        self.assertEqual([chunk.symbol for chunk in chunks], ["Foo", "calcularTotal"])
        self.assertEqual(chunks[1].start_line, 2)
        self.assertEqual(chunks[1].end_line, 5)

    def test_incremental_index_skips_unchanged_and_invalidates_one_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            (root / "Foo.java").write_text("public class Foo {}\n", encoding="utf-8")
            (root / "README.md").write_text("# Regra\nAgrupamento APAC\n", encoding="utf-8")
            with RagIndex(Path(temporary) / "index.db") as index:
                first = index.index_repo(root)
                second = index.index_repo(root)
                (root / "Foo.java").write_text("public class Foo { public int total; }\n", encoding="utf-8")
                third = index.index_repo(root)
                self.assertEqual(first["indexed"], 2)
                self.assertEqual(second["unchanged"], 2)
                self.assertEqual(third["indexed"], 1)
                self.assertEqual(third["unchanged"], 1)

    def test_index_provenance_reindexes_when_revision_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            source = root / "Foo.java"; source.write_text("public class Foo {}\n", encoding="utf-8")
            with RagIndex(Path(temporary) / "index.db") as index:
                first = index.index_repo(root)
                original = __import__("rag.indexer", fromlist=["git_revision", "git_branch"])
                old_revision, old_branch = original.git_revision, original.git_branch
                try:
                    original.git_revision = lambda _root: "commit-2"
                    original.git_branch = lambda _root: "feature-x"
                    second = index.index_repo(root)
                    row = index.connection.execute("SELECT git_commit,git_branch FROM documents WHERE path='Foo.java'").fetchone()
                    self.assertEqual(first["indexed"], 1)
                    self.assertEqual(second["indexed"], 1)
                    self.assertEqual((row["git_commit"], row["git_branch"]), ("commit-2", "feature-x"))
                finally:
                    original.git_revision, original.git_branch = old_revision, old_branch

    def test_removed_and_sensitive_files_do_not_leave_active_chunks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            source = root / "Foo.java"; source.write_text("public class Foo {}\n", encoding="utf-8")
            with RagIndex(Path(temporary) / "index.db") as index:
                index.index_repo(root)
                source.write_text('password="segredo-real"\n', encoding="utf-8")  # secret-scan: allow-test-fixture
                result = index.index_repo(root)
                self.assertEqual(result["refused"], 1)
                self.assertEqual(index.status()["chunks"], 0)

    def test_exact_symbol_is_retrieved_with_provenance_and_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            (root / "FatItemEspelhoContaApacDAO.java").write_text("public class FatItemEspelhoContaApacDAO {\n public void agruparProfissionais() {}\n}\n", encoding="utf-8")
            database = Path(temporary) / "index.db"
            with RagIndex(database) as index:
                index.index_repo(root)
            payload = retrieve(database, "FatItemEspelhoContaApacDAO agrupamento APAC", self.policy(), "SMALL")
            self.assertTrue(payload["hits"])
            self.assertEqual(payload["hits"][0]["path"], "FatItemEspelhoContaApacDAO.java")
            self.assertEqual(len(payload["hits"][0]["content_hash"]), 64)
            self.assertLessEqual(payload["estimated_tokens"], 3000)
            self.assertEqual(payload["retrieval_mode"], "LEXICAL_ONLY")
            self.assertEqual(payload["hits"][0]["taxonomy"]["artifact"], "codigo")
            self.assertIn("query_term_in_symbol", payload["hits"][0]["match_reasons"])
            self.assertEqual(payload["hits"][0]["selection_reason"], "selected_by_ranked_relevance")

    def test_runtime_writes_rag_context_without_counting_model_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); repo = base / "repo"; repo.mkdir()
            (repo / "README.md").write_text("# Evidência\nagrupamento profissionais APAC\n", encoding="utf-8")
            database = base / "index.db"
            with RagIndex(database) as index:
                index.index_repo(repo)
            initialized = RUNTIME.initialize(argparse.Namespace(
                task_id="RAG-TEST", complexity="LOCALIZED", risk_class="LOW", operational_mode="COPILOT",
                reasoning_class=None, budget_justification=None, agents_planned=[], runs_dir=base / "runs", telemetry_db=base / "telemetry.db",
                task_type="GENERAL", estimated_files=2, estimated_modules=1, architectural=False, production_critical=False,
                database_migration=False, security_sensitive=False, tests_required=True, ambiguity_score=0, complexity_score=2,
            ))
            result = RUNTIME.rag_retrieve(argparse.Namespace(run_dir=initialized["run_dir"], query="agrupamento APAC", database=database, path_filter=None, domain=None, agent=None))
            state = json.loads((Path(initialized["run_dir"]) / "state.json").read_text(encoding="utf-8"))
            pack = json.loads(Path(result["context_pack"]).read_text(encoding="utf-8"))
            self.assertEqual(state["budget"]["model_calls_used"], 0)
            self.assertEqual(state["rag"]["queries"], 1)
            self.assertEqual(pack["query_hash"], __import__("hashlib").sha256(b"agrupamento APAC").hexdigest())
            cached = RUNTIME.rag_retrieve(argparse.Namespace(run_dir=initialized["run_dir"], query="agrupamento APAC", database=database, path_filter=None, domain=None, agent=None))
            state = json.loads((Path(initialized["run_dir"]) / "state.json").read_text(encoding="utf-8"))
            dashboard = RUNTIME.dashboard(argparse.Namespace(runs_dir=base / "runs", telemetry_db=base / "telemetry.db"))
            self.assertTrue(cached["cache_hit"])
            self.assertEqual(state["rag"]["cache_hits"], 1)
            self.assertEqual(dashboard["rag"]["queries_count"], 1)
            self.assertGreaterEqual(dashboard["rag"]["selected_chunks"], 1)

    def test_security_filter_rejects_credentials(self):
        self.assertFalse(safe_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz"))
        self.assertTrue(safe_text("A variável REDMINE_API_KEY não deve ser exibida"))


    def test_taxonomy_classifies_aghuse_layers(self):
        self.assertEqual(classify("src/main/java/ContaON.java", "public class ContaON {}", "CODE")["layer"], "backend")
        self.assertEqual(classify("src/main/webapp/conta.xhtml", "<p:inputText/>", "CODE")["layer"], "frontend")
        self.assertEqual(classify("src/test/ContaONTest.java", "class ContaONTest {}", "TEST")["layer"], "testes")

    def test_taxonomy_classifies_aghuse_components(self):
        cases = {
            "ContaON.java": ("ON", "public class ContaON {}"),
            "ContaEJB.java": ("EJB", "@Stateless public class ContaEJB {}"),
            "ContaRN.java": ("RN", "public class ContaRN {}"),
            "ContaFacade.java": ("Facade", "public class ContaFacade {}"),
            "ContaDAO.java": ("DAO", "public class ContaDAO {}"),
            "ContaEntity.java": ("Entity", "@Entity class ContaEntity {}"),
            "ContaController.java": ("Controller", "class ContaController {}"),
            "ContaService.java": ("Service", "class ContaService {}"),
            "ContaTest.java": ("Test", "class ContaTest {}"),
            "schema.sql": ("SQL", "select 1"),
            "SecurityConfig.java": ("Security", "class SecurityConfig {}"),
            "Messages.properties": ("Message", "menu.label=Conta"),
            "application.yml": ("Configuration", "server:\n  port: 8080"),
            "conta.xhtml": ("XHTML", "<h:form/>")
        }
        for path, (expected, text) in cases.items():
            with self.subTest(path=path):
                result = classify(path, text, "CODE")
                self.assertIn(expected, result["categories"])
                self.assertEqual(result["category"], expected)
        documentation = classify("README.md", "Security e configuration são conceitos documentados.", "CODE")
        self.assertNotIn("ON", documentation["categories"])
        self.assertNotIn("Security", documentation["categories"])
        self.assertNotIn("Configuration", documentation["categories"])

    def test_taxonomy_filter_restricts_search(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            (root / "ContaON.java").write_text("public class ContaON { void calcular() {} }\n", encoding="utf-8")
            (root / "conta.xhtml").write_text("<html>calcular</html>\n", encoding="utf-8")
            database = Path(temporary) / "index.db"
            with RagIndex(database) as index:
                index.index_repo(root)
                from rag.retriever import search
                hits = search(index, "calcular", 10, taxonomy={"layer": "backend"})
                self.assertTrue(hits)
                self.assertTrue(all(".java" in hit.path for hit in hits))

    def test_taxonomy_category_filter_restricts_search(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            (root / "ContaON.java").write_text("public class ContaON {}\n", encoding="utf-8")
            (root / "conta.xhtml").write_text("<html/>\n", encoding="utf-8")
            database = Path(temporary) / "index.db"
            with RagIndex(database) as index:
                index.index_repo(root)
                from rag.retriever import search
                hits = search(index, "ContaON", 10, taxonomy={"category": "ON"})
                self.assertEqual([hit.path for hit in hits], ["ContaON.java"])

    def test_optional_reranker_changes_reported_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"; root.mkdir()
            (root / "ContaON.java").write_text("public class ContaON { void calcular() {} }\n", encoding="utf-8")
            database = Path(temporary) / "index.db"
            model = Path(temporary) / "reranker.json"
            model.write_text(json.dumps({"schema_version":"1.0.0", "method":"term_log_odds", "weights":{"symbol:contaon":2.0}}), encoding="utf-8")
            with RagIndex(database) as index: index.index_repo(root)
            payload = retrieve(database, "ContaON", self.policy(), "SMALL", reranker_path=model)
            self.assertEqual(payload["retrieval_mode"], "LEXICAL_RERANKED")
            self.assertTrue(load_reranker(model))

    def test_local_semantic_similarity_is_deterministic(self):
        self.assertGreater(cosine("regra de cálculo da conta", "calculo conta regra"), 0.5)
        self.assertEqual(cosine("abc", "xyz"), 0.0)

    def test_runtime_uses_default_reranker_when_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); repo = base / "repo"; repo.mkdir()
            (repo / "ContaON.java").write_text("public class ContaON { void calcular() {} }\n", encoding="utf-8")
            database = base / "index.db"
            model = base / "reranker.json"
            model.write_text(json.dumps({"schema_version":"1.0.0", "method":"term_log_odds", "weights":{}}), encoding="utf-8")
            with RagIndex(database) as index: index.index_repo(repo)
            initialized = RUNTIME.initialize(argparse.Namespace(task_id="RAG-RERANK", complexity="LOCALIZED", risk_class="LOW", operational_mode="COPILOT", reasoning_class=None, budget_justification=None, agents_planned=[], runs_dir=base / "runs", telemetry_db=base / "telemetry.db", task_type="GENERAL", estimated_files=1, estimated_modules=1, architectural=False, production_critical=False, database_migration=False, security_sensitive=False, tests_required=True, ambiguity_score=0, complexity_score=2))
            previous = RUNTIME.DEFAULT_RAG_RERANKER; RUNTIME.DEFAULT_RAG_RERANKER = model
            try:
                result = RUNTIME.rag_retrieve(argparse.Namespace(run_dir=initialized["run_dir"], query="ContaON", database=database, path_filter=None, domain=None, agent=None, taxonomy=None))
                self.assertEqual(result["retrieval_mode"], "LEXICAL_RERANKED")
            finally:
                RUNTIME.DEFAULT_RAG_RERANKER = previous

if __name__ == "__main__":
    unittest.main()
