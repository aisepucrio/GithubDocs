from rouge_score import rouge_scorer

# Função para ler o texto completo de um arquivo
def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

# Caminhos dos arquivos
reference_file = "gabarito/gabarito.md"
hypothesis_file = "readme/readme.md"

# Lê os textos
reference_text = read_file(reference_file)
hypothesis_text = read_file(hypothesis_file)

# Inicializa o scorer do ROUGE
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Calcula o score
scores = scorer.score(reference_text, hypothesis_text)

# Exibe os resultados
print("\n\n\n")
for rouge_type, score in scores.items():
    print(f"{rouge_type.upper()}: Precision={score.precision:.4f}, "
          f"Recall={score.recall:.4f}, F1={score.fmeasure:.4f}")
print("\n\n\n")
