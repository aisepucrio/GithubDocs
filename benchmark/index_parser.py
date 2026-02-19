"""
Parser de índices para seleção de configs de teste.

Formatos suportados:
    "1-20"      -> [1, 2, 3, ..., 20]
    "1,4,7"     -> [1, 4, 7]
    "1-5,10,15" -> [1, 2, 3, 4, 5, 10, 15]
    "all"       -> todos os configs disponíveis
"""

import re


def parse_indices(index_string: str, max_index: int) -> list[int]:
    """
    Converte uma string de índices em uma lista de inteiros.

    Args:
        index_string: String com os índices (ex: "1-20", "1,4", "1-5,10")
        max_index: Índice máximo permitido (tamanho do array de configs)

    Returns:
        Lista de índices (0-based internamente, mas input é 1-based)

    Raises:
        ValueError: Se o formato for inválido ou índices fora do range
    """
    index_string = index_string.strip().lower()

    if index_string == "all":
        return list(range(max_index))

    indices = set()
    parts = index_string.split(",")

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            match = re.match(r"^(\d+)-(\d+)$", part)
            if not match:
                raise ValueError(f"Formato inválido de range: '{part}'. Use formato '1-20'")

            start = int(match.group(1))
            end = int(match.group(2))

            if start > end:
                raise ValueError(f"Range inválido: início ({start}) maior que fim ({end})")

            if start < 1:
                raise ValueError(f"Índice deve começar em 1, não {start}")

            if end > max_index:
                raise ValueError(f"Índice {end} excede o máximo disponível ({max_index})")

            for i in range(start, end + 1):
                indices.add(i - 1)  # Converte para 0-based
        else:
            if not part.isdigit():
                raise ValueError(f"Índice inválido: '{part}'. Use apenas números")

            idx = int(part)

            if idx < 1:
                raise ValueError(f"Índice deve começar em 1, não {idx}")

            if idx > max_index:
                raise ValueError(f"Índice {idx} excede o máximo disponível ({max_index})")

            indices.add(idx - 1)  # Converte para 0-based

    return sorted(list(indices))


def format_indices_summary(indices: list[int]) -> str:
    """
    Formata uma lista de índices em um resumo legível.

    Args:
        indices: Lista de índices (0-based)

    Returns:
        String formatada (ex: "1-5, 10, 15-20")
    """
    if not indices:
        return "nenhum"

    indices_1based = [i + 1 for i in sorted(indices)]

    ranges = []
    start = indices_1based[0]
    end = start

    for idx in indices_1based[1:]:
        if idx == end + 1:
            end = idx
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = idx
            end = idx

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)
