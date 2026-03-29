import winreg
import sys
import os

def register_context_menu():
    # Path to your python script or executable
    app_path = os.path.abspath(__file__)  # if running as .py
    # If you've compiled to .exe, replace with the path to your .exe instead:
    # app_path = r"C:\path\to\your\app.exe"

    python_path = sys.executable 

    key_path = r"*\\shell\\Open with CSV Editor"
    command_path = key_path + r"\\command"

    try:
        # Create the context menu entry
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Open with CSV Editor")

        # Set the command to run when clicked
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_path) as key:
            winreg.SetValueEx(
                key, "", 0, winreg.REG_SZ,
                f'"{python_path}" "{app_path}" "%1"'
            )
        print("Registered successfully.")
    except PermissionError:
        print("Run this script as administrator.")

def unregister_context_menu():
    try:
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\\shell\\Open with CSV Editor\\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\\shell\\Open with CSV Editor")
        print("Unregistered successfully.")
    except FileNotFoundError:
        print("Registry entry not found.")

register_context_menu()