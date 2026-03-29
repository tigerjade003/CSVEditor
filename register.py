import winreg
import sys
import os

def register_context_menu():
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".csv") as key:
        prefix = winreg.QueryValue(key, "")
    app_path = os.path.abspath(__file__)
    python_path = sys.executable

    # csvfile targets .csv files only
    key_path = f"{prefix}\\shell\\Open with CSV Editor"
    command_path = key_path + r"\command"

    try:
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Open with CSV Editor")

        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_path) as key:
            winreg.SetValueEx(
                key, "", 0, winreg.REG_SZ,
                f'"{python_path}" "{app_path}" "%1"'
            )
        print("Registered successfully.")
    except PermissionError:
        print("Run this script as administrator.")

def unregister_context_menu():
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".csv") as key:
        prefix = winreg.QueryValue(key, "")
    try:
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{prefix}\\shell\\Open with CSV Editor\\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{prefix}\\shell\\Open with CSV Editor")
        print("Unregistered successfully.")
    except FileNotFoundError:
        print("Registry entry not found.")

register_context_menu()