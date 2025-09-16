import nltk
from nltk.translate.bleu_score import corpus_bleu
from nltk.tokenize import word_tokenize, sent_tokenize

# Baixa recursos necessários
nltk.download("punkt")
nltk.download("punkt_tab")

def read_markdown(filename):
    """Lê um arquivo Markdown e retorna lista de frases tokenizadas"""
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()
    # Divide em sentenças
    sentences = sent_tokenize(text)
    # Tokeniza cada sentença
    return [word_tokenize(sentence) for sentence in sentences]

# Caminhos
reference_file = "gabarito/gabarito.md"
hypothesis_file = "readme/readme.md"

# Lê e processa
references = read_markdown(reference_file)
hypotheses = read_markdown(hypothesis_file)

print("Frases no gabarito:", len(references))
print("Frases nas hipóteses:", len(hypotheses))

# Ajusta para o menor tamanho
min_len = min(len(references), len(hypotheses))
references = references[:min_len]
hypotheses = hypotheses[:min_len]

# BLEU espera lista de listas de referências
references_for_bleu = [[ref] for ref in references]

# Calcula BLEU corpus-level
bleu_score = corpus_bleu(references_for_bleu, hypotheses)
print("\n\n\n\n")
print(f"BLEU score (corpus): {bleu_score:.4f}")
print("\n\n\n\n")
