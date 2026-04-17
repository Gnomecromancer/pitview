from click.testing import CliRunner
from pitview.cli import main
from pitview.nt import NTClient
from pitview.rio import poll_system, ping_robot


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "1317" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_nt_client_init():
    client = NTClient(team=1317)
    assert client.team == 1317
    assert not client.connected
    assert client.snapshot() == {}


def test_nt_client_listener():
    client = NTClient(team=1317)
    events = []
    client.add_listener(events.append)
    assert len(client._listeners) == 1


def test_rio_unreachable():
    # Robot not connected in test environment
    assert ping_robot() is False
    stats = poll_system()
    assert isinstance(stats, dict)
