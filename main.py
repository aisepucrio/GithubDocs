import argparse
import logging

from dotenv import load_dotenv

from src.facade import start
from src.load_configuration import load_config
from src.load_configuration.conf_structures import CliParams
from src.log import CustomLogger


def main():
    parser = argparse.ArgumentParser(description="Gemini Documentation Generator")
    parser.add_argument("config_path", help="Path to the configuration file.")
    parser.add_argument("--mock", action="store_true", help="Use mock agent for testing.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--refine", action="store_true", help="Ativa refinamento de arquivos grandes via load_summarize_chain antes de enviar ao modelo.")
    parser.add_argument("--map-reduce", action="store_true", help="Ativa map-reduce: sumariza cada arquivo via batch e reduz com o prompt original.")
    parser.add_argument("--tool-calling", action="store_true", help="Substitui o prompt-com-dicionario por um prompt minimo + tool calling. O LLM puxa dados do repo sob demanda via tools do RepoInfoExtractor.")
    args = parser.parse_args()

    logger = CustomLogger()
    if args.debug:
        logger.log_level = logging.DEBUG

    logger.info("Loading configuration...")
    config = load_config(args.config_path)

    if args.mock:
        logger.warning("Using mock agent.")
        for step in config.orchestration_steps:
            step.model_name = "mock"

    if args.debug:
        logger.debug("Configuration loaded:")
        logger.debug(f"Target Info: {config.target_info}")
        logger.debug(f"Output Info: {config.output_info}")
        for step in config.orchestration_steps:
            logger.debug(f"Orchestration Step: {step}")

    config.cli_params = CliParams(
        refine=args.refine,
        map_reduce=args.map_reduce,
        tool_calling=args.tool_calling,
    )

    logger.info("Starting documentation generation...")
    start(config)


if __name__ == "__main__":
    load_dotenv()
    main()