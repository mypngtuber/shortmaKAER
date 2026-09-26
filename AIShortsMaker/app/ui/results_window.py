from tkinter import messagebox
import customtkinter as ctk
from app.models.shorts import Short
from app.services.project import save_project, update_selected
from app.services.exporter import export_one
from app.video.preview import create_preview
from app.video.ffmpeg import video_length
from app.utils.timestamps import seconds
from app.ui.preview_window import PreviewWindow


class ResultsWindow(ctk.CTkToplevel):
    def __init__(self, owner, job):
        super().__init__(owner)
        self.owner, self.job = owner, job
        self.title(f'Shorts Found: {len(job.shorts)}')
        self.geometry('760x760')
        self.minsize(540, 490)
        self.selection = {}
        self.progress_bars = {}
        self.select_all = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self, text='Select All', variable=self.select_all, command=self.toggle_all).pack(anchor='w', padx=22, pady=12)
        self.listing = ctk.CTkScrollableFrame(self)
        self.listing.pack(fill='both', expand=True, padx=18)
        self.selected_label = ctk.CTkLabel(self, text='')
        self.selected_label.pack(pady=8)
        ctk.CTkButton(self, text='EXPORT SELECTED', height=42, command=self.export_selected).pack(pady=10)
        self.draw()

    def draw(self):
        for child in self.listing.winfo_children():
            child.destroy()
        self.selection.clear()
        self.progress_bars.clear()
        for short in self.job.shorts:
            card = ctk.CTkFrame(self.listing)
            card.pack(fill='x', padx=10, pady=7)
            choice = ctk.BooleanVar(value=True)
            self.selection[short.id] = choice
            ctk.CTkCheckBox(card, text=f'Short #{short.id}: {short.title}', variable=choice,
                            command=self.update_count, font=ctk.CTkFont(size=16, weight='bold')).pack(anchor='w', padx=15, pady=10)
            ctk.CTkLabel(card, text=f'{short.start} → {short.end}   |   {short.duration:.1f} sec',
                         anchor='w').pack(fill='x', padx=20)
            ctk.CTkLabel(card, text=short.hook + '\n' + short.reason, anchor='w', justify='left', wraplength=610).pack(fill='x', padx=20, pady=5)
            buttons = ctk.CTkFrame(card, fg_color='transparent')
            buttons.pack(anchor='w', padx=15, pady=5)
            ctk.CTkButton(buttons, text='Create Preview', width=125, command=lambda s=short: self.preview(s)).pack(side='left', padx=4)
            ctk.CTkButton(buttons, text='Edit', width=75, command=lambda s=short: self.edit(s)).pack(side='left', padx=4)
            ctk.CTkButton(buttons, text='Export', width=75, command=lambda s=short: self.export([s])).pack(side='left', padx=4)
            bar = ctk.CTkProgressBar(card)
            bar.pack(fill='x', padx=20, pady=8)
            bar.set(0)
            self.progress_bars[short.id] = bar
        self.update_count()

    def toggle_all(self):
        for choice in self.selection.values():
            choice.set(self.select_all.get())
        self.update_count()

    def update_count(self):
        count = sum(x.get() for x in self.selection.values())
        self.selected_label.configure(text=f'Selected: {count} / {len(self.job.shorts)}')
        self.select_all.set(count == len(self.job.shorts))

    def edit(self, short):
        dialog = ctk.CTkToplevel(self)
        dialog.title('Edit Short')
        dialog.geometry('430x280')
        dialog.transient(self)
        dialog.grab_set()
        fields = {}
        for name, value in [('Start', short.start), ('End', short.end), ('Title', short.title)]:
            line = ctk.CTkFrame(dialog, fg_color='transparent')
            line.pack(fill='x', padx=18, pady=9)
            ctk.CTkLabel(line, text=name, width=55).pack(side='left')
            field = ctk.CTkEntry(line)
            field.insert(0, value)
            field.pack(side='left', fill='x', expand=True)
            fields[name] = field
        def update():
            try:
                a, b = seconds(fields['Start'].get()), seconds(fields['End'].get())
                if b > video_length(self.owner.settings, self.job.video) + .05:
                    raise ValueError('End time is beyond the video duration.')
                updated = Short(id=short.id, start=fields['Start'].get(), end=fields['End'].get(),
                                duration=round(b-a, 3), title=fields['Title'].get(), hook=short.hook, reason=short.reason)
                self.job.shorts[self.job.shorts.index(short)] = updated
                save_project(self.job)
                update_selected(self.job)
                dialog.destroy()
                self.draw()
                self.owner.note(f'Short {short.id} updated locally')
            except Exception as exc:
                messagebox.showerror('Invalid Short', str(exc), parent=dialog)
        ctk.CTkButton(dialog, text='Update', command=update).pack(side='left', padx=55, pady=15)
        ctk.CTkButton(dialog, text='Cancel', command=dialog.destroy).pack(side='right', padx=55, pady=15)

    def preview(self, short):
        def work():
            return create_preview(self.job, short, self.owner.settings,
                lambda v: self.owner.dispatch(lambda value=v: self.progress_bars.get(short.id) and self.progress_bars[short.id].set(value)))
        self.owner.run_task('Creating Preview', work, lambda file: PreviewWindow(self, file))

    def export_selected(self):
        self.export([x for x in self.job.shorts if self.selection[x.id].get()])

    def export(self, shorts):
        if not shorts:
            messagebox.showinfo('Export', 'Select at least one Short.', parent=self)
            return
        def work():
            files = []
            for index, short in enumerate(shorts):
                self.owner.dispatch(lambda s=short: self.owner.stage(f'Exporting Short {s.id:02}', 0))
                def update(value, s=short, i=index):
                    self.owner.dispatch(lambda v=value, item=s: self.progress_bars.get(item.id) and self.progress_bars[item.id].set(v))
                    self.owner.dispatch(lambda v=value, item=s, position=i: self.owner.stage(f'Exporting Short {item.id:02}', (position+v)/len(shorts)))
                files.append(export_one(self.job, short, self.owner.settings, update))
            return files
        self.owner.run_task('Exporting Shorts', work, lambda files: messagebox.showinfo('Export complete',
                            f'{len(files)} Shorts saved to:\n{files[0].parent}', parent=self))
