import tkinter as tk
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