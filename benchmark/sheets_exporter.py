"""
Exportador de resultados para Google Sheets.

SETUP NECESSÁRIO:
    1. Crie um projeto no Google Cloud Console
    2. Ative a Google Sheets API
    3. Crie credenciais de Service Account
    4. Baixe o JSON das credenciais
    5. Coloque o caminho no GOOGLE_SHEETS_CREDENTIALS ou no arquivo .env
    6. Compartilhe a planilha com o email do service account

VARIÁVEIS DE AMBIENTE:
    GOOGLE_SHEETS_CREDENTIALS: Caminho para o arquivo JSON de credenciais
    GOOGLE_SHEETS_SPREADSHEET_ID: ID da planilha (parte da URL)

EXEMPLO DE URL:
    https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_AQUI/edit
"""

import os
from datetime import datetime
from typing import Optional

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


class GoogleSheetsExporter:
    """Exporta resultados de benchmark para Google Sheets."""

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    HEADERS = [
        "Índice",
        "Nome Config",
        "Sucesso",
        "Tempo (s)",
        "Modelo",
        "Temperatura",
        "Repo",
        "Arquivo Output",
        "Erro",
        "Timestamp",
    ]

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
    ):
        """
        Inicializa o exportador.

        Args:
            credentials_path: Caminho para o JSON de credenciais (ou via env)
            spreadsheet_id: ID da planilha Google Sheets (ou via env)
        """
        if not GSPREAD_AVAILABLE:
            raise ImportError(
                "gspread não instalado. Execute: pip install gspread google-auth"
            )

        self.credentials_path = credentials_path or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

        if not self.credentials_path:
            raise ValueError(
                "Credenciais não configuradas. "
                "Defina GOOGLE_SHEETS_CREDENTIALS ou passe credentials_path"
            )

        if not self.spreadsheet_id:
            raise ValueError(
                "ID da planilha não configurado. "
                "Defina GOOGLE_SHEETS_SPREADSHEET_ID ou passe spreadsheet_id"
            )

        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

    def _connect(self):
        """Conecta ao Google Sheets."""
        if self._client is not None:
            return

        credentials = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=self.SCOPES,
        )
        self._client = gspread.authorize(credentials)
        self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)

    def _get_or_create_worksheet(self, name: str) -> "gspread.Worksheet":
        """Obtém ou cria uma worksheet."""
        self._connect()

        try:
            worksheet = self._spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(
                title=name,
                rows=1000,
                cols=len(self.HEADERS),
            )
            worksheet.append_row(self.HEADERS)

        return worksheet

    def export_results(
        self,
        results: list[dict],
        worksheet_name: Optional[str] = None,
        append: bool = True,
    ) -> str:
        """
        Exporta resultados para o Google Sheets.

        Args:
            results: Lista de dicionários com os resultados
            worksheet_name: Nome da aba (default: "Benchmark_YYYY-MM-DD")
            append: Se True, adiciona às linhas existentes; se False, substitui

        Returns:
            URL da planilha
        """
        if not results:
            raise ValueError("Nenhum resultado para exportar")

        self._connect()

        if worksheet_name is None:
            worksheet_name = f"Benchmark_{datetime.now().strftime('%Y-%m-%d')}"

        worksheet = self._get_or_create_worksheet(worksheet_name)

        if not append:
            worksheet.clear()
            worksheet.append_row(self.HEADERS)

        rows = []
        for r in results:
            row = [
                r.get("config_index", ""),
                r.get("config_name", ""),
                r.get("success", ""),
                r.get("execution_time_seconds", ""),
                r.get("model_name", ""),
                r.get("temperature", ""),
                r.get("repo_path", ""),
                r.get("output_file", ""),
                r.get("error_message", ""),
                r.get("timestamp", ""),
            ]
            rows.append(row)

        if rows:
            worksheet.append_rows(rows)

        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"
        print(f"\nResultados exportados para: {spreadsheet_url}")
        print(f"Aba: {worksheet_name}")
        print(f"Linhas adicionadas: {len(rows)}")

        return spreadsheet_url

    def create_summary_sheet(self, results: list[dict]) -> str:
        """
        Cria uma aba de resumo com estatísticas agregadas.

        Args:
            results: Lista de dicionários com os resultados

        Returns:
            URL da planilha
        """
        self._connect()

        worksheet_name = "Resumo"
        try:
            worksheet = self._spreadsheet.worksheet(worksheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=100,
                cols=10,
            )

        total = len(results)
        success = sum(1 for r in results if r.get("success") == "Sim")
        failures = total - success
        total_time = sum(float(r.get("execution_time_seconds", 0)) for r in results)
        avg_time = total_time / total if total > 0 else 0

        summary_data = [
            ["Métrica", "Valor"],
            ["Total de Testes", total],
            ["Sucessos", success],
            ["Falhas", failures],
            ["Taxa de Sucesso", f"{(success/total*100):.1f}%" if total > 0 else "N/A"],
            ["Tempo Total (s)", f"{total_time:.2f}"],
            ["Tempo Médio (s)", f"{avg_time:.2f}"],
            ["", ""],
            ["Última Atualização", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]

        worksheet.update(summary_data, "A1")

        models = {}
        for r in results:
            model = r.get("model_name", "desconhecido")
            if model not in models:
                models[model] = {"total": 0, "success": 0, "time": 0}
            models[model]["total"] += 1
            if r.get("success") == "Sim":
                models[model]["success"] += 1
            models[model]["time"] += float(r.get("execution_time_seconds", 0))

        if models:
            model_data = [["", ""], ["Por Modelo", ""], ["Modelo", "Total", "Sucesso", "Tempo Médio"]]
            for model, stats in models.items():
                avg = stats["time"] / stats["total"] if stats["total"] > 0 else 0
                model_data.append([model, stats["total"], stats["success"], f"{avg:.2f}s"])

            start_row = len(summary_data) + 2
            worksheet.update(model_data, f"A{start_row}")

        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"


def export_to_sheets(
    results: list[dict],
    credentials_path: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
    worksheet_name: Optional[str] = None,
    create_summary: bool = True,
) -> str:
    """
    Função helper para exportar resultados rapidamente.

    Args:
        results: Lista de dicionários com os resultados
        credentials_path: Caminho para credenciais (ou via env)
        spreadsheet_id: ID da planilha (ou via env)
        worksheet_name: Nome da aba
        create_summary: Se True, cria aba de resumo

    Returns:
        URL da planilha
    """
    exporter = GoogleSheetsExporter(
        credentials_path=credentials_path,
        spreadsheet_id=spreadsheet_id,
    )

    url = exporter.export_results(results, worksheet_name=worksheet_name)

    if create_summary:
        exporter.create_summary_sheet(results)

    return url
