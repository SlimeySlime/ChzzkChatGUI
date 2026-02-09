"""
커스텀 위젯 클래스들
"""
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import pyqtSignal, Qt


class ClickableTextEdit(QTextEdit):
    """클릭 가능한 채팅 영역"""
    user_clicked = pyqtSignal(str)  # uid 전달

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            anchor = self.anchorAt(event.pos())
            if anchor and anchor.startswith('user:'):
                uid = anchor.replace('user:', '')
                self.user_clicked.emit(uid)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor and anchor.startswith('user:'):
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)
