import re
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from app.utils.settings import Settings, DEFAULT_MODELS, load_key, save_key, save_settings
from app.video.ffmpeg import test
from app.ui.widgets import label_row


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.title('Gemini Settings')
        self.geometry('620x730')
        self.minsize(540, 520)
        self.transient(owner)
        self.grab_set()
        self.data = owner.settings.model_copy(deep=True)
        box = ctk.CTkScrollableFrame(self)
        box.pack(fill='both', expand=True, padx=18, pady=12)
        box.grid_columnconfigure(1, weight=1)
        self.key = label_row(box, 'API Key', load_key(), 0)
        self.key.configure(show='*')
        ctk.CTkButton(box, text='Test API', command=self.test_api).grid(row=1, column=1, sticky='e', padx=12)
        ctk.CTkLabel(box, text='Primary Model').grid(row=2, column=0, padx=12, pady=10, sticky='w')
        self.primary = ctk.CTkOptionMenu(box, values=self.model_names())
        self.primary.set(self.data.primary_model)
        self.primary.grid(row=2, column=1, sticky='ew', padx=12)
        ctk.CTkLabel(box, text='Fallback Models (in order)').grid(row=3, column=0, columnspan=2, sticky='w', padx=12)
        self.checks = ctk.CTkScrollableFrame(box, height=215)
        self.checks.grid(row=4, column=0, columnspan=2, sticky='ew', padx=12)
        self.variables = {}
        self.draw_models()
        self.custom = label_row(box, 'Add Model', '', 5)
        ctk.CTkButton(box, text='Add Model', command=self.add_model).grid(row=6, column=1, sticky='e', padx=12)
        self.retries = label_row(box, 'Retry attempts', self.data.retry_attempts, 7)
        self.path = label_row(box, 'FFmpeg Path', self.data.ffmpeg_path, 8)
        actions = ctk.CTkFrame(box, fg_color='transparent')
        actions.grid(row=9, column=1, sticky='e', padx=12, pady=6)
        ctk.CTkButton(actions, text='Browse', width=85, command=self.browse).pack(side='left', padx=3)
        ctk.CTkButton(actions, text='Test FFmpeg', width=110, command=self.test_ffmpeg).pack(side='left', padx=3)
        ctk.CTkButton(self, text='Save', command=self.save).pack(pady=12)

    def model_names(self):
        return list(dict.fromkeys(['gemini-3.6-flash', *DEFAULT_MODELS, *self.data.custom_models, self.data.primary_model]))

    def draw_models(self):
        for child in self.checks.winfo_children():
            child.destroy()
        previous = {key: var.get() for key, var in self.variables.items()}
        self.variables = {}
        for name in self.model_names():
            var = ctk.BooleanVar(value=previous.get(name, name in self.data.fallback_models))
            self.variables[name] = var
            ctk.CTkCheckBox(self.checks, text=name, variable=var).pack(anchor='w', padx=8, pady=3)

    def add_model(self):
        name = self.custom.get().strip()
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{2,100}', name):
            messagebox.showerror('Model', 'Enter a valid Gemini model name.', parent=self)
            return
        if name not in self.data.custom_models and name not in self.model_names():
            self.data.custom_models.append(name)
            self.primary.configure(values=self.model_names())
            self.draw_models()
        self.custom.delete(0, 'end')

    def browse(self):
        path = filedialog.askopenfilename(parent=self, title='Select ffmpeg executable', filetypes=[('FFmpeg', 'ffmpeg.exe ffmpeg'), ('All files', '*.*')])
        if path:
            self.path.delete(0, 'end')
            self.path.insert(0, path)

    def test_ffmpeg(self):
        try:
            data = self.data.model_copy(update={'ffmpeg_path': self.path.get()})
            messagebox.showinfo('FFmpeg', test(data), parent=self)
        except Exception as exc:
            messagebox.showerror('FFmpeg', str(exc), parent=self)

    def test_api(self):
        key = self.key.get().strip()
        if not key:
            messagebox.showerror('Gemini', 'Enter an API key first.', parent=self)
            return
        model = self.primary.get()
        def work():
            try:
                from google import genai
                with genai.Client(api_key=key) as client:
                    response = client.models.generate_content(model=model, contents='Reply OK')
                    if not response.text:
                        raise ValueError('Empty response')
                self.owner.dispatch(lambda: messagebox.showinfo('Gemini', 'API connection successful.', parent=self))
            except Exception:
                self.owner.dispatch(lambda: messagebox.showerror('Gemini', 'API test failed. Check your key, model and internet connection.', parent=self))
        threading.Thread(target=work, daemon=True).start()

    def save(self):
        try:
            name = self.primary.get()
            retries = int(self.retries.get())
            settings = Settings(primary_model=name, fallback_models=[n for n, v in self.variables.items() if v.get() and n != name],
                                custom_models=self.data.custom_models, retry_attempts=retries, ffmpeg_path=self.path.get().strip())
            save_key(self.key.get())
            save_settings(settings)
            self.owner.settings = settings
            self.owner.note('Settings saved')
            self.destroy()
        except Exception:
            messagebox.showerror('Settings', 'Could not save settings. Check the retry count (1–8) and your system keyring.', parent=self)
