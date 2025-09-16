from bert_score import score

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

# BERTScore espera listas de strings (uma ou várias sentenças)
references = [reference_text]
hypotheses = [hypothesis_text]

# Calcula BERTScore
P, R, F1 = score(hypotheses, references, lang="en", rescale_with_baseline=True)

# Exibe resultados
print("\n\n\n")
print(f"BERTScore Precision: {P[0]:.4f}")
print(f"BERTScore Recall:    {R[0]:.4f}")
print(f"BERTScore F1:        {F1[0]:.4f}")
print("\n\n\n")
