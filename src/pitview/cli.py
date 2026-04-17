import threading
import time

import click
import uvicorn


@click.command()
@click.option("--port", default=8765, help="Local server port")
@click.option("--nt-host", default=None, help="NT4 server host (default: auto from team number)")
@click.option("--rio-host", default="10.13.17.2", show_default=True, help="RoboRIO host")
@click.option("--rio-port", default=5800, show_default=True, help="RoboRIO HTTP port")
@click.option("--radio-host", default="10.13.17.1", show_default=True, help="Radio host")
@click.option("--radio-port", default=80, show_default=True, help="Radio HTTP port")
@click.option("--photon-host", default="photonvision.local", show_default=True, help="PhotonVision host")
@click.option("--photon-port", default=5800, show_default=True, help="PhotonVision HTTP port")
@click.option("--no-window", is_flag=True, help="Run server only, open in browser manually")
@click.option("--debug", is_flag=True, help="Enable WebView dev tools")
@click.version_option("0.1.0")
def main(port, nt_host, rio_host, rio_port, radio_host, radio_port, photon_host, photon_port, no_window, debug):
    """PitView — FRC robot dashboard for Team 1317."""
    from .server import app, config

    config.update({
        "nt_host": nt_host,
        "rio_host": rio_host,
        "rio_port": rio_port,
        "radio_host": radio_host,
        "radio_port": radio_port,
        "photon_host": photon_host,
        "photon_port": photon_port,
    })

    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    if no_window:
        click.echo(f"PitView running at http://127.0.0.1:{port}")
        server_thread.join()
        return

    try:
        import webview
        window = webview.create_window(
            "PitView — Team 1317",
            f"http://127.0.0.1:{port}",
            width=1440,
            height=900,
            min_size=(900, 600),
        )
        webview.start(debug=debug)
    except ImportError:
        click.echo(f"pywebview not installed — open http://127.0.0.1:{port} in a browser")
        server_thread.join()


if __name__ == "__main__":
    main()
