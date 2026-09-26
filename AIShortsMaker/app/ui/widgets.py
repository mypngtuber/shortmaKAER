import customtkinter as ctk


def label_row(parent, title, value, row, width=360):
    ctk.CTkLabel(parent, text=title, anchor='w').grid(row=row, column=0, padx=12, pady=7, sticky='w')
    entry = ctk.CTkEntry(parent, width=width)
    entry.insert(0, str(value))
    entry.grid(row=row, column=1, padx=12, pady=7, sticky='ew')
    return entry
