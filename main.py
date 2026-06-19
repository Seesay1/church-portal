import tkinter as tk
import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

# Load environment variables before importing modules that use them.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from login import LoginUI
from database import setup_database

def main():

    # Create database and tables
    setup_database()

    root = tk.Tk()
    LoginUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
