from main import main
import argparse
from log import CustomLogger

def main():
    parser = argparse.ArgumentParser(description="Gemini Documentation Generator")
    parser.add_argument("tests_path", help="Path to the tests file.")
    parser.add_argument("range_path", help="range between 0-n saying which tests to consider .")
    args = parser.parse_args()

    logger = CustomLogger()
    logger.info("Starting tests...")

class TestModels:

    def test_gemini_model(self):
        pass