from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULO_PATH = Path(__file__).parents[1] / "scripts" / "aghuse_automacao.py"
SPEC = importlib.util.spec_from_file_location("aghuse_automacao", MODULO_PATH)
assert SPEC and SPEC.loader
AUTOMACAO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUTOMACAO)


class AutomacaoAghuseTest(unittest.TestCase):
    def test_extrai_tarefas_sem_confundir_numeros_menores(self):
        self.assertEqual(AUTOMACAO.extrair_tarefas("feature/51093-01", "corrige 51092"), ["51092", "51093"])

    def test_mapeia_modulos_e_tipos(self):
        resultado = AUTOMACAO.mapear_modulos(
            ["aghu-entidades/src/Entidade.java", "aghu/aghu-web/src/tela.xhtml", "README.md"]
        )
        self.assertIn("aghu-entidades", resultado["modulos"])
        self.assertIn("aghu-web", resultado["modulos"])
        self.assertTrue(resultado["possui_xhtml"])

    def test_pom_agregador_nao_vira_nome_de_modulo(self):
        self.assertEqual(AUTOMACAO.modulo_de_arquivo("aghu/pom.xml"), "aghu")

    def test_detecta_mensagem_duplicada(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivo = Path(temporario) / "mensagens.properties"
            arquivo.write_text("chave=um\nchave=dois\noutra: três\n", encoding="utf-8")
            resultado = AUTOMACAO.analisar_mensagens([arquivo])
        self.assertTrue(resultado["possui_duplicacoes"])
        self.assertEqual(resultado["arquivos"][0]["duplicadas"], ["chave"])

    def test_aponta_metadados_ausentes_no_ddl(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivo = Path(temporario) / "aplicar.sql"
            arquivo.write_text("CREATE TABLE AGH.TESTE (SEQ NUMBER);\nCOMMIT;\n", encoding="utf-8")
            resultado = AUTOMACAO.analisar_sql([arquivo])
        achados = resultado["arquivos"][0]["achados"]
        self.assertTrue(any("COMMENT ON TABLE" in achado for achado in achados))
        self.assertTrue(any("GRANT" in achado for achado in achados))
        self.assertTrue(any("COMMIT" in achado for achado in achados))

    def test_extrai_erro_de_seguranca_sem_expor_usuario(self):
        resultado = AUTOMACAO.analisar_seguranca(
            "Capturado Erro de Permissao: Usuario = TESTE, Pagina = /pages/tela.xhtml, Metodo = render"
        )
        self.assertEqual(resultado["ocorrencias"][0]["pagina"], "/pages/tela.xhtml")
        self.assertNotIn("TESTE", str(resultado))

    def test_classifica_log_oracle(self):
        resultado = AUTOMACAO.classificar_log(
            "Caused by: java.sql.SQLException: ORA-00942\n"
            "at br.gov.mec.aghu.exemplo.ExemploDAO.buscar(ExemploDAO.java:1)"
        )
        self.assertEqual(resultado["categoria"], "banco")
        self.assertEqual(resultado["codigos_oracle"], ["ORA-00942"])

    def test_manifesto_preserva_ordem_e_checksum(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivo = Path(temporario) / "01.sql"
            arquivo.write_bytes(b"select 1;\n")
            resultado = AUTOMACAO.gerar_manifesto([arquivo], "51093")
        self.assertEqual(resultado["tarefa"], "51093")
        self.assertEqual(resultado["arquivos"][0]["ordem"], 1)
        self.assertEqual(len(resultado["arquivos"][0]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
