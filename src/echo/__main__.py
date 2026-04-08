"""Entry point for `python -m echo`."""

import sys


def main() -> None:
    """Run the Echo AI Chatbot application."""
    from echo.cli import EchoConsoleApp

    try:
        app = EchoConsoleApp()
        app.run()
    except KeyboardInterrupt:
        pass  # Already handled in run()
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
