# Setup Guide for Chatterbox Environment

This guide explains how to create and use a Python virtual environment named `chatterbox_env`
and install the required dependencies.

---

## 1. Create the virtual environment

Run the following command in your terminal or command prompt:

```bash
python -m venv chatterbox_env
```

This will create a folder called `chatterbox_env` containing the isolated environment.

---

## 2. Activate the virtual environment

- On **Windows**:
```bash
chatterbox_env\Scripts\activate
```

- On **macOS/Linux**:
```bash
source chatterbox_env/bin/activate
```

Once activated, your terminal should show `(chatterbox_env)` at the beginning of the line.

---

## 3. Install dependencies

Make sure you are inside the `chatterbox_env` environment (it should be activated).
Then install the required libraries using the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 4. Verify installation

Try running one of the example scripts, e.g.:

```bash
python example_for_mac.py
```

If everything is installed correctly, the script should run without import errors.

---


