import logging
import sys
import traceback
import inspect
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    DEBUG = "DEBUG"


class Colors:
    """Códigos ANSI para cores no terminal"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class CustomLogger:
    def __init__(self, log_level=logging.INFO, show_timestamp=True):
        self.log_level = log_level
        self.show_timestamp = show_timestamp
    
    def _get_caller_info(self):
        try:
            frame = inspect.currentframe()
            if frame is None:
                return "unknown", 0, "unknown"
            
            caller_frame = frame
            while caller_frame:
                caller_frame = caller_frame.f_back
                if caller_frame is None:
                    break
                code_name = caller_frame.f_code.co_name
                if code_name not in ['_get_caller_info', '_log', 'info', 'success', 'warning', 'debug', 'error', '__init__']:
                    break
            
            if caller_frame is None:
                return "unknown", 0, "unknown"
            
            filename = caller_frame.f_code.co_filename
            line_number = caller_frame.f_lineno
            function_name = caller_frame.f_code.co_name
            
            short_filename = filename.split('/')[-1].split('\\')[-1]
            
            return short_filename, line_number, function_name
        except Exception:
            return "unknown", 0, "unknown"
        finally:
            # É uma boa prática deletar o frame para evitar vazamento de memória
            del frame
    
    def _format_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _log(self, level: LogLevel, message: str, color: str):
        filename, line, function = self._get_caller_info()
        
        if filename != "unknown":
            location = f"{filename}:{line}"
            if function != "<module>":
                location += f" ({function})"
        else:
            location = "unknown location"
        
        parts = []
        
        # REMOÇÃO DO COLORS.RESET de cada parte do prefixo
        if self.show_timestamp:
            parts.append(f"{Colors.GRAY}[{self._format_timestamp()}]") 
        
        parts.append(f"{color}{Colors.BOLD}[{level.value}]")
        parts.append(f"{Colors.CYAN}[{location}]")
        
        prefix = " ".join(parts)
        
        print(f"{prefix}{Colors.RESET} {message}{Colors.RESET}")
    
    def info(self, message: str):
        """Log de informação"""
        if self.log_level <= logging.INFO:
            self._log(LogLevel.INFO, message, Colors.BLUE)
    
    def success(self, message: str):
        """Log de sucesso"""
        if self.log_level <= logging.INFO:
            self._log(LogLevel.SUCCESS, message, Colors.GREEN)

    def warning(self, format_string: str, variable=None):
        if self.log_level <= logging.WARNING:
            # If a variable exists, format it. Otherwise, use the string as-is.
            if variable is not None:
                message = format_string % variable
            else:
                message = format_string
                
            self._log(LogLevel.WARNING, message, Colors.YELLOW)

    def debug(self, message: str):
        """Log de debug"""
        if self.log_level <= logging.DEBUG:
            self._log(LogLevel.DEBUG, message, Colors.MAGENTA)

    def error(self, message: str, exception: Exception = None):
        """Log de erro"""
        if self.log_level <= logging.INFO:
            self._log(LogLevel.ERROR, message, Colors.RED)