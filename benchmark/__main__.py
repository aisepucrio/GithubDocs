"""
Ponto de entrada do módulo de benchmark.

Uso:
    python -m benchmark "1-20"        # Testa configs 1 a 20
    python -m benchmark "1,4,7"       # Testa configs 1, 4 e 7
    python -m benchmark "1-5,10,15"   # Testa configs 1-5, 10 e 15
    python -m benchmark "all"         # Testa todos os configs

    # Com opções:
    python -m benchmark "1-10" --no-sheets    # Sem exportar para Sheets
    python -m benchmark "1-10" --quiet        # Sem output verboso
    python -m benchmark "1-10" --list         # Lista configs disponíveis
"""

import argparse
import sys
import os

from dotenv import load_dotenv

from .test_configs import TEST_CONFIGS, get_config_name, get_total_configs
from .index_parser import parse_indices, format_indices_summary
from .runner import BenchmarkRunner


def list_configs():
    """Lista todas as configs disponíveis."""
    total = get_total_configs()
    print(f"\nConfigs disponíveis: {total}\n")
    print("-" * 60)

    for i in range(total):
        name = get_config_name(i)
        print(f"  {i+1:3d}. {name}")

    print("-" * 60)
    print(f"\nUso: python -m benchmark \"1-{total}\" para testar todas")
    print(f"     python -m benchmark \"1,2,3\" para testar específicas\n")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Benchmark tool para GithubDocs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
    python -m benchmark "1-20"        Testa configs 1 a 20
    python -m benchmark "1,4,7"       Testa configs 1, 4 e 7
    python -m benchmark "1-5,10"      Testa configs 1-5 e 10
    python -m benchmark "all"         Testa todos
    python -m benchmark --list        Lista configs disponíveis
        """,
    )

    parser.add_argument(
        "indices",
        nargs="?",
        default=None,
        help='Índices para testar (ex: "1-20", "1,4,7", "all")',
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Lista configs disponíveis",
    )

    parser.add_argument(
        "--no-sheets",
        action="store_true",
        help="Não exporta para Google Sheets",
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Modo silencioso (menos output)",
    )

    parser.add_argument(
        "--worksheet", "-w",
        type=str,
        default=None,
        help="Nome da worksheet no Google Sheets",
    )

    parser.add_argument(
        "--credentials", "-c",
        type=str,
        default=None,
        help="Caminho para credenciais do Google Sheets",
    )

    parser.add_argument(
        "--spreadsheet", "-s",
        type=str,
        default=None,
        help="ID da planilha Google Sheets",
    )

    args = parser.parse_args()

    if args.list:
        list_configs()
        return 0

    if args.indices is None:
        parser.print_help()
        print("\nErro: Especifique os índices ou use --list para ver configs disponíveis")
        return 1

    total_configs = get_total_configs()

    if total_configs == 0:
        print("Erro: Nenhuma config definida em benchmark/test_configs.py")
        print("Adicione suas configs TOML no array TEST_CONFIGS")
        return 1

    try:
        indices = parse_indices(args.indices, total_configs)
    except ValueError as e:
        print(f"Erro ao parsear índices: {e}")
        return 1

    if not indices:
        print("Erro: Nenhum índice válido selecionado")
        return 1

    print(f"\nBenchmark GithubDocs")
    print(f"=" * 60)
    print(f"Configs selecionadas: {format_indices_summary(indices)}")
    print(f"Total: {len(indices)} de {total_configs} disponíveis")

    runner = BenchmarkRunner(verbose=not args.quiet)
    results = runner.run_batch(indices)

    if not args.no_sheets:
        try:
            from .sheets_exporter import export_to_sheets

            print(f"\n{'='*60}")
            print("Exportando para Google Sheets...")

            url = export_to_sheets(
                results=runner.get_results_as_dicts(),
                credentials_path=args.credentials,
                spreadsheet_id=args.spreadsheet,
                worksheet_name=args.worksheet,
            )

            print(f"Planilha: {url}")

        except ImportError as e:
            print(f"\nAviso: Não foi possível exportar para Sheets: {e}")
            print("Instale as dependências: pip install gspread google-auth")

        except Exception as e:
            print(f"\nErro ao exportar para Sheets: {e}")
            print("Verifique as credenciais e o ID da planilha")

    success_count = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"RESULTADO FINAL: {success_count}/{len(results)} testes passaram")
    print(f"{'='*60}\n")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
