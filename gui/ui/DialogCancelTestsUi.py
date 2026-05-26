# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_cancel_tests.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_dialog_cancel_tests(object):
    def setupUi(self, dialog_cancel_tests):
        if not dialog_cancel_tests.objectName():
            dialog_cancel_tests.setObjectName("dialog_cancel_tests")
        dialog_cancel_tests.resize(446, 336)
        self.verticalLayout = QVBoxLayout(dialog_cancel_tests)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QWidget(dialog_cancel_tests)
        self.widget.setObjectName("widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.horizontalLayout_2 = QHBoxLayout(self.widget)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.widget_bue_selection = QWidget(self.widget)
        self.widget_bue_selection.setObjectName("widget_bue_selection")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.widget_bue_selection.sizePolicy().hasHeightForWidth())
        self.widget_bue_selection.setSizePolicy(sizePolicy1)
        self.widget_bue_selection.setMinimumSize(QSize(400, 0))

        self.horizontalLayout_2.addWidget(self.widget_bue_selection)

        self.label = QLabel(self.widget)
        self.label.setObjectName("label")
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)
        self.label.setPixmap(QPixmap("/home/ty22117/bUE-lake-tests/gui/ui/image.png"))
        self.label.setScaledContents(True)

        self.horizontalLayout_2.addWidget(self.label)

        self.verticalLayout.addWidget(self.widget)

        self.widget_2 = QWidget(dialog_cancel_tests)
        self.widget_2.setObjectName("widget_2")
        sizePolicy1.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy1)
        self.horizontalLayout = QHBoxLayout(self.widget_2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.button_exit = QPushButton(self.widget_2)
        self.button_exit.setObjectName("button_exit")

        self.horizontalLayout.addWidget(self.button_exit)

        self.button_send_cancel = QPushButton(self.widget_2)
        self.button_send_cancel.setObjectName("button_send_cancel")

        self.horizontalLayout.addWidget(self.button_send_cancel)

        self.verticalLayout.addWidget(self.widget_2)

        self.retranslateUi(dialog_cancel_tests)

        QMetaObject.connectSlotsByName(dialog_cancel_tests)

    # setupUi

    def retranslateUi(self, dialog_cancel_tests):
        dialog_cancel_tests.setWindowTitle(QCoreApplication.translate("dialog_cancel_tests", "Cancel Tests", None))
        self.label.setText("")
        self.button_exit.setText(QCoreApplication.translate("dialog_cancel_tests", "Exit", None))
        self.button_send_cancel.setText(QCoreApplication.translate("dialog_cancel_tests", "Cancel Tests", None))

    # retranslateUi
