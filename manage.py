from app import create_app, seed_data

app = create_app()


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "initdb":
        seed_data(app)
        print("Database initialized.")
    else:
        app.run(debug=True)
