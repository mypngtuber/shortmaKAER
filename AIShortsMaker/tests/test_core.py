import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.shorts import Analysis, Job, Short
from app.services.analyzer import select_candidates
from app.services.project import cached_analysis, save_analysis, load_project
from app.subtitles.parser import parse_srt
from app.subtitles.processor import write_segment
from app.utils.settings import Settings
from app.utils.timestamps import seconds, stamp
from app.gemini.manager import run
from app.video.ffmpeg import video_length
from app.video.processor import render

ROOT = Path(__file__).resolve().parents[1] / 'output'


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.video = self.folder / 'test.mp4'
        self.video.write_bytes(b'local video marker')
        self.srt = self.folder / 'source.srt'
        self.srt.write_text('1\n00:00:01,000 --> 00:00:03,000\nFirst line\n\n2\n00:00:03,000 --> 00:00:05,000\nSecond line\n', encoding='utf-8')

    def short(self, id, a, b, title):
        return Short(id=id, start=stamp(a), end=stamp(b), duration=b-a, title=title)

    def job(self):
        return Job(video=str(self.video), srt=str(self.srt), mode='srt', count=1, minimum=2, maximum=60)

    def test_timestamp_validation(self):
        self.assertEqual(seconds('02:03:04.500'), 7384.5)
        for value in ('00:60:00.000', '00:01:60.000', '1:01:01', '-1:01:01.000'):
            with self.assertRaises(ValueError):
                seconds(value)
        with self.assertRaises(ValueError):
            self.short(1, 10, 9, 'Invalid')

    def test_subtitle_clipping_and_shift(self):
        entries = parse_srt(str(self.srt))
        output = self.folder / 'shifted.srt'
        self.assertTrue(write_segment(entries, stamp(2), stamp(4), output))
        shifted = parse_srt(str(output))
        self.assertEqual(len(shifted), 2)
        self.assertEqual(shifted[0].start.total_seconds(), 0)
        self.assertEqual(shifted[1].end.total_seconds(), 2)
        self.assertFalse(write_segment(entries, stamp(6), stamp(8), output))

    def test_selection_and_cache_invalidated_when_source_changes(self):
        candidates = Analysis(shorts=[self.short(1, 1, 4, 'First'), self.short(2, 2, 5, 'Overlap'),
                                      self.short(3, 8, 11, 'Independent'), self.short(4, 90, 94, 'Beyond')])
        chosen = select_candidates(candidates, 3, 2, 60, 20)
        self.assertEqual([x.id for x in chosen], [1, 2])
        job = self.job()
        save_analysis(job, candidates, chosen)
        self.assertEqual(len(cached_analysis(job)[1]), 2)
        self.assertEqual(len(load_project(str(self.folder / 'Shorts' / 'project.json')).shorts), 2)
        self.srt.write_text(self.srt.read_text() + '\nChanged', encoding='utf-8')
        self.assertIsNone(cached_analysis(job))

    @patch('app.gemini.manager.time.sleep')
    @patch('app.gemini.manager.analyze_once')
    def test_retries_and_fallback_serial(self, request, sleep):
        request.side_effect = [TimeoutError(), TimeoutError(), '{"shorts": []}']
        settings = Settings(primary_model='primary', fallback_models=['fallback'], retry_attempts=2)
        self.assertEqual(run('secret', settings, 'prompt', 'SRT', None, lambda _: None), '{"shorts": []}')
        self.assertEqual([x.args[1] for x in request.call_args_list], ['primary', 'primary', 'fallback'])
        self.assertEqual(sleep.call_count, 1)
        self.assertTrue(all('secret' not in str(call) for call in sleep.call_args_list))

    @patch('app.gemini.client.genai.Client')
    @patch('app.gemini.manager.analyze_once')
    def test_large_audio_uploaded_once_and_deleted(self, request, client_factory):
        from types import SimpleNamespace
        audio = self.folder / 'speech.mp3'
        with audio.open('wb') as stream:
            stream.truncate(16 * 1024 * 1024)
        uploaded = SimpleNamespace(name='files/speech', uri='https://generativelanguage.googleapis.com/files/speech',
                                   mime_type='audio/mpeg', state=SimpleNamespace(name='ACTIVE'))
        client_factory.return_value.files.upload.return_value = uploaded
        request.side_effect = [TimeoutError(), '{"shorts": []}']
        settings = Settings(primary_model='first', fallback_models=['second'], retry_attempts=1)
        self.assertEqual(run('secret', settings, 'prompt', None, str(audio), lambda _: None), '{"shorts": []}')
        client_factory.return_value.files.upload.assert_called_once()
        client_factory.return_value.files.delete.assert_called_once_with(name='files/speech')
        self.assertEqual([call.args[1] for call in request.call_args_list], ['first', 'second'])

    def test_real_ffmpeg_render(self):
        import subprocess
        from app.video.ffmpeg import executable
        settings = Settings()
        subprocess.run([executable(settings), '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=180x320:r=10',
                        '-t', '2', '-c:v', 'mpeg4', '-y', str(self.video)], check=True)
        self.assertAlmostEqual(video_length(settings, str(self.video)), 2, delta=.1)
        destination = self.folder / 'out.mp4'
        from app.video.captions import caption_file
        caption = caption_file(str(self.srt), stamp(0), stamp(2), self.folder, 'captions')
        render(settings, str(self.video), self.short(1, 0, 2, 'Test'), destination, caption, lambda _: None)
        self.assertTrue(destination.stat().st_size > 0)


if __name__ == '__main__':
    unittest.main()
