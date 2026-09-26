import queue
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from app.models.shorts import Job
from app.utils.settings import load_key, load_settings
from app.utils.files import AUDIO, VIDEO, require_file
from app.utils.logger import log_line
from app.video.ffmpeg import video_length
from app.subtitles.parser import parse_srt
from app.services.analyzer import analyze
from app.services.project import cached_analysis, load_project, save_analysis
from app.ui.settings_window import SettingsWindow
from app.ui.results_window import ResultsWindow


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('AI SHORTS MAKER')
        self.geometry('760x800')
        self.minsize(610, 660)
        self.settings = load_settings()
        self.tasks = queue.Queue()
        self.busy = False
        self.video = ''
        self.srt = ''
        self.audio = ''
        header = ctk.CTkFrame(self)
        header.pack(fill='x', padx=18, pady=12)
        ctk.CTkLabel(header, text='AI SHORTS MAKER', font=ctk.CTkFont(size=22, weight='bold')).pack(side='left', padx=14, pady=9)
        ctk.CTkButton(header, text='Settings', width=85, command=lambda: SettingsWindow(self)).pack(side='right', padx=6)
        ctk.CTkButton(header, text='Open Project', width=110, command=self.open_project).pack(side='right', padx=6)
        form = ctk.CTkScrollableFrame(self)
        form.pack(fill='both', expand=True, padx=18, pady=5)
        ctk.CTkLabel(form, text='VIDEO', font=ctk.CTkFont(size=16, weight='bold')).pack(anchor='w', padx=12, pady=8)
        self.video_text = ctk.CTkLabel(form, text='Select local video (.mp4, .mov, .mkv, .avi, .webm)', wraplength=570)
        self.video_text.pack(pady=8)
        ctk.CTkButton(form, text='Select Video', command=self.select_video).pack(pady=7)
        ctk.CTkLabel(form, text='CONTENT SOURCE', font=ctk.CTkFont(size=16, weight='bold')).pack(anchor='w', padx=12, pady=10)
        self.mode = ctk.StringVar(value='srt')
        modes = ctk.CTkFrame(form, fg_color='transparent')
        modes.pack(fill='x', padx=14)
        for title, value in [('SRT', 'srt'), ('Audio', 'audio'), ('Audio + SRT', 'audio_srt')]:
            ctk.CTkRadioButton(modes, text=title, variable=self.mode, value=value).pack(side='left', padx=12, pady=7)
        files = ctk.CTkFrame(form, fg_color='transparent')
        files.pack(pady=10)
        ctk.CTkButton(files, text='Select SRT', command=self.select_srt).pack(side='left', padx=7)
        ctk.CTkButton(files, text='Select Audio', command=self.select_audio).pack(side='left', padx=7)
        self.srt_text = ctk.CTkLabel(form, text='SRT: none', wraplength=550)
        self.srt_text.pack()
        self.audio_text = ctk.CTkLabel(form, text='Audio: none', wraplength=550)
        self.audio_text.pack()
        values = ctk.CTkFrame(form)
        values.pack(fill='x', padx=12, pady=15)
        self.count = self.field(values, 'Number of Shorts', '5')
        self.minimum = self.field(values, 'Minimum duration (sec)', '20')
        self.maximum = self.field(values, 'Maximum duration (sec)', '60')
        ctk.CTkLabel(values, text='Output: 9:16  •  1080 × 1920  •  MP4').pack(pady=8)
        actions = ctk.CTkFrame(form, fg_color='transparent')
        actions.pack(pady=7)
        self.find_button = ctk.CTkButton(actions, text='FIND SHORTS', width=170, height=45, command=self.find)
        self.find_button.pack(side='left', padx=5)
        ctk.CTkButton(actions, text='Re-analyze', width=105, height=45, command=lambda: self.find(True)).pack(side='left', padx=5)
        footer = ctk.CTkFrame(self)
        footer.pack(fill='x', padx=18, pady=10)
        self.status = ctk.CTkLabel(footer, text='Status: Ready')
        self.status.pack(anchor='w', padx=12, pady=3)
        self.bar = ctk.CTkProgressBar(footer)
        self.bar.pack(fill='x', padx=12, pady=5)
        self.bar.set(0)
        ctk.CTkLabel(footer, text='LOG', anchor='w').pack(fill='x', padx=12)
        self.logs = ctk.CTkTextbox(footer, height=95, state='disabled')
        self.logs.pack(fill='x', padx=12, pady=5)
        self.after(50, self.drain)

    def field(self, parent, title, initial):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=12, pady=5)
        ctk.CTkLabel(row, text=title, width=195, anchor='w').pack(side='left')
        field = ctk.CTkEntry(row, width=80)
        field.insert(0, initial)
        field.pack(side='left')
        return field

    def dispatch(self, callback):
        self.tasks.put(callback)

    def drain(self):
        try:
            while True:
                self.tasks.get_nowait()()
        except queue.Empty:
            pass
        self.after(50, self.drain)

    def note(self, message):
        self.logs.configure(state='normal')
        self.logs.insert('end', log_line(message) + '\n')
        self.logs.see('end')
        self.logs.configure(state='disabled')

    def stage(self, message, progress=None):
        if self.status.cget('text') != 'Status: ' + message:
            self.status.configure(text='Status: ' + message)
            self.note(message)
        if progress is not None:
            self.bar.set(max(0, min(1, progress)))

    def choose(self, description, pattern):
        return filedialog.askopenfilename(parent=self, filetypes=[(description, pattern), ('All files', '*.*')])

    def select_video(self):
        path = self.choose('Video', '*.mp4 *.mov *.mkv *.avi *.webm')
        if path:
            self.video = str(require_file(path, VIDEO))
            self.video_text.configure(text=self.video)
            self.note('Video loaded')

    def select_srt(self):
        path = self.choose('SRT', '*.srt')
        if path:
            try:
                require_file(path, {'.srt'})
                parse_srt(path)
                self.srt = path
                self.srt_text.configure(text='SRT: ' + path)
                self.note('SRT loaded')
            except ValueError as exc:
                messagebox.showerror('SRT', str(exc), parent=self)

    def select_audio(self):
        path = self.choose('Audio', '*.mp3 *.wav *.m4a *.aac *.flac')
        if path:
            self.audio = str(require_file(path, AUDIO))
            self.audio_text.configure(text='Audio: ' + self.audio)
            self.note('Audio loaded')

    def inputs(self):
        require_file(self.video, VIDEO)
        return Job(video=self.video, srt=self.srt or None, audio=self.audio or None, mode=self.mode.get(),
                   count=int(self.count.get()), minimum=int(self.minimum.get()), maximum=int(self.maximum.get()))

    def run_task(self, title, work, done):
        if self.busy:
            messagebox.showinfo('Busy', 'Please wait for the current task to finish.', parent=self)
            return
        self.busy = True
        self.stage(title, 0)
        def runner():
            try:
                result = work()
            except Exception as exc:
                # Never surface raw SDK errors; local/validation errors are user-facing.
                if isinstance(exc, (ValueError, RuntimeError, FileNotFoundError)):
                    message = str(exc)
                else:
                    message = 'Operation failed. Check your inputs, FFmpeg installation and Gemini settings.'
                self.dispatch(lambda: self.fail(message))
            else:
                self.dispatch(lambda: self.finish(result, done))
        threading.Thread(target=runner, daemon=True).start()

    def fail(self, message):
        self.busy = False
        self.stage('Failed')
        messagebox.showerror('AI Shorts Maker', message, parent=self)

    def finish(self, result, done):
        self.busy = False
        self.stage('Ready', 1)
        done(result)

    def find(self, force=False):
        if self.busy:
            messagebox.showinfo('Busy', 'Please wait for the current task to finish.', parent=self)
            return
        try:
            job = self.inputs()
            cached = None if force else cached_analysis(job)
            if cached:
                job.shorts = cached[1]
                self.stage('Loaded cached analysis', 1)
                ResultsWindow(self, job)
                return
            key = load_key()
            if not key:
                raise ValueError('Set your Gemini API key in Settings first.')
        except Exception as exc:
            messagebox.showerror('Inputs', str(exc), parent=self)
            return
        def work():
            length = video_length(self.settings, job.video)
            self.dispatch(lambda: self.stage('Analyzing SRT' if job.mode == 'srt' else 'Uploading Audio to Gemini', .2))
            analysis, selected = analyze(job, self.settings, key, length, lambda text: self.dispatch(lambda message=text: self.stage(message, .55)))
            self.dispatch(lambda: self.stage('Selecting Shorts', .85))
            save_analysis(job, analysis, selected)
            return job
        self.run_task('Preparing Gemini request', work, lambda result: ResultsWindow(self, result))

    def open_project(self):
        path = self.choose('Project', '*.json')
        if path:
            try:
                job = load_project(path)
                self.video, self.srt, self.audio = job.video, job.srt or '', job.audio or ''
                self.video_text.configure(text=self.video)
                self.srt_text.configure(text='SRT: ' + (self.srt or 'none'))
                self.audio_text.configure(text='Audio: ' + (self.audio or 'none'))
                self.mode.set(job.mode)
                for field, value in [(self.count, job.count), (self.minimum, job.minimum), (self.maximum, job.maximum)]:
                    field.delete(0, 'end')
                    field.insert(0, str(value))
                if not job.shorts:
                    cached = cached_analysis(job)
                    if cached:
                        job.shorts = cached[1]
                self.note('Project loaded')
                if job.shorts:
                    ResultsWindow(self, job)
            except Exception as exc:
                messagebox.showerror('Project', str(exc), parent=self)
