import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    'api_key',
    help="Faceit Developer API key"
)
args = parser.parse_args()
api_key = args.api_key

def main():
    pass

if __name__ == "__main__":
    main()