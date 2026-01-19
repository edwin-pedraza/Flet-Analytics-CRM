import argparse
import os
import webbrowser

import flet as ft

from app.ui import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CRM Analytics UI")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host for UI server")
    parser.add_argument("--port", type=int, default=8550, help="UI server port")
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_URL", "http://127.0.0.1:8000"),
        help="Backend API URL",
    )
    parser.add_argument("--desktop", action="store_true", help="Run as desktop app")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    view = ft.AppView.FLET_APP if args.desktop else ft.AppView.WEB_BROWSER

    if view == ft.AppView.WEB_BROWSER and not args.no_browser:
        if args.host in ("0.0.0.0", "::"):
            open_url = f"http://127.0.0.1:{args.port}"
        else:
            open_url = f"http://{args.host}:{args.port}"
        os.environ["FLET_DISPLAY_URL_PREFIX"] = open_url
        try:
            webbrowser.open(open_url)
        except Exception:
            pass

    ft.run(
        lambda page: main(page, api_url=args.api_url),
        host=args.host,
        port=args.port,
        view=view,
    )
