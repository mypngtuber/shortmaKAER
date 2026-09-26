import sys
from tkinter import messagebox
import customtkinter as ctk


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, file):
        super().__init__(parent)
        self.title('Preview - ' + file.name)
        self.geometry('530x810')
        self.minsize(330, 450)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.screen = ctk.CTkFrame(self, fg_color='black')
        self.screen.pack(fill='both', expand=True, padx=12, pady=8)
        bar = ctk.CTkFrame(self)
        bar.pack(fill='x', padx=12, pady=8)
        ctk.CTkButton(bar, text='Play / Pause', width=105, command=self.toggle).pack(side='left', padx=5)
        self.seeking = False
        self.seek = ctk.CTkSlider(bar, from_=0, to=1000, command=self.on_seek)
        self.seek.pack(side='left', fill='x', expand=True, padx=5)
        self.seek.bind('<ButtonPress-1>', self.start_seek, add='+')
        self.seek.bind('<ButtonRelease-1>', self.end_seek, add='+')
        self.seek.set(0)
        self.volume = ctk.CTkSlider(bar, from_=0, to=100, width=90, command=self.on_volume)
        self.volume.pack(side='left', padx=5)
        self.volume.set(80)
        ctk.CTkButton(bar, text='Fullscreen', width=95, command=self.fullscreen).pack(side='left', padx=5)
        try:
            import vlc
            self.instance = vlc.Instance('--no-video-title-show', '--quiet')
            self.player = self.instance.media_player_new()
            self.player.set_media(self.instance.media_new(str(file)))
            self.update_idletasks()
            if sys.platform == 'win32':
                self.player.set_hwnd(self.screen.winfo_id())
            elif sys.platform == 'darwin':
                self.player.set_nsobject(self.screen.winfo_id())
            else:
                self.player.set_xwindow(self.screen.winfo_id())
            self.player.audio_set_volume(80)
            self.player.play()
            self.after(500, self.tick)
        except Exception:
            messagebox.showerror('Preview', 'VLC could not start. Install the VLC desktop app (same architecture as Python).', parent=self)
            self.destroy()

    def tick(self):
        if not self.winfo_exists():
            return
        if self.player.get_length() > 0 and not self.seeking:
            self.seek.set(max(0, self.player.get_position()) * 1000)
        self.after(500, self.tick)

    def start_seek(self, _event):
        self.seeking = True

    def end_seek(self, _event):
        self.on_seek(self.seek.get())
        self.seeking = False

    def on_seek(self, value):
        if hasattr(self, 'player') and self.player.get_length() > 0 and self.seeking:
            self.player.set_position(value / 1000)

    def on_volume(self, value):
        if hasattr(self, 'player'):
            self.player.audio_set_volume(int(value))

    def toggle(self):
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()

    def fullscreen(self):
        self.attributes('-fullscreen', not bool(self.attributes('-fullscreen')))

    def close(self):
        if hasattr(self, 'player'):
            self.player.stop()
            self.player.release()
            self.instance.release()
        self.destroy()
