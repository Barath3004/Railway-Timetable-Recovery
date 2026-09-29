
import sys

def main():
    from src.api.app import app

    app.run(host="127.0.0.1", port=5000)
    return 0

if __name__ == "__main__":
    sys.exit(main())
