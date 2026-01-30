"""
다이얼로그 클래스들
- SettingsDialog: 설정 대화상자
- UserChatDialog: 사용자 채팅 기록 팝업
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget
)


class SettingsDialog(QDialog):
    """설정 다이얼로그"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('설정')
        self.setFixedSize(300, 150)
        self.setStyleSheet('''
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #cccccc;
            }
            QSpinBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                padding: 5px;
                border-radius: 4px;
            }
        ''')

        layout = QVBoxLayout(self)

        # 폰트 크기 설정
        form_layout = QFormLayout()

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.settings.get('font_size', 10))
        self.font_size_spin.setSuffix(' pt')
        form_layout.addRow('채팅 폰트 크기:', self.font_size_spin)

        layout.addLayout(form_layout)
        layout.addStretch()

        # 버튼
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet('''
            QPushButton {
                background-color: #3d3d3d;
                color: #cccccc;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        ''')
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        """변경된 설정 반환"""
        return {
            'font_size': self.font_size_spin.value()
        }


class UserChatDialog(QDialog):
    """특정 사용자의 채팅 기록을 보여주는 팝업"""

    def __init__(self, uid, nickname, messages, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.nickname = nickname
        self.messages = messages
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'{self.nickname}의 채팅 기록')
        self.resize(450, 400)  # 크기만 설정 (위치는 parent에서 지정)
        self.setStyleSheet('''
            QDialog {
                background-color: #2b2b2b;
            }
        ''')

        layout = QVBoxLayout(self)

        # 사용자 정보 헤더
        header = QLabel(f'''
            <div style="padding: 10px;">
                <span style="color: #00ff00; font-size: 16px; font-weight: bold;">{self.nickname}</span><br>
                <span style="color: #666666; font-size: 11px;">UID: {self.uid}</span><br>
                <span style="color: #888888; font-size: 12px;">총 {len(self.messages)}개의 메시지</span>
            </div>
        ''')
        header.setStyleSheet('background-color: #1f1f1f; border-radius: 5px;')
        layout.addWidget(header)

        # 채팅 기록 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet('''
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
        ''')

        chat_widget = QWidget()
        chat_widget.setStyleSheet('background-color: #1a1a1a;')
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setSpacing(2)

        for msg in self.messages:
            msg_label = QLabel(f'''
                <span style="color: #888888;">[{msg['time']}]</span>
                <span style="color: {'#ffcc00' if msg['type'] == '후원' else '#ffffff'};">{msg['message']}</span>
            ''')
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet('padding: 5px; background-color: #252525; border-radius: 3px;')
            chat_layout.addWidget(msg_label)

        chat_layout.addStretch()
        scroll_area.setWidget(chat_widget)
        layout.addWidget(scroll_area)
