# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'manageuserwidget.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_Manage_User_Form(object):
    def setupUi(self, Manage_User_Form):
        if not Manage_User_Form.objectName():
            Manage_User_Form.setObjectName(u"Manage_User_Form")
        Manage_User_Form.resize(500, 495)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Manage_User_Form.sizePolicy().hasHeightForWidth())
        Manage_User_Form.setSizePolicy(sizePolicy)
        icon = QIcon()
        icon.addFile(u"assets/icons/profile.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Manage_User_Form.setWindowIcon(icon)
        self.verticalLayout = QVBoxLayout(Manage_User_Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox = QGroupBox(Manage_User_Form)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.fname_input = QLineEdit(self.groupBox)
        self.fname_input.setObjectName(u"fname_input")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.fname_input.sizePolicy().hasHeightForWidth())
        self.fname_input.setSizePolicy(sizePolicy1)
        self.fname_input.setMinimumSize(QSize(100, 0))

        self.gridLayout.addWidget(self.fname_input, 0, 1, 1, 3)

        self.username_input = QLineEdit(self.groupBox)
        self.username_input.setObjectName(u"username_input")

        self.gridLayout.addWidget(self.username_input, 2, 2, 1, 1)

        self.lname_label = QLabel(self.groupBox)
        self.lname_label.setObjectName(u"lname_label")

        self.gridLayout.addWidget(self.lname_label, 1, 0, 1, 1)

        self.password_input = QLineEdit(self.groupBox)
        self.password_input.setObjectName(u"password_input")

        self.gridLayout.addWidget(self.password_input, 3, 2, 1, 1)

        self.username_label = QLabel(self.groupBox)
        self.username_label.setObjectName(u"username_label")

        self.gridLayout.addWidget(self.username_label, 2, 0, 1, 1)

        self.lname_input = QLineEdit(self.groupBox)
        self.lname_input.setObjectName(u"lname_input")

        self.gridLayout.addWidget(self.lname_input, 1, 2, 1, 2)

        self.fname_label = QLabel(self.groupBox)
        self.fname_label.setObjectName(u"fname_label")

        self.gridLayout.addWidget(self.fname_label, 0, 0, 1, 1)

        self.password_label = QLabel(self.groupBox)
        self.password_label.setObjectName(u"password_label")

        self.gridLayout.addWidget(self.password_label, 3, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.add_button = QPushButton(Manage_User_Form)
        self.add_button.setObjectName(u"add_button")
        icon1 = QIcon()
        icon1.addFile(u"assets/icons/add-user.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.add_button)

        self.update_button = QPushButton(Manage_User_Form)
        self.update_button.setObjectName(u"update_button")
        icon2 = QIcon()
        icon2.addFile(u"assets/icons/update.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.update_button.setIcon(icon2)

        self.horizontalLayout.addWidget(self.update_button)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tableWidget = QTableWidget(Manage_User_Form)
        self.tableWidget.setObjectName(u"tableWidget")

        self.verticalLayout.addWidget(self.tableWidget)

        self.edit_button = QPushButton(Manage_User_Form)
        self.edit_button.setObjectName(u"edit_button")
        icon3 = QIcon()
        icon3.addFile(u"assets/icons/edit.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.edit_button.setIcon(icon3)

        self.verticalLayout.addWidget(self.edit_button)

        self.delete_button = QPushButton(Manage_User_Form)
        self.delete_button.setObjectName(u"delete_button")
        icon4 = QIcon()
        icon4.addFile(u"assets/icons/delete.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_button.setIcon(icon4)

        self.verticalLayout.addWidget(self.delete_button)


        self.retranslateUi(Manage_User_Form)

        QMetaObject.connectSlotsByName(Manage_User_Form)
    # setupUi

    def retranslateUi(self, Manage_User_Form):
        Manage_User_Form.setWindowTitle(QCoreApplication.translate("Manage_User_Form", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("Manage_User_Form", u"User Information", None))
        self.lname_label.setText(QCoreApplication.translate("Manage_User_Form", u"Last Name", None))
        self.username_label.setText(QCoreApplication.translate("Manage_User_Form", u"Username", None))
        self.fname_label.setText(QCoreApplication.translate("Manage_User_Form", u"First Name", None))
        self.password_label.setText(QCoreApplication.translate("Manage_User_Form", u"Password", None))
        self.add_button.setText(QCoreApplication.translate("Manage_User_Form", u"Add", None))
        self.update_button.setText(QCoreApplication.translate("Manage_User_Form", u"Update", None))
        self.edit_button.setText(QCoreApplication.translate("Manage_User_Form", u"Edit", None))
        self.delete_button.setText(QCoreApplication.translate("Manage_User_Form", u"Delete", None))
    # retranslateUi

