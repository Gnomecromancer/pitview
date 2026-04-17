import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pitview",
        description="FRC robot dashboard: NT4 live data, PhotonVision cameras, radio, and system stats for Team 1317",
    )
    parser.add_argument("--version", action="version", version="0.1.0")
    args = parser.parse_args()
    print("pitview: not yet implemented")


if __name__ == "__main__":
    main()
