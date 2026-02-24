# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QMainWindow, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QTextBrowser,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(1040, 851)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.actiontest = QAction(MainWindow)
        self.actiontest.setObjectName(u"actiontest")
        icon = QIcon()
        iconThemeName = u"battery"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u"../../../../../.designer/.designer/.designer/.designer/backup", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.actiontest.setIcon(icon)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_4 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.frame_top = QFrame(self.centralwidget)
        self.frame_top.setObjectName(u"frame_top")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(80)
        sizePolicy1.setHeightForWidth(self.frame_top.sizePolicy().hasHeightForWidth())
        self.frame_top.setSizePolicy(sizePolicy1)
        self.frame_top.setMinimumSize(QSize(0, 400))
        self.frame_top.setFrameShape(QFrame.StyledPanel)
        self.frame_top.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_top)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.frame_left = QFrame(self.frame_top)
        self.frame_left.setObjectName(u"frame_left")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(25)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.frame_left.sizePolicy().hasHeightForWidth())
        self.frame_left.setSizePolicy(sizePolicy2)
        self.frame_left.setFrameShape(QFrame.StyledPanel)
        self.frame_left.setFrameShadow(QFrame.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frame_left)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.tableWidget_bue = QTableWidget(self.frame_left)
        if (self.tableWidget_bue.columnCount() < 3):
            self.tableWidget_bue.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.tableWidget_bue.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tableWidget_bue.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tableWidget_bue.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.tableWidget_bue.setObjectName(u"tableWidget_bue")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(75)
        sizePolicy3.setHeightForWidth(self.tableWidget_bue.sizePolicy().hasHeightForWidth())
        self.tableWidget_bue.setSizePolicy(sizePolicy3)
        self.tableWidget_bue.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tableWidget_bue.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_bue.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tableWidget_bue.setShowGrid(True)
        self.tableWidget_bue.setGridStyle(Qt.SolidLine)
        self.tableWidget_bue.setRowCount(0)
        self.tableWidget_bue.horizontalHeader().setVisible(True)
        self.tableWidget_bue.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget_bue.horizontalHeader().setMinimumSectionSize(73)
        self.tableWidget_bue.horizontalHeader().setDefaultSectionSize(73)
        self.tableWidget_bue.horizontalHeader().setHighlightSections(True)
        self.tableWidget_bue.horizontalHeader().setStretchLastSection(False)
        self.tableWidget_bue.verticalHeader().setVisible(False)
        self.tableWidget_bue.verticalHeader().setCascadingSectionResizes(False)
        self.tableWidget_bue.verticalHeader().setProperty(u"showSortIndicator", False)
        self.tableWidget_bue.verticalHeader().setStretchLastSection(False)

        self.verticalLayout_7.addWidget(self.tableWidget_bue)

        self.groupBox_controls = QGroupBox(self.frame_left)
        self.groupBox_controls.setObjectName(u"groupBox_controls")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(25)
        sizePolicy4.setHeightForWidth(self.groupBox_controls.sizePolicy().hasHeightForWidth())
        self.groupBox_controls.setSizePolicy(sizePolicy4)
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_controls)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.button_run_tests = QPushButton(self.groupBox_controls)
        self.button_run_tests.setObjectName(u"button_run_tests")

        self.verticalLayout_2.addWidget(self.button_run_tests)

        self.button_cancel_tests = QPushButton(self.groupBox_controls)
        self.button_cancel_tests.setObjectName(u"button_cancel_tests")

        self.verticalLayout_2.addWidget(self.button_cancel_tests)

        self.button_switch_map_type = QPushButton(self.groupBox_controls)
        self.button_switch_map_type.setObjectName(u"button_switch_map_type")

        self.verticalLayout_2.addWidget(self.button_switch_map_type)


        self.verticalLayout_7.addWidget(self.groupBox_controls)


        self.horizontalLayout.addWidget(self.frame_left)

        self.frame_middle = QFrame(self.frame_top)
        self.frame_middle.setObjectName(u"frame_middle")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy5.setHorizontalStretch(50)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.frame_middle.sizePolicy().hasHeightForWidth())
        self.frame_middle.setSizePolicy(sizePolicy5)
        self.frame_middle.setFrameShape(QFrame.StyledPanel)
        self.frame_middle.setFrameShadow(QFrame.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.frame_middle)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.frame_map = QFrame(self.frame_middle)
        self.frame_map.setObjectName(u"frame_map")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(60)
        sizePolicy6.setHeightForWidth(self.frame_map.sizePolicy().hasHeightForWidth())
        self.frame_map.setSizePolicy(sizePolicy6)
        self.frame_map.setMinimumSize(QSize(0, 0))
        self.frame_map.setFrameShape(QFrame.StyledPanel)
        self.frame_map.setFrameShadow(QFrame.Raised)

        self.verticalLayout_6.addWidget(self.frame_map)

        self.group_messages = QGroupBox(self.frame_middle)
        self.group_messages.setObjectName(u"group_messages")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(40)
        sizePolicy7.setHeightForWidth(self.group_messages.sizePolicy().hasHeightForWidth())
        self.group_messages.setSizePolicy(sizePolicy7)
        self.group_messages.setMinimumSize(QSize(499, 0))
        self.verticalLayout_3 = QVBoxLayout(self.group_messages)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.textBrowser_messages = QTextBrowser(self.group_messages)
        self.textBrowser_messages.setObjectName(u"textBrowser_messages")
        sizePolicy8 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(1)
        sizePolicy8.setHeightForWidth(self.textBrowser_messages.sizePolicy().hasHeightForWidth())
        self.textBrowser_messages.setSizePolicy(sizePolicy8)

        self.verticalLayout_3.addWidget(self.textBrowser_messages)

        self.button_clear_messages = QPushButton(self.group_messages)
        self.button_clear_messages.setObjectName(u"button_clear_messages")
        sizePolicy.setHeightForWidth(self.button_clear_messages.sizePolicy().hasHeightForWidth())
        self.button_clear_messages.setSizePolicy(sizePolicy)

        self.verticalLayout_3.addWidget(self.button_clear_messages)


        self.verticalLayout_6.addWidget(self.group_messages)


        self.horizontalLayout.addWidget(self.frame_middle)

        self.frame_right = QFrame(self.frame_top)
        self.frame_right.setObjectName(u"frame_right")
        sizePolicy9 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy9.setHorizontalStretch(10)
        sizePolicy9.setVerticalStretch(0)
        sizePolicy9.setHeightForWidth(self.frame_right.sizePolicy().hasHeightForWidth())
        self.frame_right.setSizePolicy(sizePolicy9)
        self.frame_right.setMinimumSize(QSize(200, 0))
        self.frame_right.setFrameShape(QFrame.StyledPanel)
        self.frame_right.setFrameShadow(QFrame.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame_right)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.tableWidget_coords = QTableWidget(self.frame_right)
        if (self.tableWidget_coords.columnCount() < 2):
            self.tableWidget_coords.setColumnCount(2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tableWidget_coords.setHorizontalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tableWidget_coords.setHorizontalHeaderItem(1, __qtablewidgetitem4)
        self.tableWidget_coords.setObjectName(u"tableWidget_coords")
        sizePolicy.setHeightForWidth(self.tableWidget_coords.sizePolicy().hasHeightForWidth())
        self.tableWidget_coords.setSizePolicy(sizePolicy)
        self.tableWidget_coords.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_coords.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tableWidget_coords.setColumnCount(2)
        self.tableWidget_coords.horizontalHeader().setDefaultSectionSize(75)
        self.tableWidget_coords.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_coords.verticalHeader().setVisible(False)

        self.verticalLayout_5.addWidget(self.tableWidget_coords)

        self.tableWidget_distances = QTableWidget(self.frame_right)
        if (self.tableWidget_distances.columnCount() < 2):
            self.tableWidget_distances.setColumnCount(2)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tableWidget_distances.setHorizontalHeaderItem(0, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tableWidget_distances.setHorizontalHeaderItem(1, __qtablewidgetitem6)
        self.tableWidget_distances.setObjectName(u"tableWidget_distances")
        sizePolicy.setHeightForWidth(self.tableWidget_distances.sizePolicy().hasHeightForWidth())
        self.tableWidget_distances.setSizePolicy(sizePolicy)
        self.tableWidget_distances.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_distances.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tableWidget_distances.setWordWrap(False)
        self.tableWidget_distances.setColumnCount(2)
        self.tableWidget_distances.horizontalHeader().setVisible(True)
        self.tableWidget_distances.horizontalHeader().setCascadingSectionResizes(False)
        self.tableWidget_distances.horizontalHeader().setMinimumSectionSize(50)
        self.tableWidget_distances.horizontalHeader().setDefaultSectionSize(88)
        self.tableWidget_distances.horizontalHeader().setHighlightSections(False)
        self.tableWidget_distances.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_distances.verticalHeader().setVisible(False)

        self.verticalLayout_5.addWidget(self.tableWidget_distances)


        self.horizontalLayout.addWidget(self.frame_right)


        self.verticalLayout_4.addWidget(self.frame_top)

        self.frame_base_station_log = QFrame(self.centralwidget)
        self.frame_base_station_log.setObjectName(u"frame_base_station_log")
        sizePolicy10 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy10.setHorizontalStretch(0)
        sizePolicy10.setVerticalStretch(20)
        sizePolicy10.setHeightForWidth(self.frame_base_station_log.sizePolicy().hasHeightForWidth())
        self.frame_base_station_log.setSizePolicy(sizePolicy10)
        self.frame_base_station_log.setMinimumSize(QSize(0, 0))

        self.verticalLayout_4.addWidget(self.frame_base_station_log)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Base Station", None))
        self.actiontest.setText(QCoreApplication.translate("MainWindow", u"test", None))
#if QT_CONFIG(tooltip)
        self.actiontest.setToolTip(QCoreApplication.translate("MainWindow", u"test", None))
#endif // QT_CONFIG(tooltip)
        ___qtablewidgetitem = self.tableWidget_bue.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"bUE", None));
        ___qtablewidgetitem1 = self.tableWidget_bue.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"State", None));
        ___qtablewidgetitem2 = self.tableWidget_bue.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MainWindow", u"Pings", None));
        self.groupBox_controls.setTitle(QCoreApplication.translate("MainWindow", u"Controls", None))
        self.button_run_tests.setText(QCoreApplication.translate("MainWindow", u"Run Tests", None))
        self.button_cancel_tests.setText(QCoreApplication.translate("MainWindow", u"Cancel Tests", None))
        self.button_switch_map_type.setText(QCoreApplication.translate("MainWindow", u"Switch Map Type", None))
        self.group_messages.setTitle(QCoreApplication.translate("MainWindow", u"Messages", None))
        self.button_clear_messages.setText(QCoreApplication.translate("MainWindow", u"Clear Messages", None))
        ___qtablewidgetitem3 = self.tableWidget_coords.horizontalHeaderItem(0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MainWindow", u"bUE", None));
        ___qtablewidgetitem4 = self.tableWidget_coords.horizontalHeaderItem(1)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MainWindow", u"Coords", None));
        ___qtablewidgetitem5 = self.tableWidget_distances.horizontalHeaderItem(0)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MainWindow", u"bUEs", None));
        ___qtablewidgetitem6 = self.tableWidget_distances.horizontalHeaderItem(1)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MainWindow", u"Distances (m)", None));
    # retranslateUi

