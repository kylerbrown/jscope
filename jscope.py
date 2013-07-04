import numpy as np
import jack
import sys
import signal
# Python Qt4 bindings for GUI objects
from PySide import QtGui, QtCore
import matplotlib
matplotlib.use('Qt4Agg')
# Matplotlib Figure object
from matplotlib.figure import Figure
# import the Qt4Agg FigureCanvas object, that binds Figure to
# Qt4Agg backend. It also inherits from QWidget
from matplotlib.backends.backend_qt4agg \
import FigureCanvasQTAgg as FigureCanvas
import argparse

PG = False
if PG == True:
    import pyqtgraph as pg

class RingBuffer():
    def __init__(self, length):
        self.data = np.zeros(length, dtype='f')
        self.index = 0

    def add(self, x):
        x_index = (self.index + np.arange(x.size)) % self.data.size
        self.data[x_index] = x
        self.index = x_index[-1] + 1

    def fifo(self):
        idx = (self.index + np.arange(self.data.size)) % self.data.size
        return self.data[idx]

class JScopePG(QtGui.QMainWindow):
    def __init__(self, nscopes, subsamp_factor, length, zoom):
        super(JScopePG, self).__init__()
        self.scopes = range(nscopes)
        self.subsamp_factor = subsamp_factor
        self.plotlength = length
        self.zoom = zoom
        self.initJACK()
        self.initUI()
        self.timerEvent(None)
        self.timer = self.startTimer(10)

    def initUI(self):
        self.data_layout = pg.GraphicsLayoutWidget()
        #self.area = pgd.DockArea()
        #data_dock = pgd.Dock("Data", size=(500, 200))
        #self.area.addDock(data_dock, 'right')
        #data_dock.addWidget(self.data_layout)
        self.setCentralWidget(self.data_layout)

        self.abscissa = -np.arange(self.Sr*self.plotlength) / self.Sr
        self.input_slice = np.zeros((len(self.scopes), self.N), dtype='f')
        self.output_slice = self.input_slice.copy()
        self.pl = []
        self.curve = []
        self.input_ring = []
        self.output_ring = []
        for i in self.scopes:
            self.pl.append(self.data_layout.addPlot(title=str(i)))
            self.curve.append(self.pl[i].plot(pen='w'))
            self.pl[i].showGrid(x=True, y=True)
            self.pl[i].enableAutoRange('xy', False)
            self.data_layout.nextRow()
            #data_dock.addWidget(self.pl[i])
            self.input_ring.append(RingBuffer(self.abscissa.size))
            self.output_ring.append(RingBuffer(self.abscissa.size))
        self.show()

    def timerEvent(self, evt):
        x = self.ReadFromJack()
        for i in self.scopes:
            self.input_ring[i].add(np.squeeze(x[i,:]))
        self.plot()

    def initJACK(self):
        jack.attach("jscope")
        for i in self.scopes:
            jack.register_port("in_%d" %(i), jack.IsInput)
        jack.activate()
        self.N = jack.get_buffer_size()
        self.Sr = float(jack.get_sample_rate())

    def ReadFromJack(self):
        try:
            jack.process(self.input_slice, self.output_slice)
        except jack.InputSyncError:
            print "Input Sync Error"
            pass
        except jack.OutputSyncError:
            print "Output Sync Error"
            pass
        return self.output_slice

    def plot(self):
        for i in self.scopes:
            x = self.input_ring[i].data
            #self.pl[i].clear()
            #self.pl[i].plot(self.abscissa[::self.subsamp_factor],
            #                x[::self.subsamp_factor])
            self.curve[i].setData(self.abscissa, x)
            #print(x)
        #self.show()

class JScopeWin(FigureCanvas):
    def __init__(self, nscopes, subsamp_factor, length, zoom):
        self.scopes = range(nscopes)
        jack.attach("jscope")
        print(jack.get_ports())
        for i in self.scopes:
            jack.register_port("in_%d" %(i), jack.IsInput)
        jack.activate()
        print jack.get_ports()
        #jack.connect(jack.get_ports()[-2], "jscope:in_1")

        self.N = jack.get_buffer_size()
        self.Sr = float(jack.get_sample_rate())
        self.plotlength = length #  plot length in seconds
        self.abscissa = np.flipud(-np.arange(self.Sr*self.plotlength) / self.Sr)
        
        self.input_slice = np.zeros((nscopes, self.N), dtype='f')
        self.output_slice = self.input_slice.copy()

        self.fig = Figure()
        self.subsamp_factor = subsamp_factor
        self.ax = []
        self.plot_data = []
        self.l_plot_data = []
        self.input_ring = []
        self.output_ring = []
        for i in self.scopes:
            self.ax.append(self.fig.add_subplot(nscopes, 1, i+1))
            self.ax[i].set_ylim(-zoom, zoom)
            self.plot_data.append([])
            foo, = self.ax[i].plot([], self.plot_data[i])
            self.l_plot_data.append(foo)
            self.input_ring.append(RingBuffer(self.abscissa.size))
            self.output_ring.append(RingBuffer(self.abscissa.size))
            self.ax[i].set_xlim(self.abscissa[0], self.abscissa[-1])
            self.ax[i].grid()

        FigureCanvas.__init__(self, self.fig)
        self.fig.canvas.draw()

        self.timerEvent(None)
        self.timer = self.startTimer(0)

    def timerEvent(self, evt):
        x = self.ReadFromJack()
        for i in self.scopes:
            self.input_ring[i].add(np.squeeze(x[i,:]))
        self.plot()

    def ReadFromJack(self):
        #return np.random.randn(self.N)
        try:
            jack.process(self.input_slice, self.output_slice)
        except jack.InputSyncError:
            print "Input Sync Error"
            pass
        except jack.OutputSyncError:
            print "Output Sync Error"
            pass
        #print ".",
        #print(self.input_slice)
        #print(self.output_slice)
        return self.output_slice

    def plot2(self):
        pass
    def plot(self):
        for i in self.scopes:
            x = self.input_ring[i].fifo()
            self.plot_data[i] = x
            self.l_plot_data[i].set_data(self.abscissa[::self.subsamp_factor],
                                      x[::self.subsamp_factor])
        self.fig.canvas.draw()

def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    QtGui.QApplication.quit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple plotting tool using pyjack \
    and matplotlib')
    parser.add_argument('-n', '--numscopes', type=int, dest='nscopes',
                        default=2, help='number of scopes to display')
    parser.add_argument('-s', '--subsample', type=int, dest='subsample',
                        default=10, help='subsampling factor, increasing reduces load, \
                        default is 10')
    parser.add_argument('-l', '--length', type=float, dest='length',
                        default=2, help='Length of scrolling scope in seconds, \
                        default is 2')
    parser.add_argument('-z', '--zoom', type=float, dest='zoom',
                        default=1, help='sets the y axis, ranges from 0 to 1')
    args = parser.parse_args()

    # create the GUI application
    if PG == True:
        signal.signal(signal.SIGINT, sigint_handler)
        app = QtGui.QApplication(sys.argv)
        app.setApplicationName('jscope')
        timer = QtCore.QTimer()
        timer.start(500)  # You may change this if you wish.
        timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.
        mainWin = JScopePG(args.nscopes, args.subsample, args.length, args.zoom)
    else:
        app = QtGui.QApplication(sys.argv)
        # Create our Matplotlib widget
        widget = JScopeWin(args.nscopes, args.subsample, args.length, args.zoom)
        # set the window title
        #widget.setWindowTitle("JScope")
        # show the widget
        widget.show()
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())
    jack.deactivate() #todo add these one quit
    jack.detach()
    print('done') #never prints









