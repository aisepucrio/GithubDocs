from rouge_score import rouge_scorer
from nltk.tokenize import sent_tokenize
import nltk

# Baixa recursos do NLTK
nltk.download("punkt")

# Função para ler texto completo
def read_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

# Caminhos dos arquivos
reference_file = "gabarito/gabarito.md"
hypothesis_file = "readme/readme.md"

# Lê os textos
reference_text = read_file(reference_file)
hypothesis_text = read_file(hypothesis_file)

# Divide os textos em frases
reference_sentences = sent_tokenize(reference_text)
hypothesis_sentences = sent_tokenize(hypothesis_text)

# Ajusta para o menor tamanho
min_len = min(len(reference_sentences), len(hypothesis_sentences))
reference_sentences = reference_sentences[:min_len]
hypothesis_sentences = hypothesis_sentences[:min_len]

# Inicializa o scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Calcula ROUGE para cada frase
for i, (ref, hyp) in enumerate(zip(reference_sentences, hypothesis_sentences), start=1):
    scores = scorer.score(ref, hyp)
    print(f"--- Frase {i} ---")
    print("Referência: ", ref)
    print("Hipótese:   ", hyp)
    for rouge_type, score in scores.items():
        print(f"{rouge_type.upper()}: Precision={score.precision:.4f}, "
              f"Recall={score.recall:.4f}, F1={score.fmeasure:.4f}")
    print()
