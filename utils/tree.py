# tree.py
import os

def tree(path='.', include_venv_files=False, _prefix=''):
    """
    Gera a estrutura de diretórios semelhante ao comando 'tree',
    ignorando a pasta .git e, por padrão, ignorando arquivos dentro da pasta venv.
    Retorna a árvore como string.
    
    Args:
        path (str): diretório raiz
        include_venv_files (bool): se True, inclui arquivos internos da venv
        _prefix (str): usado internamente para formatação recursiva
    
    Returns:
        str: árvore de diretórios formatada
    """
    entries = sorted(os.listdir(path))
    entries = [e for e in entries if e != '.git']  # ignora .git
    entries_count = len(entries)
    
    lines = []
    
    for idx, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        is_last = idx == entries_count - 1
        connector = '└── ' if is_last else '├── '
        lines.append(f"{_prefix}{connector}{entry}")
        
        if os.path.isdir(full_path):
            # Se for venv e não quiser incluir arquivos internos, apenas mostra a pasta
            if entry == '.venv' and not include_venv_files:
                continue
            # Define novo prefixo para subdiretórios
            new_prefix = _prefix + ('    ' if is_last else '│   ')
            lines.append(tree(full_path, include_venv_files, _prefix=new_prefix))
    
    return '\n'.join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gera a árvore de diretórios como string")
    parser.add_argument("path", nargs="?", default=".", help="Diretório raiz")
    parser.add_argument("--include-venv", action="store_true", help="Incluir arquivos dentro da venv")
    args = parser.parse_args()
    
    output = tree(args.path, include_venv_files=args.include_venv)
    print(output)
