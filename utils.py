"""
Module for utility functions such as checking available models, etc.
"""
import argparse
import openai


def print_available_models():
    """Print all available models."""
    models = openai.Model.list()
    print("Available models:")
    if models is None:
        print("Models not available. The API returned None.")
        return

    if not isinstance(models, dict) or "data" not in models:
        print("Models not available. No 'data' in the API response.")
        return

    model_data = models.get("data")

    if model_data is None:
        print("Models not available. The API returned None in 'data'.")
        return

    for model in model_data:
        print(model.get("id"))


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        prog="Meidobot utils", description="Utility functions for Meidobot."
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available models.",
    )
    args = parser.parse_args()

    if args.list_models:
        print_available_models()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
