import argparse
import logging

from dotenv import load_dotenv

from src.facade import start
from src.load_configuration import load_config
from src.log import CustomLogger


def main():
    parser = argparse.ArgumentParser(description="Gemini Documentation Generator")
    parser.add_argument("config_path", help="Path to the configuration file.")
    parser.add_argument("--mock", action="store_true", help="Use mock agent for testing.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--issuelog", action="store_true", help="Print GitHub issues analysis to terminal.")
    parser.add_argument("--refine", action="store_true", help="Ativa refinamento de arquivos grandes via load_summarize_chain antes de enviar ao modelo.")
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

    logger.info("Starting documentation generation...")
    start(config, enable_issue_log=args.issuelog or args.debug, refine=args.refine)


if __name__ == "__main__":
    load_dotenv()
    main()