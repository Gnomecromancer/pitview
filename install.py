"""Create a Start Menu shortcut for PitView so it's findable via Windows+S."""
import os
import sys
import subprocess
from pathlib import Path


def find_pitview_exe():
    """Find the pitview script installed by pip."""
    candidates = [
        Path(sys.executable).parent / "Scripts",
        Path(sys.executable).parent.parent / "Scripts",
        Path(os.environ.get("APPDATA", "")) / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" / "PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0" / "LocalCache" / "local-packages" / "Python313" / "Scripts",
    ]
    for scripts in candidates:
        for name in ["pitview.exe", "pitview"]:
            p = scripts / name
            if p.exists():
                return str(p)
    return None


def create_shortcut(target: str, shortcut_path: str, description: str, icon: str | None = None):
    ps = f"""
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target}'
$Shortcut.Description = '{description}'
"""
    if icon:
        ps += f"$Shortcut.IconLocation = '{icon}'\n"
    ps += "$Shortcut.Save()"
    subprocess.run(["powershell.exe", "-Command", ps], check=True, capture_output=True)


def main():
    exe = find_pitview_exe()
    if not exe:
        print("ERROR: pitview not found. Run: pip install -e .")
        sys.exit(1)

    start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"
    start_menu.mkdir(parents=True, exist_ok=True)

    shortcut = str(start_menu / "PitView.lnk")
    create_shortcut(
        target=exe,
        shortcut_path=shortcut,
        description="FRC Robot Dashboard — Team 1317",
    )
    print(f"Installed: {shortcut}")
    print("PitView is now searchable via Windows+S")


if __name__ == "__main__":
    main()
