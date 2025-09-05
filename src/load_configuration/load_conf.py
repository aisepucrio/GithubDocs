def read_configuration(file_path: str) -> dict:
    import yaml
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == "__main__":
    print(read_configuration("conf/config.yaml"))
