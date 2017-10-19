from functools import partial
import json
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QButtonGroup,
                             QCheckBox,
                             QComboBox,
                             QDialog,
                             QDialogButtonBox,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QPushButton,
                             QRadioButton,
                             QSpinBox,
                             QTabWidget,
                             QVBoxLayout,
                             QWidget)

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo, showWarning

from ._version import __version__
from .about import IR_GITHUB_URL
from .util import (addMenuItem,
                   removeComboBoxItem,
                   setComboBoxItem,
                   setMenuVisibility,
                   updateModificationTime)


class SettingsManager:
    def __init__(self):
        addHook('unloadProfile', self.saveSettings)

        self.defaults = {'badTags': ['iframe', 'script'],
                         'copyTitle': False,
                         'editExtract': False,
                         'editSource': False,
                         'extractBgColor': 'Green',
                         'extractDeck': None,
                         'extractKey': 'x',
                         'extractMethod': 'percent',
                         'extractRandom': True,
                         'extractSchedule': True,
                         'extractTextColor': 'White',
                         'extractValue': 30,
                         'feedLog': {},
                         'generalZoom': 1,
                         'highlightBgColor': 'Yellow',
                         'highlightKey': 'h',
                         'highlightTextColor': 'Black',
                         'importDeck': 'Default',
                         'laterMethod': 'percent',
                         'laterRandom': True,
                         'laterValue': 50,
                         'limitWidth': True,
                         'limitWidthAll': False,
                         'lineScrollFactor': 0.05,
                         'maxWidth': 600,
                         'modelName': 'IR3',
                         'pageScrollFactor': 0.5,
                         'plainText': False,
                         'quickKeys': {},
                         'removeKey': 'z',
                         'scroll': {},
                         'soonMethod': 'percent',
                         'soonRandom': True,
                         'soonValue': 10,
                         'sourceField': 'Source',
                         'textField': 'Text',
                         'titleField': 'Title',
                         'undoKey': 'u',
                         'userAgent': 'IR/{} (+{})'.format(
                             __version__, IR_GITHUB_URL),
                         'zoom': {},
                         'zoomStep': 0.1}

    def loadSettings(self):
        self.settingsChanged = False
        self.mediaDir = os.path.join(mw.pm.profileFolder(), 'collection.media')
        self.jsonPath = os.path.join(self.mediaDir, '_ir.json')

        if os.path.isfile(self.jsonPath):
            with open(self.jsonPath, encoding='utf-8') as jsonFile:
                self.settings = json.load(jsonFile)
            self.addMissingSettings()
            self.removeOutdatedQuickKeys()
        else:
            self.settings = self.defaults

        if self.settingsChanged:
            showInfo('Your Incremental Reading settings file has been modified'
                     ' for compatibility reasons. Please take a moment to'
                     ' reconfigure the add-on to your liking.')

        return self.settings

    def addMissingSettings(self):
        for k, v in self.defaults.items():
            if k not in self.settings:
                self.settings[k] = v
                self.settingsChanged = True

    def removeOutdatedQuickKeys(self):
        required = ['alt',
                    'bgColor',
                    'ctrl',
                    'deckName',
                    'editExtract',
                    'editSource',
                    'fieldName',
                    'modelName',
                    'regularKey',
                    'shift',
                    'textColor']

        for keyCombo, quickKey in self.settings['quickKeys'].copy().items():
            for k in required:
                if k not in quickKey:
                    self.settings['quickKeys'].pop(keyCombo)
                    self.settingsChanged = True
                    break

    def saveSettings(self):
        with open(self.jsonPath, 'w', encoding='utf-8') as jsonFile:
            json.dump(self.settings, jsonFile)

        updateModificationTime(self.mediaDir)

    def loadMenuItems(self):
        menuName = 'Read::Quick Keys'
        if menuName in mw.customMenus:
            mw.customMenus[menuName].clear()

        for keyCombo, quickKey in self.settings['quickKeys'].items():
            menuText = 'Add Card [%s -> %s]' % (quickKey['modelName'],
                                                quickKey['deckName'])
            function = partial(mw.readingManager.quickAdd, quickKey)
            addMenuItem(menuName, menuText, function, keyCombo)

        setMenuVisibility(menuName)

    def showDialog(self):
        dialog = QDialog(mw)

        zoomScrollLayout = QHBoxLayout()
        zoomScrollLayout.addWidget(self.createZoomGroupBox())
        zoomScrollLayout.addWidget(self.createScrollGroupBox())

        zoomScrollTab = QWidget()
        zoomScrollTab.setLayout(zoomScrollLayout)

        tabWidget = QTabWidget()
        tabWidget.setUsesScrollButtons(False)
        tabWidget.addTab(self.createGeneralTab(), 'General')
        tabWidget.addTab(self.createExtractionTab(), 'Extraction')
        tabWidget.addTab(self.createHighlightingTab(), 'Highlighting')
        tabWidget.addTab(self.createSchedulingTab(), 'Scheduling')
        tabWidget.addTab(self.createQuickKeysTab(), 'Quick Keys')
        tabWidget.addTab(zoomScrollTab, 'Zoom / Scroll')

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        buttonBox.accepted.connect(dialog.accept)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(tabWidget)
        mainLayout.addWidget(buttonBox)

        dialog.setLayout(mainLayout)
        dialog.setWindowTitle('Incremental Reading Options')
        dialog.exec_()

        self.settings['zoomStep'] = self.zoomStepSpinBox.value() / 100.0
        self.settings['generalZoom'] = self.generalZoomSpinBox.value() / 100.0
        self.settings['lineScrollFactor'] = self.lineStepSpinBox.value() / 100.0
        self.settings['pageScrollFactor'] = self.pageStepSpinBox.value() / 100.0
        self.settings['editExtract'] = self.editExtractButton.isChecked()
        self.settings['editSource'] = self.editSourceCheckBox.isChecked()
        self.settings['plainText'] = self.plainTextCheckBox.isChecked()
        self.settings['copyTitle'] = self.copyTitleCheckBox.isChecked()
        self.settings['extractSchedule'] = (self
                                            .extractScheduleCheckBox
                                            .isChecked())
        self.settings['soonRandom'] = self.soonRandomCheckBox.isChecked()
        self.settings['laterRandom'] = self.laterRandomCheckBox.isChecked()
        self.settings['extractRandom'] = self.extractRandomCheckBox.isChecked()

        if self.extractDeckComboBox.currentText() == '[Current Deck]':
            self.settings['extractDeck'] = None
        else:
            self.settings['extractDeck'] = (self
                                            .extractDeckComboBox
                                            .currentText())

        try:
            self.settings['soonValue'] = int(
                self.soonValueEditBox.text())
            self.settings['laterValue'] = int(
                self.laterValueEditBox.text())
            self.settings['extractValue'] = int(
                self.extractValueEditBox.text())
            self.settings['maxWidth'] = int(self.widthEditBox.text())
        except ValueError:
            showWarning('Integer value expected. Please try again.')

        if self.soonPercentButton.isChecked():
            self.settings['soonMethod'] = 'percent'
        else:
            self.settings['soonMethod'] = 'count'

        if self.laterPercentButton.isChecked():
            self.settings['laterMethod'] = 'percent'
        else:
            self.settings['laterMethod'] = 'count'

        if self.extractPercentButton.isChecked():
            self.settings['extractMethod'] = 'percent'
        else:
            self.settings['extractMethod'] = 'count'

        if self.limitAllCardsButton.isChecked():
            self.settings['limitWidth'] = True
            self.settings['limitWidthAll'] = True
        elif self.limitIrCardsButton.isChecked():
            self.settings['limitWidth'] = True
            self.settings['limitWidthAll'] = False
        else:
            self.settings['limitWidth'] = False
            self.settings['limitWidthAll'] = False

        mw.readingManager.viewManager.resetZoom(mw.state)

    def createGeneralTab(self):
        extractKeyLabel = QLabel('Extract Key')
        highlightKeyLabel = QLabel('Highlight Key')
        removeKeyLabel = QLabel('Remove Key')

        self.extractKeyComboBox = QComboBox()
        self.highlightKeyComboBox = QComboBox()
        self.removeKeyComboBox = QComboBox()

        keys = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789')
        for comboBox in [self.extractKeyComboBox,
                         self.highlightKeyComboBox,
                         self.removeKeyComboBox]:
            comboBox.addItems(keys)

        self.setDefaultKeys()

        extractKeyLayout = QHBoxLayout()
        extractKeyLayout.addWidget(extractKeyLabel)
        extractKeyLayout.addWidget(self.extractKeyComboBox)

        highlightKeyLayout = QHBoxLayout()
        highlightKeyLayout.addWidget(highlightKeyLabel)
        highlightKeyLayout.addWidget(self.highlightKeyComboBox)

        removeKeyLayout = QHBoxLayout()
        removeKeyLayout.addWidget(removeKeyLabel)
        removeKeyLayout.addWidget(self.removeKeyComboBox)

        saveButton = QPushButton('Save')
        saveButton.clicked.connect(self.saveKeys)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        buttonLayout.addWidget(saveButton)

        controlsLayout = QVBoxLayout()
        controlsLayout.addLayout(extractKeyLayout)
        controlsLayout.addLayout(highlightKeyLayout)
        controlsLayout.addLayout(removeKeyLayout)
        controlsLayout.addLayout(buttonLayout)
        controlsLayout.addStretch()

        controlsGroupBox = QGroupBox('Basic Controls')
        controlsGroupBox.setLayout(controlsLayout)

        widthLabel = QLabel('Card Width Limit:')
        self.widthEditBox = QLineEdit()
        self.widthEditBox.setFixedWidth(50)
        self.widthEditBox.setText(str(self.settings['maxWidth']))
        pixelsLabel = QLabel('pixels')

        widthEditLayout = QHBoxLayout()
        widthEditLayout.addWidget(widthLabel)
        widthEditLayout.addWidget(self.widthEditBox)
        widthEditLayout.addWidget(pixelsLabel)

        applyLabel = QLabel('Apply to')
        self.limitAllCardsButton = QRadioButton('All Cards')
        self.limitIrCardsButton = QRadioButton('IR Cards')
        limitNoneButton = QRadioButton('None')

        if self.settings['limitWidth'] and self.settings['limitWidthAll']:
            self.limitAllCardsButton.setChecked(True)
        elif self.settings['limitWidth']:
            self.limitIrCardsButton.setChecked(True)
        else:
            limitNoneButton.setChecked(True)

        applyLayout = QHBoxLayout()
        applyLayout.addWidget(applyLabel)
        applyLayout.addWidget(self.limitAllCardsButton)
        applyLayout.addWidget(self.limitIrCardsButton)
        applyLayout.addWidget(limitNoneButton)

        displayLayout = QVBoxLayout()
        displayLayout.addLayout(widthEditLayout)
        displayLayout.addLayout(applyLayout)
        displayLayout.addStretch()

        displayGroupBox = QGroupBox('Display')
        displayGroupBox.setLayout(displayLayout)

        layout = QHBoxLayout()
        layout.addWidget(controlsGroupBox)
        layout.addWidget(displayGroupBox)

        tab = QWidget()
        tab.setLayout(layout)

        return tab

    def setDefaultKeys(self):
        setComboBoxItem(self.extractKeyComboBox, self.settings['extractKey'])
        setComboBoxItem(self.highlightKeyComboBox,
                        self.settings['highlightKey'])
        setComboBoxItem(self.removeKeyComboBox, self.settings['removeKey'])

    def saveKeys(self):
        keys = [self.extractKeyComboBox.currentText(),
                self.highlightKeyComboBox.currentText(),
                self.removeKeyComboBox.currentText()]

        if len(set(keys)) < 3:
            showInfo('There is a conflict with the keys you have chosen.'
                     ' Please try again.')
            self.setDefaultKeys()
        else:
            self.settings['extractKey'] = (self
                                           .extractKeyComboBox
                                           .currentText()
                                           .lower())
            self.settings['highlightKey'] = (self
                                             .highlightKeyComboBox
                                             .currentText()
                                             .lower())
            self.settings['removeKey'] = (self
                                          .removeKeyComboBox
                                          .currentText()
                                          .lower())

    def createExtractionTab(self):
        extractDeckLabel = QLabel('Extracts Deck')
        self.extractDeckComboBox = QComboBox()
        deckNames = sorted([d['name'] for d in mw.col.decks.all()])
        self.extractDeckComboBox.addItem('[Current Deck]')
        self.extractDeckComboBox.addItems(deckNames)

        if self.settings['extractDeck']:
            setComboBoxItem(self.extractDeckComboBox,
                            self.settings['extractDeck'])
        else:
            setComboBoxItem(self.extractDeckComboBox, '[Current Deck]')

        extractDeckLayout = QHBoxLayout()
        extractDeckLayout.addWidget(extractDeckLabel)
        extractDeckLayout.addWidget(self.extractDeckComboBox)

        self.editExtractButton = QRadioButton('Edit Extracted Note')
        enterTitleButton = QRadioButton('Enter Title Only')

        if self.settings['editExtract']:
            self.editExtractButton.setChecked(True)
        else:
            enterTitleButton.setChecked(True)

        radioButtonsLayout = QHBoxLayout()
        radioButtonsLayout.addWidget(self.editExtractButton)
        radioButtonsLayout.addWidget(enterTitleButton)
        radioButtonsLayout.addStretch()

        self.editSourceCheckBox = QCheckBox('Edit Source Note')
        self.plainTextCheckBox = QCheckBox('Extract as Plain Text')
        self.copyTitleCheckBox = QCheckBox('Copy Title')
        self.extractScheduleCheckBox = QCheckBox('Schedule Extracts')

        if self.settings['editSource']:
            self.editSourceCheckBox.setChecked(True)

        if self.settings['plainText']:
            self.plainTextCheckBox.setChecked(True)

        if self.settings['copyTitle']:
            self.copyTitleCheckBox.setChecked(True)

        if self.settings['extractSchedule']:
            self.extractScheduleCheckBox.setChecked(True)

        layout = QVBoxLayout()
        layout.addLayout(extractDeckLayout)
        layout.addLayout(radioButtonsLayout)
        layout.addWidget(self.editSourceCheckBox)
        layout.addWidget(self.plainTextCheckBox)
        layout.addWidget(self.copyTitleCheckBox)
        layout.addWidget(self.extractScheduleCheckBox)
        layout.addStretch()

        tab = QWidget()
        tab.setLayout(layout)

        return tab

    def createHighlightingTab(self):
        colorsGroupBox = self.createColorsGroupBox()
        colorPreviewGroupBox = self.createColorPreviewGroupBox()

        horizontalLayout = QHBoxLayout()
        horizontalLayout.addWidget(colorsGroupBox)
        horizontalLayout.addWidget(colorPreviewGroupBox)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Save)
        buttonBox.accepted.connect(self.saveHighlightSettings)

        layout = QVBoxLayout()
        layout.addWidget(self.targetComboBox)
        layout.addLayout(horizontalLayout)
        layout.addWidget(buttonBox)
        layout.addStretch()

        tab = QWidget()
        tab.setLayout(layout)

        return tab

    def saveHighlightSettings(self):
        target = self.targetComboBox.currentText()
        bgColor = self.bgColorComboBox.currentText()
        textColor = self.textColorComboBox.currentText()

        if target == self.settings['highlightKey']:
            self.settings['highlightBgColor'] = bgColor
            self.settings['highlightTextColor'] = textColor
        elif target == self.settings['extractKey']:
            self.settings['extractBgColor'] = bgColor
            self.settings['extractTextColor'] = textColor
        else:
            self.settings['quickKeys'][target]['bgColor'] = bgColor
            self.settings['quickKeys'][target]['textColor'] = textColor

    def createColorsGroupBox(self):
        self.targetComboBox = QComboBox()
        self.targetComboBox.addItem(self.settings['highlightKey'])
        self.targetComboBox.addItem(self.settings['extractKey'])
        self.targetComboBox.addItems(self.settings['quickKeys'].keys())
        self.targetComboBox.currentIndexChanged.connect(
            self.updateHighlightingTab)

        targetLayout = QHBoxLayout()
        targetLayout.addWidget(self.targetComboBox)
        targetLayout.addStretch()

        colors = self.getColorList()

        self.bgColorComboBox = QComboBox()
        self.bgColorComboBox.addItems(colors)
        setComboBoxItem(self.bgColorComboBox,
                        self.settings['highlightBgColor'])
        self.bgColorComboBox.currentIndexChanged.connect(
            self.updateColorPreview)

        self.textColorComboBox = QComboBox()
        self.textColorComboBox.addItems(colors)
        setComboBoxItem(self.textColorComboBox,
                        self.settings['highlightTextColor'])
        self.textColorComboBox.currentIndexChanged.connect(
            self.updateColorPreview)

        bgColorLabel = QLabel('Background')
        bgColorLayout = QHBoxLayout()
        bgColorLayout.addWidget(bgColorLabel)
        bgColorLayout.addSpacing(10)
        bgColorLayout.addWidget(self.bgColorComboBox)

        textColorLabel = QLabel('Text')
        textColorLayout = QHBoxLayout()
        textColorLayout.addWidget(textColorLabel)
        textColorLayout.addSpacing(10)
        textColorLayout.addWidget(self.textColorComboBox)

        layout = QVBoxLayout()
        layout.addLayout(bgColorLayout)
        layout.addLayout(textColorLayout)
        layout.addStretch()

        groupBox = QGroupBox('Colors')
        groupBox.setLayout(layout)

        return groupBox

    def updateHighlightingTab(self):
        target = self.targetComboBox.currentText()
        if target == self.settings['highlightKey']:
            setComboBoxItem(self.bgColorComboBox,
                            self.settings['highlightBgColor'])
            setComboBoxItem(self.textColorComboBox,
                            self.settings['highlightTextColor'])
        elif target == self.settings['extractKey']:
            setComboBoxItem(self.bgColorComboBox,
                            self.settings['extractBgColor'])
            setComboBoxItem(self.textColorComboBox,
                            self.settings['extractTextColor'])
        else:
            setComboBoxItem(self.bgColorComboBox,
                            self.settings['quickKeys'][target]['bgColor'])
            setComboBoxItem(self.textColorComboBox,
                            self.settings['quickKeys'][target]['textColor'])

    def getColorList(self):
        moduleDir, _ = os.path.split(__file__)
        colorsFilePath = os.path.join(moduleDir, 'data', 'colors.u8')
        with open(colorsFilePath, encoding='utf-8') as colorsFile:
            return [line.strip() for line in colorsFile]

    def updateColorPreview(self):
        bgColor = self.bgColorComboBox.currentText()
        textColor = self.textColorComboBox.currentText()
        styleSheet = ('QLabel {'
                      'background-color: %s;'
                      'color: %s;'
                      'padding: 10px;'
                      'font-size: 16px;'
                      'font-family: tahoma, geneva, sans-serif;'
                      '}') % (bgColor, textColor)
        self.colorPreviewLabel.setStyleSheet(styleSheet)
        self.colorPreviewLabel.setAlignment(Qt.AlignCenter)

    def createColorPreviewGroupBox(self):
        self.colorPreviewLabel = QLabel('Example Text')
        self.updateColorPreview()
        colorPreviewLayout = QVBoxLayout()
        colorPreviewLayout.addWidget(self.colorPreviewLabel)

        groupBox = QGroupBox('Preview')
        groupBox.setLayout(colorPreviewLayout)

        return groupBox

    def createSchedulingTab(self):
        soonLabel = QLabel('Soon Button')
        laterLabel = QLabel('Later Button')
        extractLabel = QLabel('Extracts')

        self.soonPercentButton = QRadioButton('Percent')
        soonPositionButton = QRadioButton('Position')
        self.laterPercentButton = QRadioButton('Percent')
        laterPositionButton = QRadioButton('Position')
        self.extractPercentButton = QRadioButton('Percent')
        extractPositionButton = QRadioButton('Position')

        self.soonRandomCheckBox = QCheckBox('Randomize')
        self.laterRandomCheckBox = QCheckBox('Randomize')
        self.extractRandomCheckBox = QCheckBox('Randomize')

        self.soonValueEditBox = QLineEdit()
        self.soonValueEditBox.setFixedWidth(100)
        self.laterValueEditBox = QLineEdit()
        self.laterValueEditBox.setFixedWidth(100)
        self.extractValueEditBox = QLineEdit()
        self.extractValueEditBox.setFixedWidth(100)

        if self.settings['soonMethod'] == 'percent':
            self.soonPercentButton.setChecked(True)
        else:
            soonPositionButton.setChecked(True)

        if self.settings['laterMethod'] == 'percent':
            self.laterPercentButton.setChecked(True)
        else:
            laterPositionButton.setChecked(True)

        if self.settings['extractMethod'] == 'percent':
            self.extractPercentButton.setChecked(True)
        else:
            extractPositionButton.setChecked(True)

        if self.settings['soonRandom']:
            self.soonRandomCheckBox.setChecked(True)

        if self.settings['laterRandom']:
            self.laterRandomCheckBox.setChecked(True)

        if self.settings['extractRandom']:
            self.extractRandomCheckBox.setChecked(True)

        self.soonValueEditBox.setText(str(self.settings['soonValue']))
        self.laterValueEditBox.setText(str(self.settings['laterValue']))
        self.extractValueEditBox.setText(str(self.settings['extractValue']))

        soonLayout = QHBoxLayout()
        soonLayout.addWidget(soonLabel)
        soonLayout.addStretch()
        soonLayout.addWidget(self.soonValueEditBox)
        soonLayout.addWidget(self.soonPercentButton)
        soonLayout.addWidget(soonPositionButton)
        soonLayout.addWidget(self.soonRandomCheckBox)

        laterLayout = QHBoxLayout()
        laterLayout.addWidget(laterLabel)
        laterLayout.addStretch()
        laterLayout.addWidget(self.laterValueEditBox)
        laterLayout.addWidget(self.laterPercentButton)
        laterLayout.addWidget(laterPositionButton)
        laterLayout.addWidget(self.laterRandomCheckBox)

        extractLayout = QHBoxLayout()
        extractLayout.addWidget(extractLabel)
        extractLayout.addStretch()
        extractLayout.addWidget(self.extractValueEditBox)
        extractLayout.addWidget(self.extractPercentButton)
        extractLayout.addWidget(extractPositionButton)
        extractLayout.addWidget(self.extractRandomCheckBox)

        soonButtonGroup = QButtonGroup(soonLayout)
        soonButtonGroup.addButton(self.soonPercentButton)
        soonButtonGroup.addButton(soonPositionButton)

        laterButtonGroup = QButtonGroup(laterLayout)
        laterButtonGroup.addButton(self.laterPercentButton)
        laterButtonGroup.addButton(laterPositionButton)

        extractButtonGroup = QButtonGroup(extractLayout)
        extractButtonGroup.addButton(self.extractPercentButton)
        extractButtonGroup.addButton(extractPositionButton)

        layout = QVBoxLayout()
        layout.addLayout(soonLayout)
        layout.addLayout(laterLayout)
        layout.addLayout(extractLayout)
        layout.addStretch()

        tab = QWidget()
        tab.setLayout(layout)

        return tab

    def createQuickKeysTab(self):
        destDeckLabel = QLabel('Destination Deck')
        noteTypeLabel = QLabel('Note Type')
        textFieldLabel = QLabel('Paste Text to Field')
        keyComboLabel = QLabel('Key Combination')

        self.quickKeysComboBox = QComboBox()
        self.quickKeysComboBox.addItem('')
        self.quickKeysComboBox.addItems(self.settings['quickKeys'].keys())
        self.quickKeysComboBox.currentIndexChanged.connect(
            self.updateQuickKeysTab)

        self.destDeckComboBox = QComboBox()
        self.noteTypeComboBox = QComboBox()
        self.textFieldComboBox = QComboBox()
        self.quickKeyEditExtractCheckBox = QCheckBox('Edit Extracted Note')
        self.quickKeyEditSourceCheckBox = QCheckBox('Edit Source Note')
        self.quickKeyPlainTextCheckBox = QCheckBox('Extract as Plain Text')

        self.ctrlKeyCheckBox = QCheckBox('Ctrl')
        self.shiftKeyCheckBox = QCheckBox('Shift')
        self.altKeyCheckBox = QCheckBox('Alt')
        self.regularKeyComboBox = QComboBox()
        self.regularKeyComboBox.addItem('')
        self.regularKeyComboBox.addItems(
            list('ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'))

        destDeckLayout = QHBoxLayout()
        destDeckLayout.addWidget(destDeckLabel)
        destDeckLayout.addWidget(self.destDeckComboBox)

        noteTypeLayout = QHBoxLayout()
        noteTypeLayout.addWidget(noteTypeLabel)
        noteTypeLayout.addWidget(self.noteTypeComboBox)

        textFieldLayout = QHBoxLayout()
        textFieldLayout.addWidget(textFieldLabel)
        textFieldLayout.addWidget(self.textFieldComboBox)

        keyComboLayout = QHBoxLayout()
        keyComboLayout.addWidget(keyComboLabel)
        keyComboLayout.addStretch()
        keyComboLayout.addWidget(self.ctrlKeyCheckBox)
        keyComboLayout.addWidget(self.shiftKeyCheckBox)
        keyComboLayout.addWidget(self.altKeyCheckBox)
        keyComboLayout.addWidget(self.regularKeyComboBox)

        deckNames = sorted([d['name'] for d in mw.col.decks.all()])
        self.destDeckComboBox.addItem('')
        self.destDeckComboBox.addItems(deckNames)

        modelNames = sorted([m['name'] for m in mw.col.models.all()])
        self.noteTypeComboBox.addItem('')
        self.noteTypeComboBox.addItems(modelNames)
        self.noteTypeComboBox.currentIndexChanged.connect(self.updateFieldList)

        newButton = QPushButton('New')
        newButton.clicked.connect(self.clearQuickKeysTab)
        deleteButton = QPushButton('Delete')
        deleteButton.clicked.connect(self.deleteQuickKey)
        saveButton = QPushButton('Save')
        saveButton.clicked.connect(self.setQuickKey)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        buttonLayout.addWidget(newButton)
        buttonLayout.addWidget(deleteButton)
        buttonLayout.addWidget(saveButton)

        layout = QVBoxLayout()
        layout.addWidget(self.quickKeysComboBox)
        layout.addLayout(destDeckLayout)
        layout.addLayout(noteTypeLayout)
        layout.addLayout(textFieldLayout)
        layout.addLayout(keyComboLayout)
        layout.addWidget(self.quickKeyEditExtractCheckBox)
        layout.addWidget(self.quickKeyEditSourceCheckBox)
        layout.addWidget(self.quickKeyPlainTextCheckBox)
        layout.addLayout(buttonLayout)

        tab = QWidget()
        tab.setLayout(layout)

        return tab

    def updateQuickKeysTab(self):
        quickKey = self.quickKeysComboBox.currentText()
        if quickKey:
            model = self.settings['quickKeys'][quickKey]
            setComboBoxItem(self.destDeckComboBox, model['deckName'])
            setComboBoxItem(self.noteTypeComboBox, model['modelName'])
            setComboBoxItem(self.textFieldComboBox, model['fieldName'])
            self.ctrlKeyCheckBox.setChecked(model['ctrl'])
            self.shiftKeyCheckBox.setChecked(model['shift'])
            self.altKeyCheckBox.setChecked(model['alt'])
            setComboBoxItem(self.regularKeyComboBox, model['regularKey'])
            self.quickKeyEditExtractCheckBox.setChecked(model['editExtract'])
            self.quickKeyEditSourceCheckBox.setChecked(model['editSource'])
            self.quickKeyPlainTextCheckBox.setChecked(model['plainText'])
        else:
            self.clearQuickKeysTab()

    def updateFieldList(self):
        modelName = self.noteTypeComboBox.currentText()
        self.textFieldComboBox.clear()
        if modelName:
            model = mw.col.models.byName(modelName)
            fieldNames = [f['name'] for f in model['flds']]
            self.textFieldComboBox.addItems(fieldNames)

    def clearQuickKeysTab(self):
        self.quickKeysComboBox.setCurrentIndex(0)
        self.destDeckComboBox.setCurrentIndex(0)
        self.noteTypeComboBox.setCurrentIndex(0)
        self.textFieldComboBox.setCurrentIndex(0)
        self.ctrlKeyCheckBox.setChecked(False)
        self.shiftKeyCheckBox.setChecked(False)
        self.altKeyCheckBox.setChecked(False)
        self.regularKeyComboBox.setCurrentIndex(0)
        self.quickKeyEditExtractCheckBox.setChecked(False)
        self.quickKeyEditSourceCheckBox.setChecked(False)
        self.quickKeyPlainTextCheckBox.setChecked(False)

    def deleteQuickKey(self):
        quickKey = self.quickKeysComboBox.currentText()
        if quickKey:
            self.settings['quickKeys'].pop(quickKey)
            removeComboBoxItem(self.quickKeysComboBox, quickKey)
            self.clearQuickKeysTab()
            self.loadMenuItems()

    def setQuickKey(self):
        quickKey = {'deckName': self.destDeckComboBox.currentText(),
                    'modelName': self.noteTypeComboBox.currentText(),
                    'fieldName': self.textFieldComboBox.currentText(),
                    'ctrl': self.ctrlKeyCheckBox.isChecked(),
                    'shift': self.shiftKeyCheckBox.isChecked(),
                    'alt': self.altKeyCheckBox.isChecked(),
                    'regularKey': self.regularKeyComboBox.currentText(),
                    'bgColor': self.bgColorComboBox.currentText(),
                    'textColor': self.textColorComboBox.currentText(),
                    'editExtract': self.quickKeyEditExtractCheckBox.isChecked(),
                    'editSource': self.quickKeyEditSourceCheckBox.isChecked(),
                    'plainText': self.quickKeyPlainTextCheckBox.isChecked()}

        for k in ['deckName', 'modelName', 'regularKey']:
            if not quickKey[k]:
                showInfo('Please complete all settings. Destination deck,'
                         ' note type, and a letter or number for the key'
                         ' combination are required.')
                return

        keyCombo = ''
        if quickKey['ctrl']:
            keyCombo += 'Ctrl+'
        if quickKey['shift']:
            keyCombo += 'Shift+'
        if quickKey['alt']:
            keyCombo += 'Alt+'
        keyCombo += quickKey['regularKey']

        self.settings['quickKeys'][keyCombo] = quickKey
        self.loadMenuItems()

        showInfo('New shortcut added: %s' % keyCombo)

    def createZoomGroupBox(self):
        zoomStepLabel = QLabel('Zoom Step')
        zoomStepPercentLabel = QLabel('%')
        generalZoomLabel = QLabel('General Zoom')
        generalZoomPercentLabel = QLabel('%')

        self.zoomStepSpinBox = QSpinBox()
        self.zoomStepSpinBox.setMinimum(5)
        self.zoomStepSpinBox.setMaximum(100)
        self.zoomStepSpinBox.setSingleStep(5)
        zoomStepPercent = round(self.settings['zoomStep'] * 100)
        self.zoomStepSpinBox.setValue(zoomStepPercent)

        self.generalZoomSpinBox = QSpinBox()
        self.generalZoomSpinBox.setMinimum(10)
        self.generalZoomSpinBox.setMaximum(200)
        self.generalZoomSpinBox.setSingleStep(10)
        generalZoomPercent = round(self.settings['generalZoom'] * 100)
        self.generalZoomSpinBox.setValue(generalZoomPercent)

        zoomStepLayout = QHBoxLayout()
        zoomStepLayout.addWidget(zoomStepLabel)
        zoomStepLayout.addStretch()
        zoomStepLayout.addWidget(self.zoomStepSpinBox)
        zoomStepLayout.addWidget(zoomStepPercentLabel)

        generalZoomLayout = QHBoxLayout()
        generalZoomLayout.addWidget(generalZoomLabel)
        generalZoomLayout.addStretch()
        generalZoomLayout.addWidget(self.generalZoomSpinBox)
        generalZoomLayout.addWidget(generalZoomPercentLabel)

        layout = QVBoxLayout()
        layout.addLayout(zoomStepLayout)
        layout.addLayout(generalZoomLayout)
        layout.addStretch()

        groupBox = QGroupBox('Zoom')
        groupBox.setLayout(layout)

        return groupBox

    def createScrollGroupBox(self):
        lineStepLabel = QLabel('Line Step')
        lineStepPercentLabel = QLabel('%')
        pageStepLabel = QLabel('Page Step')
        pageStepPercentLabel = QLabel('%')

        self.lineStepSpinBox = QSpinBox()
        self.lineStepSpinBox.setMinimum(5)
        self.lineStepSpinBox.setMaximum(100)
        self.lineStepSpinBox.setSingleStep(5)
        self.lineStepSpinBox.setValue(
            round(self.settings['lineScrollFactor'] * 100))

        self.pageStepSpinBox = QSpinBox()
        self.pageStepSpinBox.setMinimum(5)
        self.pageStepSpinBox.setMaximum(100)
        self.pageStepSpinBox.setSingleStep(5)
        self.pageStepSpinBox.setValue(
            round(self.settings['pageScrollFactor'] * 100))

        lineStepLayout = QHBoxLayout()
        lineStepLayout.addWidget(lineStepLabel)
        lineStepLayout.addStretch()
        lineStepLayout.addWidget(self.lineStepSpinBox)
        lineStepLayout.addWidget(lineStepPercentLabel)

        pageStepLayout = QHBoxLayout()
        pageStepLayout.addWidget(pageStepLabel)
        pageStepLayout.addStretch()
        pageStepLayout.addWidget(self.pageStepSpinBox)
        pageStepLayout.addWidget(pageStepPercentLabel)

        layout = QVBoxLayout()
        layout.addLayout(lineStepLayout)
        layout.addLayout(pageStepLayout)
        layout.addStretch()

        groupBox = QGroupBox('Scroll')
        groupBox.setLayout(layout)

        return groupBox
