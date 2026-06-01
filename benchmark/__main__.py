"""
Ponto de entrada do módulo de benchmark.

Uso:
    python -m benchmark "1-20"        # Testa linhas 1 a 20 do Google Sheets
    python -m benchmark "1,4,7"       # Testa linhas 1, 4 e 7
    python -m benchmark "1-5,10,15"   # Testa linhas 1-5, 10 e 15
    python -m benchmark "all"         # Testa todas as linhas

    # Com opções:
    python -m benchmark "1-10" --no-export    # Sem exportar resultados para Sheets
    python -m benchmark "1-10" --quiet        # Sem output verboso
    python -m benchmark --list                # Lista configs disponíveis
    python -m benchmark "1-10" --local        # Usa configs locais em vez do Sheets

Configuração Mínima:
    Crie um arquivo .env no diretório benchmark/ com:
        GOOGLE_SHEETS_CREDENTIALS=path/to/credentials.json
        GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
"""

import argparse
import sys
import os
from pathlib import Path

from dotenv import load_dotenv

from .test_configs import load_configs
from .index_parser import parse_indices, format_indices_summary
from .runner import BenchmarkRunner

# Carrega .env do diretório do benchmark
BENCHMARK_DIR = Path(__file__).parent.parent.resolve()
load_dotenv(".env")


def list_configs(configs: list[str], names: list[str]):
    """Lista todas as configs disponíveis."""
    total = len(configs)
    print(f"\nConfigs disponíveis: {total}\n")
    print("-" * 60)

    for i in range(total):
        name = names[i] if i < len(names) and names[i] else f"Config {i + 1}"
        print(f"  {i+1:3d}. {name}")

    print("-" * 60)
    print(f"\nUso: python -m benchmark \"1-{total}\" para testar todas")
    print(f"     python -m benchmark \"1,2,3\" para testar específicas\n")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark tool para GithubDocs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
    python -m benchmark "1-20"          Testa linhas 1 a 20 do Sheets
    python -m benchmark "1,4,7"         Testa linhas 1, 4 e 7
    python -m benchmark "1-5,10"        Testa linhas 1-5 e 10
    python -m benchmark "all"           Testa todas as linhas
    python -m benchmark --list          Lista configs disponíveis
    python -m benchmark "1-5" --local   Usa configs locais (test_configs.py)
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
        "--no-export",
        action="store_true",
        help="Não exporta resultados para Google Sheets",
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

    parser.add_argument(
        "--local",
        action="store_true",
        help="Usa configs locais (test_configs.py) em vez do Google Sheets",
    )

    parser.add_argument(
        "--refine",
        action="store_true",
        help="Ativa refinamento de arquivos grandes via load_summarize_chain antes de enviar ao modelo",
    )

    parser.add_argument(
        "--no-langfuse",
        action="store_true",
        help="Disable Langfuse export even if environment variables are configured",
    )

    parser.add_argument(
        "--config-worksheet",
        type=str,
        default=os.getenv("GOOGLE_SHEETS_CONFIG_WORKSHEET", "TestConfigs"),
        help="Nome da aba com configs de teste (default: TestConfigs ou env)",
    )

    args = parser.parse_args()

    # Carrega configs: Sheets por padrão, local com --local
    if args.local:
        print("Usando configs locais (test_configs.py)...")
        configs, names, metadata = load_configs(from_sheets=False)
    else:
        try:
            print("Carregando configs do Google Sheets...")
            configs, names, metadata = load_configs(
                from_sheets=True,
                worksheet_name=args.config_worksheet,
                credentials_path=args.credentials,
                spreadsheet_id=args.spreadsheet,
            )
            print(f"Carregadas {len(configs)} configs (linhas do Sheets)")
        except Exception as e:
            print(f"Erro ao carregar configs do Sheets: {e}")
            print("Use --local para usar configs locais ou configure o .env")
            return 1

    if args.list:
        list_configs(configs, names)
        return 0

    if args.indices is None:
        parser.print_help()
        print("\nErro: Especifique os índices ou use --list para ver configs disponíveis")
        return 1

    total_configs = len(configs)

    if total_configs == 0:
        print("Erro: Nenhuma config definida")
        if args.local:
            print("Adicione suas configs TOML no array TEST_CONFIGS em test_configs.py")
        else:
            print("Verifique se a aba do Sheets contém dados válidos")
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

    langfuse_exporter = None
    if not args.no_langfuse:
        try:
            from .langfuse_exporter import create_langfuse_exporter
            langfuse_exporter = create_langfuse_exporter()
            if langfuse_exporter:
                print("Langfuse: export enabled.")
            else:
                print(
                    "Langfuse: LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY not configured — export disabled."
                )
        except Exception as e:
            print(f"Langfuse: failed to initialize ({e}) — continuing without export.")

    runner = BenchmarkRunner(configs=configs, names=names, metadata=metadata, verbose=not args.quiet, refine=args.refine, langfuse_exporter=langfuse_exporter)
    results = runner.run_batch(indices)

    if not args.no_export:
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