"""AI Shorts Maker: local Windows desktop entry point."""
import customtkinter as ctk
from app.ui.main_window import MainWindow


def main():
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('blue')
    MainWindow().mainloop()


if __name__ == '__main__':
    main()
