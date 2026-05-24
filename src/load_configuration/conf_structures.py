from dataclasses import dataclass
from pydantic import BaseModel, field_validator
from .validators import *
from typing import Optional
import os

IGNORE_FILES_PRESET = [  # Lock files
  'package-lock.json',
  'package.json',
  'package.json_1',
  'yarn.lock',
  'pnpm-lock.yaml',
  'composer.lock',
  'Gemfile.lock',
  'Cargo.lock',
  'poetry.lock',
  'Pipfile.lock',
  'go.sum',
  'mix.lock',
  'pubspec.lock',

  # Dependency directories
  'node_modules/**',
  'vendor/**',
  'bower_components/**',
  '.pnp/**',
  '__pycache__/**',
  'venv/**',
  'env/**',
  '.venv/**',
  'target/**',
  'build/**',
  'dist/**',
  'out/**',

  # Images
  '*.jpg',
  '*.jpeg',
  '*.png',
  '*.gif',
  '*.bmp',
  '*.ico',
  '*.svg',
  '*.webp',
  '*.tiff',
  '*.psd',
  '*.ai',
  '*.sketch',
  '*.fig',

  # Videos
  '*.mp4',
  '*.avi',
  '*.mov',
  '*.wmv',
  '*.flv',
  '*.webm',
  '*.mkv',

  # Audio
  '*.mp3',
  '*.wav',
  '*.ogg',
  '*.flac',
  '*.aac',
  '*.m4a',

  # Fonts
  '*.woff',
  '*.woff2',
  '*.ttf',
  '*.eot',
  '*.otf',

  # Archives
  '*.zip',
  '*.tar',
  '*.gz',
  '*.rar',
  '*.7z',
  '*.bz2',

  # Documents/PDFs
  '*.pdf',
  '*.doc',
  '*.docx',
  '*.xls',
  '*.xlsx',
  '*.ppt',
  '*.pptx',

  # Compiled/Binary files
  '*.exe',
  '*.dll',
  '*.so',
  '*.dylib',
  '*.class',
  '*.pyc',
  '*.pyo',
  '*.o',
  '*.a',
  '*.lib',
  '*.obj',
  '*.jar',
  '*.war',
  '*.ear',

  # IDE/Editor specific
  '.idea/**',
  '.vscode/**',
  '*.swp',
  '*.swo',
  '*~',
  '.DS_Store',
  'Thumbs.db',
  '*.sublime-workspace',
  '*.sublime-project',

  # Logs
  '*.log',
  'logs/**',
  'npm-debug.log*',
  'yarn-debug.log*',
  'yarn-error.log*',

  # Database files
  '*.db',
  '*.sqlite',
  '*.sqlite3',

  # Cache
  '.cache/**',
  '.next/**',
  '.nuxt/**',
  '.gradle/**',
  '.sass-cache/**',

  # Coverage reports
  'coverage/**',
  '.nyc_output/**',
  '*.lcov',

  # Generated/Minified files
  '*.min.js',
  '*.min.css',
  '*.map',
  '*.bundle.js',
  '*.chunk.js',

  # Environment files (opcional - depende do caso)
  # '.env',
  # '.env.local',
  # '.env.*.local',
  ]




class TargetInfo(BaseModel):
    repo_path: str
    branch_name: str
    commit_list: Optional[list[str]] = None
    ignore_files: Optional[list[str]] = None

    @field_validator("repo_path")
    def validate_repo_path(cls, v):
        if not path_validator(v):
            raise KeyError(f"\u274C Invalid repository {v} path")
        return v

    def __init__(self, **kwargs):
      ignore = kwargs.get("ignore_files")
      if isinstance(ignore, list) and "IGNORED_PRESET" in ignore:
          extra = [f for f in ignore if f != "IGNORED_PRESET"]
          kwargs["ignore_files"] = IGNORE_FILES_PRESET.copy() + extra
      elif ignore == "IGNORED_PRESET":
          kwargs["ignore_files"] = IGNORE_FILES_PRESET.copy()
      super().__init__(**kwargs)

    def __str__(self):
        return f"Target_info(repo_path={self.repo_path}, branch_name={self.branch_name}, commit_list={self.commit_list}, ignore_files={self.ignore_files})"


class OutputInfo(BaseModel):
    result_path: str
    log_path: str
    result_file_name: str

    @field_validator("result_path", "log_path")
    def validate_paths(cls, v):
        if not path_validator(v):
            raise KeyError(f"\u274C Path does not exist or is not a directory: {v} Please read the documentation carefully to set up the output paths")
        return v

    def __str__(self):
        return f"Output_info(result_path={self.result_path}, log_path={self.log_path}, result_file_name={self.result_file_name})"


class OrchestrationStep(BaseModel):
    step: int
    model_name: str
    temperature: float
    prompt_file: str
    template_path: str = ""
    prompt_variables: dict[str, str]
    prompt: str = ""

    @field_validator("temperature")
    def validate_temperature(cls, v):
        if not temperature_validator(v):
            raise KeyError(f"\u274C Temperature must be between 0.0and 2.0")
        return v
    
    @field_validator("template_path")
    def validate_template_path(cls, v):
        if not path_validator(v):
            raise KeyError(f"\u274C Invalid template {v} path")
        return v
    
    def __str__(self):
        return f"OrchestrationStep(step={self.step}, model_name={self.model_name}, temperature={self.temperature}, prompt_path={self.prompt_file}, prompt_variables={self.prompt_variables}, prompt={self.prompt[:50]}...)"
    
class CliParams(BaseModel):
    refine: bool = False
    map_reduce: bool = False
    tool_calling: bool = False

class BaseAppConfig(BaseModel):
    target_info: TargetInfo
    output_info: OutputInfo
    orchestration_steps: list[OrchestrationStep]
    cli_params: CliParams = CliParams()