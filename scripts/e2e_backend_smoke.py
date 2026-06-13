from backend.app.main import health


def main() -> None:
    payload = health()
    if payload.get("status") != "ok":
        raise SystemExit(f"health status was not ok: {payload}")
    print("backend smoke: /health ok")


if __name__ == "__main__":
    main()
