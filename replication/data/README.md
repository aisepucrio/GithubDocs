# Curated export schema

Files are UTF-8, comma-separated CSVs compressed with deterministic gzip headers.
Quoted cells may contain multiline prompts, code, JSON and generated Markdown.
Pandas can read them directly with `pd.read_csv(path, low_memory=False)`.
The source uses both empty cells and the literal `Valor Nulo` for missing values;
the analysis scripts preserve the source normalization rules.

| Fields | Meaning |
|---|---|
| `context_id` | Context identifier, scoped to the source project/system |
| `user_id` | Consistent pseudonym; `synthetic-*` denotes failure placeholders |
| `Q : Clareza`, `Q : Completude`, `Q : Concisão`, `Q : Corretude` | Individual criterion rating, 1–5 or missing |
| `Q : Justifique sua classificação de ...` | Original free-text justification |
| `C : input` / `C : prompt` | Rendered DOME input / Claude Code prompt |
| `C : output` | Generated document or failure/null output |
| `C : output_char_count` | Original stripped output length, measured before project/link redaction |
| `C : metadata_config_index` | Test case used for matching systems in RQ3 |
| `C : metadata_repo_path` | Original subject-repository path |
| `C : metadata_test_type` | README generation, README update or CHANGELOG task |
| `C : metadata_model_name`, `C : metadata_temperature` | Available DOME model configuration |
| `C : is_tool_calling`, `C : metadata_commit_mixed` | Strategy and commit grouping flags |
| `C : input_tokens`, `C : output_tokens`, `C : total_tokens`, `C : cache_*_tokens` | Recorded usage counts, with the source provider's accounting |
| `C : total_cost` | Recorded provider-billed cost in USD |
| `C : latency_seconds`, `C : metadata_execution_time_seconds`, `C : *_duration_s` | Recorded time measurements in seconds |
| `C : num_observations` | Recorded observation count; interpreted by the source notebook |
| `C : metadata_error_message`, `C : metadata_success`, `is_filler` | Failure evidence; `is_filler` marks supplied synthetic rows |
| `C : timestamp` / `C : metadata_timestamp` | Recorded timestamp strings |

The exact retained/dropped columns per source are listed in `../manifest.json`.
Additional provider/library metadata is retained where present; missing columns
in the Claude Code export are not fabricated. Fourteen human IDs and two
synthetic IDs are represented. Eighteen individual criterion values are missing.

Internal project names are replaced consistently by `project-a`, `project-b` and
`project-c`, including in filenames, prompts, outputs and comments. URLs and
40-character revision hashes within the exports are withheld; emails and local
home paths are masked. Trace/session identifiers and collector internals are
removed. Original numeric measurements and pre-redaction output lengths remain.
Third-party project names/excerpts remain where relevant. The private identity map
and original source checksums are not included. See `../docs/release.md` and
`../DATA_LICENSE.md` before public distribution.
