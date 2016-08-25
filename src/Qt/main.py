import importlib
import logging
from functools import partial
from multiprocessing import Queue

import pyqtgraph as pg
import pyqtgraph.exporters
from PyQt4 import QtGui, QtCore

from src.config import Load
from .graphics import MultiAgentPlot
from .ui.gui import Ui_MainWindow


class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        # Load ui files
        self.setupUi(self)

        # Loading data from configs
        self.load = Load()
        self.configs = self.load.yaml("simulations")

        # Simulation with multiprocessing
        self.queue = Queue(maxsize=4)
        self.process = None

        # Graphics
        pg.setConfigOptions(antialias=True)
        self.plot = None
        self.exporter = None
        self.image_queue = None

        self.timer = QtCore.QTimer(self)
        self.dirpath = None

        # Configures
        self.configure_plot()
        self.configure_signals()

    def enable_controls(self, boolean):
        self.startButton.setEnabled(boolean)
        self.stopButton.setEnabled(boolean)
        self.saveButton.setEnabled(boolean)

    def configure_plot(self):
        """Graphics widget for plotting simulation data."""
        logging.info("")
        self.graphicsLayout.setBackground(background=None)
        self.plot = MultiAgentPlot()
        self.graphicsLayout.addItem(self.plot, 0, 0)
        self.exporter = pg.exporters.ImageExporter(self.plot)

    def configure_signals(self):
        """Sets the functionality and values for the widgets."""
        logging.info("")

        # Buttons
        self.timer.timeout.connect(self.update_plots)
        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)

        # Disable until simulation is set
        self.enable_controls(False)

        # Menus
        names = tuple(self.configs["simulations"].keys())
        self.simulationsBox.addItem("")  # No simulation. Clear sidebar.
        self.simulationsBox.addItems(names)
        self.simulationsBox.currentIndexChanged[str].connect(self.set_sidebar)

    def reset_buffers(self):
        logging.info("")
        while not self.queue.empty():
            self.queue.get()

    def clear_sidebar(self):
        # http://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt
        logging.info("")
        layout = self.sidebarLeft
        for i in reversed(range(layout.count())):
            if i in (0, 1):
                continue
            logging.debug("{}".format(layout.itemAt(i)))
            layout.itemAt(i).widget().setParent(None)

    def set_sidebar(self, name):
        logging.info("")
        self.clear_sidebar()

        if name == "":
            return

        kwarg_mapping = self.configs["kwarg_mapping"]
        kwargs = self.configs["simulations"][name]["kwargs"]

        def _update(key, value):
            # FIXME
            logging.debug("Setting \"{}\" to \"{}\"".format(key, value))
            kwargs[key] = value

        for key, val in kwargs.items():
            logging.debug("{}: {}".format(key, val))
            # Set valid values and current value
            label = QtGui.QLabel(key)
            values = kwarg_mapping[key]
            update = partial(_update, key)

            if isinstance(val, int):
                widget = QtGui.QSpinBox()

                if values[0] is not None:
                    widget.setMinimum(values[0])
                else:
                    widget.setMinimum(-100000)

                if values[1] is not None:
                    widget.setMaximum(values[1])
                else:
                    widget.setMaximum(100000)

                widget.setValue(val)
                widget.valueChanged.connect(update)
            elif isinstance(val, float):
                widget = QtGui.QDoubleSpinBox()

                inf = float("inf")
                if values[0] is not None:
                    widget.setMinimum(values[0])
                else:
                    widget.setMinimum(-inf)

                if values[1] is not None:
                    widget.setMaximum(values[1])
                else:
                    widget.setMaximum(inf)

                widget.setValue(val)
                widget.valueChanged.connect(update)
            elif isinstance(val, bool):
                widget = QtGui.QRadioButton()
                widget.setChecked(val)
                widget.toggled.connect(update)
            elif isinstance(val, str):
                widget = QtGui.QComboBox()
                widget.addItems(values)
                index = widget.findText(val)
                widget.setCurrentIndex(index)
                widget.currentIndexChanged[str].connect(update)
            else:
                logging.warning("Value type not supported: {}".format(type(val)))
            self.sidebarLeft.addWidget(label)
            self.sidebarLeft.addWidget(widget)

        initButton = QtGui.QPushButton("Initialize")
        initButton.clicked.connect(self.set_simulation)
        self.sidebarLeft.addWidget(initButton)

        # self.sidebarLeft.addWidget(QtGui.QSpacerItem())

    def set_simulation(self):
        logging.info("")
        self.reset_buffers()
        name = self.simulationsBox.currentText()

        simu_dict = self.configs["simulations"][name]
        module_name = simu_dict["module"]
        class_name = simu_dict["class"]
        kwargs = simu_dict["kwargs"]

        module = importlib.import_module(module_name)
        simulation = getattr(module, class_name)
        self.process = simulation(self.queue, **kwargs)

        # Enable controls
        self.saveButton.clicked.connect(self.process.configure_hdfstore)
        self.enable_controls(True)

        # Plot Simulation
        # TODO: data to request to be put onto queue
        self.plot.configure(self.process)
        args = [("agent", ["position", "active", "position_ls", "position_rs"])]
        self.process.configure_queuing(args)

    def update_plots(self):
        """Updates the data in the plot(s)."""
        logging.debug("")
        data = self.queue.get()
        if data is None:
            self.timer.stop()
            self.enable_controls(False)
        else:
            self.plot.update_data(data)
            # self.exporter.export(toBytes=True)

    def start(self):
        """Start simulation process and updating plot."""
        self.startButton.setEnabled(False)
        if self.process is not None:
            logging.info("")
            self.process.start()
            self.timer.start(0.01 * 1000)  # same as dt used in simulation
        else:
            logging.info("Process is not set")

    def stop(self):
        """Stops simulation process and updating the plot"""
        if self.process is not None:
            logging.info("")
            self.process.stop()
            self.process = None
            try:
                self.saveButton.clicked.disconnect()
            except Exception():
                pass
        else:
            logging.info("Process is not set")
