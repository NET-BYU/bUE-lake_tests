# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_run_tests.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QPushButton, QSizePolicy, QWidget)

class Ui_dialog_run_tests(object):
    def setupUi(self, dialog_run_tests):
        if not dialog_run_tests.objectName():
            dialog_run_tests.setObjectName(u"dialog_run_tests")
        dialog_run_tests.resize(400, 300)
        palette = QPalette()
        brush = QBrush(QColor(222, 221, 218, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Window, brush)
        brush1 = QBrush(QColor(255, 255, 255, 255))
        brush1.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Base, brush1)
        brush2 = QBrush(QColor(239, 239, 239, 255))
        brush2.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Window, brush2)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, brush2)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, brush)
        dialog_run_tests.setPalette(palette)
        dialog_run_tests.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.buttonBox = QDialogButtonBox(dialog_run_tests)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(30, 240, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.button_hello_world = QPushButton(dialog_run_tests)
        self.button_hello_world.setObjectName(u"button_hello_world")
        self.button_hello_world.setGeometry(QRect(210, 170, 141, 61))
        self.widget_bue_selection = QWidget(dialog_run_tests)
        self.widget_bue_selection.setObjectName(u"widget_bue_selection")
        self.widget_bue_selection.setGeometry(QRect(20, 20, 161, 131))
        self.pushButton_resp = QPushButton(dialog_run_tests)
        self.pushButton_resp.setObjectName(u"pushButton_resp")
        self.pushButton_resp.setGeometry(QRect(220, 40, 121, 51))
        self.pushButton_init = QPushButton(dialog_run_tests)
        self.pushButton_init.setObjectName(u"pushButton_init")
        self.pushButton_init.setGeometry(QRect(209, 110, 121, 41))

        self.retranslateUi(dialog_run_tests)
        self.buttonBox.accepted.connect(dialog_run_tests.accept)
        self.buttonBox.rejected.connect(dialog_run_tests.reject)

        QMetaObject.connectSlotsByName(dialog_run_tests)
    # setupUi

    def retranslateUi(self, dialog_run_tests):
        dialog_run_tests.setWindowTitle(QCoreApplication.translate("dialog_run_tests", u"Dialog", None))
        self.button_hello_world.setText(QCoreApplication.translate("dialog_run_tests", u"Run Hello World", None))
        self.pushButton_resp.setText(QCoreApplication.translate("dialog_run_tests", u"Resp", None))
        self.pushButton_init.setText(QCoreApplication.translate("dialog_run_tests", u"Init", None))
    # retranslateUi

