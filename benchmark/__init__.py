"""
Benchmark Module - Ferramenta de testes e benchmark para GithubDocs

Este módulo é COMPLETAMENTE SEPARADO do framework principal.
Permite testar múltiplos configs de uma linha do sheets e exportar os resultados pro google sheets.

Uso:
    python -m benchmark "1-20"      # Testa configs 1 a 20
    python -m benchmark "1,4,7"     # Testa configs 1, 4 e 7
    python -m benchmark "1-5,10,15" # Testa configs 1-5, 10 e 15
    python -m benchmark "all" # Testa todos os configs da pagina
"""

from .runner import BenchmarkRunner
from .index_parser import parse_indices
from .sheets_exporter import GoogleSheetsExporter

__all__ = ["BenchmarkRunner", "parse_indices", "GoogleSheetsExporter"]
