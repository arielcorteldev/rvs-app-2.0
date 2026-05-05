# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'logindialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Login_Dialog(object):
    def setupUi(self, Login_Dialog):
        if not Login_Dialog.objectName():
            Login_Dialog.setObjectName(u"Login_Dialog")
        Login_Dialog.resize(300, 300)
        icon = QIcon()
        icon.addFile(u"assets/icons/RVS-icon.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Login_Dialog.setWindowIcon(icon)
        self.verticalLayout = QVBoxLayout(Login_Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(Login_Dialog)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QSize(100, 10))
        self.label.setMaximumSize(QSize(300, 150))
        self.label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.label.setPixmap(QPixmap(u"assets/icons/RVS-logo.png"))
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout.addWidget(self.label)

        self.username_input = QLineEdit(Login_Dialog)
        self.username_input.setObjectName(u"username_input")
        self.username_input.setMaximumSize(QSize(16777215, 30))

        self.verticalLayout.addWidget(self.username_input)

        self.password_input = QLineEdit(Login_Dialog)
        self.password_input.setObjectName(u"password_input")
        self.password_input.setMaximumSize(QSize(16777215, 30))

        self.verticalLayout.addWidget(self.password_input)

        self.login_button = QPushButton(Login_Dialog)
        self.login_button.setObjectName(u"login_button")
        self.login_button.setMaximumSize(QSize(16777215, 40))
        font = QFont()
        font.setFamilies([u"Calibri"])
        font.setPointSize(11)
        font.setBold(True)
        self.login_button.setFont(font)
        self.login_button.setAutoDefault(True)

        self.verticalLayout.addWidget(self.login_button)


        self.retranslateUi(Login_Dialog)

        self.login_button.setDefault(False)


        QMetaObject.connectSlotsByName(Login_Dialog)
    # setupUi

    def retranslateUi(self, Login_Dialog):
        Login_Dialog.setWindowTitle(QCoreApplication.translate("Login_Dialog", u"Dialog", None))
        self.label.setText("")
        self.username_input.setPlaceholderText(QCoreApplication.translate("Login_Dialog", u"Enter Username", None))
        self.password_input.setPlaceholderText(QCoreApplication.translate("Login_Dialog", u"Enter Password", None))
        self.login_button.setText(QCoreApplication.translate("Login_Dialog", u"Login", None))
    # retranslateUi

