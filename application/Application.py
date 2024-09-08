import sys
import vlc
from PIL import Image, ImageQt
from PyQt5.QtCore import QTimer, QCoreApplication
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow
from PyQt5.uic.properties import QtGui
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1
from io import BytesIO
from application.ui.mp3_ui import Ui_Mp3Player


class MP3MetadataReader:
    def read(self, file_path):
        # MP3 파일에서 메타데이터를 추출
        try:
            audio = MP3(file_path, ID3=ID3)
            mp3_info = {'title': None, 'artist': None, 'album_art': None}

            if audio.tags is not None:
                for tag in audio.tags.values():
                    if isinstance(tag, TIT2):  # 제목 추출
                        mp3_info['title'] = tag.text[0]
                    elif isinstance(tag, TPE1):  # 가수 추출
                        mp3_info['artist'] = tag.text[0]
                    elif isinstance(tag, APIC):  # 앨범 이미지 추출
                        try:
                            img = Image.open(BytesIO(tag.data))
                            mp3_info['album_art'] = img
                        except Exception as img_error:
                            print(f"Error loading album art: {img_error}")
                            mp3_info['album_art'] = None

            return mp3_info

        except Exception as e:
            print(f"Error reading MP3 metadata: {e}")
            return None


MILLISECONDS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60


def milliseconds_to_minutes_seconds(milliseconds):
    seconds = milliseconds // MILLISECONDS_PER_SECOND
    minutes, seconds = divmod(seconds, SECONDS_PER_MINUTE)
    return minutes, seconds


def time_formating(current_time, total_time):
    current_minutes, current_seconds = divmod(current_time, SECONDS_PER_MINUTE)
    total_minutes, total_seconds = divmod(total_time, SECONDS_PER_MINUTE)
    time_format = f"{current_minutes:02}:{current_seconds:02} / {total_minutes:02}:{total_seconds:02}"
    return time_format


def milliseconds_to_minutes_seconds(milliseconds):
    """밀리초를 분과 초로 변환"""
    seconds = milliseconds // MILLISECONDS_PER_SECOND
    minutes, seconds = divmod(seconds, 60)
    return minutes, seconds

def time_formating(current_time, total_time):
    """현재 시간과 총 시간을 포맷팅하여 반환"""
    current_minutes, current_seconds = divmod(current_time, 60)
    total_minutes, total_seconds = divmod(total_time, 60)
    return f"{current_minutes:02}:{current_seconds:02} / {total_minutes:02}:{total_seconds:02}"


class MP3Player(QMainWindow, Ui_Mp3Player):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.media_player: 'vlc.MediaPlayer' = vlc.MediaPlayer()
        self.metadata_reader: 'MP3MetadataReader' = MP3MetadataReader()

        # VLC 이벤트 매니저 설정
        self.event_manager = self.media_player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.on_time_changed)

        # 버튼 및 슬라이더에 기능 연결
        self.previousButton.clicked.connect(self.previous_track)
        self.playButton.clicked.connect(self.play_pause_track)
        self.nextButton.clicked.connect(self.next_track)
        self.volumeSlider.valueChanged.connect(self.change_volume)
        self.progressSlider.valueChanged.connect(self.seek_position)
        self.fileOpenAction.triggered.connect(self.open_file)

        # 볼륨 초기화
        self.media_player.audio_set_volume(50)
        self.volumeSlider.setValue(50)

        # 텍스트 스크롤 타이머 설정
        self.scroll_index = 0
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(400)  # 400ms마다 스크롤
        self.scroll_timer.timeout.connect(self.scroll_song_info)

    def on_time_changed(self, event):
        """재생 시간 변경 이벤트 핸들러"""
        total_time = self.media_player.get_length() // MILLISECONDS_PER_SECOND
        current_time = self.media_player.get_time() // MILLISECONDS_PER_SECOND

        if total_time > 0 and current_time > 0:
            self.songStateLabel.setText(time_formating(current_time, total_time))

    def scroll_song_info(self):
        """노래 제목과 가수를 스크롤하는 기능"""
        text = self.songInfoLabel.text()

        if len(text) > 20:
            self.scroll_index = (self.scroll_index + 1) % len(text)
            self.songInfoLabel.setText(text[self.scroll_index:] + text[:self.scroll_index])

    def previous_track(self):
        print("Previous track")

    def play_pause_track(self):
        """재생 및 일시 정지 처리"""
        if self.media_player.get_media() is None:
            print("No media loaded. Please open a file first.")
            return

        if self.media_player.is_playing():
            self.media_player.pause()
            self.playButton.setText("⏯️")
            self.scroll_timer.stop()  # 재생이 중지되면 스크롤도 중지
        else:
            self.media_player.play()
            self.playButton.setText("⏸️")
            self.scroll_timer.start()  # 재생이 시작되면 스크롤 시작

        print("Play/Pause track")

    def next_track(self):
        print("Next track")

    def change_volume(self, value):
        self.media_player.audio_set_volume(value)
        self.volumeLabel.setText(f"volume : {value}")
        print(f"Volume changed: {value}")

    def seek_position(self, value):
        if self.media_player.is_playing():
            length = self.media_player.get_length() / 1000
            self.media_player.set_time(int(value * length / 100) * 1000)
        print(f"Track position changed: {value}%")

    def open_file(self):

        """MP3 파일을 선택하여 로드하고, 메타데이터를 표시"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open MP3 File", "", "MP3 Files (*.mp3)")

        if file_name:
            media = vlc.Media(file_name)
            self.media_player.set_media(media)

            self.wait_for_media_to_load()

            # 미디어가 로드되면 타이머 시작 (스크롤 등)
            self.scroll_timer.start()

            # 음악을 로드 후 시간을 00:00 / 총 시간으로 표시
            total_length_ms = self.media_player.get_length()
            total_minutes, total_seconds = milliseconds_to_minutes_seconds(total_length_ms)
            self.songStateLabel.setText(f"00:00 / {total_minutes:02}:{total_seconds:02}")

            # 메타데이터 읽기
            mp3_info = self.metadata_reader.read(file_name)

            if mp3_info:
                title = mp3_info.get('title', 'Unknown Title')
                artist = mp3_info.get('artist', 'Unknown Artist')
                album_art = mp3_info.get('album_art')

                self.songInfoLabel.setText(f"Title: {title} : Artist: {artist}")

                if album_art:
                    qt_image = ImageQt.ImageQt(album_art)
                    pixmap = QtGui.QPixmap.fromImage(qt_image)
                    self.albumImage.setPixmap(pixmap)

            else:
                self.songInfoLabel.setText(f"Title: Unknown Title : Artist: Unknown Artist  ")

        else:
            raise Exception("No file selected. Please select an MP3 file to play.")

    def wait_for_media_to_load(self):
        """미디어가 로드될 때까지 대기"""
        while self.media_player.get_state() not in (vlc.State.Playing, vlc.State.Paused):
            # 이벤트 루프를 계속 돌려 UI가 멈추지 않도록 함
            QCoreApplication.processEvents()
            if self.media_player.get_state() == vlc.State.Error:
                raise Exception("Failed to load media.")
            print("미디어 로드 중...")


class Application:
    @classmethod
    def run(cls):
        app = QApplication(sys.argv)
        window = MP3Player()
        window.show()
        sys.exit(app.exec_())

