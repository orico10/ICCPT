# Building Executables

This page explains how to build executables for Windows and macOS.

## Prerequisites

From the repository root (`CleanCooking_os`):

```cmd
pip install -r requirements_developer.txt
```

If you do not have a developer requirements file installed yet, start from:

```cmd
pip install -r requirements.txt
```

## Windows executable (main.exe)

Run PyInstaller from the repository root:

```cmd
pyinstaller --onefile --paths=./src main.py
```

This creates a `dist` folder. The executable will be located at:

```
dist\main.exe
```

Move `main.exe` so that it sits at the same level as `main.py` in the repository.
That is the expected layout for running ICCPT as a user.

## macOS executable (main)

Run PyInstaller from the repository root:

```bash
pyinstaller --onefile --paths=./src main.py
```

This creates a `dist` folder. The executable will be located at:

```
dist/main
```

Move `main` so that it sits at the same level as `main.py` in the repository.


