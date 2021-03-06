# PyQt5 Video player
import os
os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'
from PyQt5.QtCore import QDir, Qt, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QInputDialog,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget)
from PyQt5.QtWidgets import QMainWindow,QWidget, QPushButton, QAction
from PyQt5.QtGui import QIcon
import sys
import time

import pkg_resources
clock_icon_file = pkg_resources.resource_filename('pyecog2', 'icons/wall-clock.png')
play_icon_file = pkg_resources.resource_filename('pyecog2', 'icons/play.png')
pause_icon_file = pkg_resources.resource_filename('pyecog2', 'icons/pause.png')

class VideoWindow(QWidget):
    sigTimeChanged = pyqtSignal(object)

    def __init__(self, project=None, parent=None):
        super(VideoWindow, self).__init__(parent)
        self.project = project
        self.setWindowTitle("Video")
        self.mediaPlayer = QMediaPlayer() #None, QMediaPlayer.VideoSurface)
        self.last_position = 0
        self.position_on_new_file = 0
        self.duration = -1
        self.waiting_for_file = False
        self.media_state_before_file_transition = self.mediaPlayer.state()
        self.video_time_offset = 0.0

        self.play_icon = QIcon(play_icon_file)
        self.clock_icon = QIcon(clock_icon_file)
        self.pause_icon = QIcon(pause_icon_file)

        videoWidget = QVideoWidget()
        self.videoWidget = videoWidget
        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.play_icon)
        self.playButton.clicked.connect(self.play)

        self.timeOffsetButton = QPushButton()
        self.timeOffsetButton.setIcon(self.clock_icon)
        self.timeOffsetButton.clicked.connect(self.setTimeOffset)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.errorLabel = QLabel()
        self.errorLabel.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Maximum)

        # Create layouts to place inside widget
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.timeOffsetButton)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.positionSlider)

        layout = QVBoxLayout()
        layout.addWidget(videoWidget)
        layout.addLayout(controlLayout)
        layout.addWidget(self.errorLabel)   # Hide error Label

        # Set widget to contain window contents
        self.setLayout(layout)

        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.mediaStatusChanged.connect(self.mediaStatusChanged)
        self.mediaPlayer.error.connect(self.handleError)
        self.mediaPlayer.setNotifyInterval(40) # 25 fps

        if self.project is None:
            self.current_time_range = [0,0]
            self.current_file = ''
            # self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.current_file)))
            # self.playButton.setEnabled(True)
            # self.mediaPlayer.play()
        elif self.project.current_animal.video_files:
            self.current_file = self.project.current_animal.video_files[0]
            self.current_time_range = [self.project.current_animal.video_init_time[0],
                                   self.project.current_animal.video_init_time[0] + self.project.current_animal.video_duration[0]]
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.current_file)))
            self.playButton.setEnabled(True)
        else:
            self.current_file = ''
            self.current_time_range = [0,0]

    def setTimeOffset(self):
        offset, okpressed = QInputDialog.getDouble(self,'Video time offset',
                                                   'Offset video time position (seconds)',
                                                   value = self.video_time_offset)
        if okpressed:
            self.video_time_offset = offset
            current_position = self.current_time_range[0] + self.last_position/1000
            self.setGlobalPosition(0)
            self.setGlobalPosition(current_position)


    def openFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Movie",
                QDir.homePath())

        if fileName != '':
            self.mediaPlayer.setMedia(
                    QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)

    def exitCall(self):
        sys.exit(app.exec_())

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(self.pause_icon)
        else:
            self.playButton.setIcon(self.play_icon)

    def positionChanged(self, position):
        # Connected to video player
        # print('positionChanged',position,self.last_position,self.waiting_for_file,self.duration,self.current_time_range)
        # if self.duration == -1:
        #     print('positionChanged: no file - duration ==-1')
        #     return
        # if self.waiting_for_file:
        #     print('positionChanged: Waiting to load file')
        #     return
        # if position == 0:
        #     print('positionChanged: avoiding setting positions to 0')
        #     return
        if position == 0 or self.waiting_for_file or self.duration == -1 or position == self.last_position:
            # avoid position changes on file transitions or repeated signals on same position
            return
        if position < self.duration-40:  # avoid time changes when switching files
            self.last_position = position
            self.positionSlider.setValue(position)
            self.sigTimeChanged.emit(position/1000 + self.current_time_range[0])
        else: # position is at the end of file - try to switch to next file
            pos = self.current_time_range[1] + .04
            print('Trying to jump to next file',self.current_time_range[1],self.duration,pos)
            self.setGlobalPosition(pos)

    def durationChanged(self, duration):
        # print('duration changed',duration)
        self.duration = duration
        self.positionSlider.setRange(0, duration)
        self.mediaPlayer.setPosition(self.position_on_new_file) # if duration changes avoid the position going back to 0

    def setPosition(self, position):
        # connected to slider
        # print('setPosition',position)
        self.mediaPlayer.setPosition(position) #  milliseconds since the beginning of the media

    def setGlobalPosition(self, pos):
        # Connected to project main model sigTimeChanged
        # open the right media
        if self.current_time_range[0] <= pos <= self.current_time_range[1]: # correct file opened
            position = int((pos-self.current_time_range[0])*1000)
            if self.mediaPlayer.state() == QMediaPlayer.PlayingState and abs(position-self.last_position)<200:
                # skip position setting by signal of main model to ensure smooth video plaback
                return
            # go to correct relative position
            self.mediaPlayer.setPosition(position)  # UNIX time
            return
        else:
            for i, file in enumerate(self.project.current_animal.video_files): # search for file to open
                arange = [self.project.current_animal.video_init_time[i] + self.video_time_offset,
                          self.project.current_animal.video_init_time[i] + self.project.current_animal.video_duration[i]
                          + self.video_time_offset]
                if (arange[0] <= pos <= arange[1]):
                    print('Changing video file: ', file)
                    self.current_file = file
                    self.errorLabel.setText("File: " + self.current_file)
                    self.current_time_range = arange
                    self.waiting_for_file = True
                    self.media_state_before_file_transition = self.mediaPlayer.state()
                    self.mediaPlayer.stop()
                    position = (pos-self.current_time_range[0])*1000
                    self.position_on_new_file = int(position)
                    # print('Changing position_on_new_file: ', self.position_on_new_file,pos)
                    self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(file)))
                    self.playButton.setEnabled(True)
                    # self.duration = (arange[1]-arange[0])*1000
                    return
        print('no video file found for current position')
        self.errorLabel.setText("No video file found for current position")
        self.mediaPlayer.stop()
        self.mediaPlayer.setMedia(QMediaContent())
        self.current_file = ''
        self.current_time_range = [0, 0]
        # self.duration = 0
        self.playButton.setEnabled(False)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.setValue(0)

    def mediaStatusChanged(self,status):
        if self.waiting_for_file:
            if self.mediaPlayer.mediaStatus() == QMediaPlayer.LoadedMedia:
                self.waiting_for_file = False
                # print('finished loading file')
                # self.mediaPlayer.stop()
                self.mediaPlayer.setPosition(self.position_on_new_file)
                self.mediaPlayer.play()
                time.sleep(.05)
                self.mediaPlayer.pause()
                if self.media_state_before_file_transition == QMediaPlayer.PlayingState:
                    self.mediaPlayer.play()
                # print('finished setting position on new file')


    def handleError(self):
        self.playButton.setEnabled(False)
        self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())
        print("Video - Error: " + self.mediaPlayer.errorString())


    # def reset(self):
    #     self.mediaPlayer = QMediaPlayer() #None, QMediaPlayer.VideoSurface)
    #     self.last_position = 0
    #     self.position_on_new_file = 0
    #     self.duration = -1
    #     self.waiting_for_file = False
    #     self.media_state_before_file_transition = self.mediaPlayer.state()
    #
    #     videoWidget = QVideoWidget()
    #     self.videoWidget = videoWidget
    #     self.playButton = QPushButton()
    #     self.playButton.setEnabled(False)
    #     self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
    #     self.playButton.clicked.connect(self.play)
    #
    #     self.positionSlider = QSlider(Qt.Horizontal)
    #     self.positionSlider.setRange(0, 0)
    #     self.positionSlider.sliderMoved.connect(self.setPosition)
    #
    #     self.errorLabel = QLabel()
    #     self.errorLabel.setSizePolicy(QSizePolicy.Preferred,
    #             QSizePolicy.Maximum)
    #
    #     # Create layouts to place inside widget
    #     controlLayout = QHBoxLayout()
    #     controlLayout.setContentsMargins(0, 0, 0, 0)
    #     controlLayout.addWidget(self.playButton)
    #     controlLayout.addWidget(self.positionSlider)
    #
    #     layout = QVBoxLayout()
    #     layout.addWidget(videoWidget)
    #     layout.addLayout(controlLayout)
    #     layout.addWidget(self.errorLabel)   # Hide error Label
    #
    #     # Set widget to contain window contents
    #     self.setLayout(layout)
    #
    #     self.mediaPlayer.setVideoOutput(videoWidget)
    #     self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
    #     self.mediaPlayer.positionChanged.connect(self.positionChanged)
    #     self.mediaPlayer.durationChanged.connect(self.durationChanged)
    #     self.mediaPlayer.mediaStatusChanged.connect(self.mediaStatusChanged)
    #     self.mediaPlayer.error.connect(self.handleError)
    #
    #     if self.project is None:
    #         self.current_time_range = [0,0]
    #         self.current_file = ''
    #         # self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.current_file)))
    #         # self.playButton.setEnabled(True)
    #         # self.mediaPlayer.play()
    #     elif self.project.current_animal.video_files:
    #         self.current_file = self.project.current_animal.video_files[0]
    #         self.current_time_range = [self.project.current_animal.video_init_time[0],
    #                                self.project.current_animal.video_init_time[0] + self.project.current_animal.video_duration[0]]
    #         self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.current_file)))
    #         self.playButton.setEnabled(True)
    #     else:
    #         self.current_file = ''
    #         self.current_time_range = [0,0]
    #
    #     self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec_())