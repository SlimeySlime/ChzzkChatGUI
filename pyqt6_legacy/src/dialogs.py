"""
다이얼로그 클래스들
- SettingsDialog: 설정 대화상자
- UserChatDialog: 사용자 채팅 기록 팝업
- BugReportDialog: 버그 리포트
"""
import platform
import sys
from urllib.parse import quote

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget,
    QLineEdit, QTextEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices


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


class BugReportDialog(QDialog):
    """버그 리포트 다이얼로그"""

    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.email = email
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('버그 리포트')
        self.setFixedSize(450, 350)
        self.setStyleSheet('''
            QDialog { background-color: #2b2b2b; }
            QLabel { color: #cccccc; }
            QLineEdit, QTextEdit {
                background-color: #1a1a1a; color: #ffffff;
                border: 1px solid #333; padding: 6px; border-radius: 4px;
            }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #00ff00; }
        ''')

        layout = QVBoxLayout(self)

        # 제목
        layout.addWidget(QLabel('제목'))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('버그 제목을 입력하세요')
        layout.addWidget(self.title_input)

        # 설명
        layout.addWidget(QLabel('설명'))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText('어떤 상황에서 버그가 발생했나요?\n재현 방법이 있다면 알려주세요.')
        layout.addWidget(self.desc_input)

        # 시스템 정보
        self.sys_info = f'OS: {platform.system()} {platform.release()}, Python: {sys.version.split()[0]}'
        info_label = QLabel(f'<span style="color: #666;">{self.sys_info}</span>')
        layout.addWidget(info_label)

        # 전송 버튼
        send_btn = QPushButton('메일 클라이언트로 보내기')
        send_btn.setStyleSheet('''
            QPushButton {
                background-color: #00ff00; color: #000000;
                border: none; padding: 8px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00cc00; }
        ''')
        send_btn.clicked.connect(self.send_report)
        layout.addWidget(send_btn)

    def send_report(self):
        import logging
        logger = logging.getLogger(__name__)

        title = self.title_input.text().strip()
        desc = self.desc_input.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, '알림', '제목을 입력해주세요.')
            return

        subject = f'[ChzzkChat Bug] {title}'
        body = f'{desc}\n\n---\n{self.sys_info}'
        mailto_str = f'mailto:{self.email}?subject={quote(subject)}&body={quote(body)}'

        logger.info('버그리포트 mailto URL: %s', mailto_str)

        try:
            url = QUrl(mailto_str)
            logger.info('QUrl valid=%s, scheme=%s', url.isValid(), url.scheme())

            result = QDesktopServices.openUrl(url)
            logger.info('QDesktopServices.openUrl 결과: %s', result)

            if not result:
                # QDesktopServices 실패 시 webbrowser fallback
                import webbrowser
                webbrowser.open(mailto_str)
                logger.info('webbrowser.open fallback 사용')

            self.accept()
        except Exception:
            logger.exception('버그리포트 전송 실패')
            QMessageBox.warning(self, '오류', '메일 클라이언트를 열 수 없습니다.\n로그를 확인해주세요.')
