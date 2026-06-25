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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QWidget)

class Ui_dialog_run_tests(object):
    def setupUi(self, dialog_run_tests):
        if not dialog_run_tests.objectName():
            dialog_run_tests.setObjectName(u"dialog_run_tests")
        dialog_run_tests.resize(943, 648)
        palette = QPalette()
        brush = QBrush(QColor(222, 221, 218, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Button, brush)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Window, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Button, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Window, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, brush)
        dialog_run_tests.setPalette(palette)
        dialog_run_tests.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        dialog_run_tests.setStyleSheet(u"background-color: rgb(222, 221, 218);")
        self.comboBox_select_test = QComboBox(dialog_run_tests)
        self.comboBox_select_test.setObjectName(u"comboBox_select_test")
        self.comboBox_select_test.setGeometry(QRect(580, 10, 341, 29))
        self.comboBox_select_test.setStyleSheet(u"color: rgb(0, 0, 0);")
        self.label = QLabel(dialog_run_tests)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(460, 10, 101, 31))
        self.label.setStyleSheet(u"color: rgb(0, 0, 0);")
        self.pushButton_cancel = QPushButton(dialog_run_tests)
        self.pushButton_cancel.setObjectName(u"pushButton_cancel")
        self.pushButton_cancel.setGeometry(QRect(860, 610, 71, 30))
        self.pushButton_cancel.setStyleSheet(u"color: rgb(224, 27, 36);")
        self.pushButton_run = QPushButton(dialog_run_tests)
        self.pushButton_run.setObjectName(u"pushButton_run")
        self.pushButton_run.setGeometry(QRect(780, 610, 71, 30))
        font = QFont()
        font.setBold(True)
        self.pushButton_run.setFont(font)
        self.pushButton_run.setStyleSheet(u"color: rgb(9, 131, 22);")
        self.label_2 = QLabel(dialog_run_tests)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(530, 610, 181, 31))
        self.label_2.setStyleSheet(u"color: rgb(0, 0, 0);")
        self.spinBox_delay_time = QSpinBox(dialog_run_tests)
        self.spinBox_delay_time.setObjectName(u"spinBox_delay_time")
        self.spinBox_delay_time.setGeometry(QRect(710, 610, 51, 30))
        self.spinBox_delay_time.setStyleSheet(u"color: rgb(0, 0, 0);")
        self.spinBox_delay_time.setMinimum(1)
        self.spinBox_delay_time.setValue(30)
        self.scrollArea_test_setup = QScrollArea(dialog_run_tests)
        self.scrollArea_test_setup.setObjectName(u"scrollArea_test_setup")
        self.scrollArea_test_setup.setGeometry(QRect(20, 50, 901, 551))
        self.scrollArea_test_setup.setStyleSheet(u"background-color: rgb(255, 255, 255);")
        self.scrollArea_test_setup.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 899, 549))
        self.scrollArea_test_setup.setWidget(self.scrollAreaWidgetContents)

        self.retranslateUi(dialog_run_tests)

        QMetaObject.connectSlotsByName(dialog_run_tests)
    # setupUi

    def retranslateUi(self, dialog_run_tests):
        dialog_run_tests.setWindowTitle(QCoreApplication.translate("dialog_run_tests", u"Dialog", None))
        self.comboBox_select_test.setCurrentText("")
        self.label.setText(QCoreApplication.translate("dialog_run_tests", u"Test to Run:", None))
        self.pushButton_cancel.setText(QCoreApplication.translate("dialog_run_tests", u"Cancel ", None))
        self.pushButton_run.setText(QCoreApplication.translate("dialog_run_tests", u"Run", None))
        self.label_2.setText(QCoreApplication.translate("dialog_run_tests", u"Run test in (seconds)", None))
    # retranslateUi

