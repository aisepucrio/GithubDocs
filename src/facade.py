from src.load_configuration import read_configuration
from src.load_configuration import FrameworkConfig

def main_loop():
    frame_conf = read_configuration("conf/config.yaml")
    
    extracted_information = frame_conf.extract_information

    