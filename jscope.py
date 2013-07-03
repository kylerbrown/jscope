import numpy as np
import jack
import sys
# Python Qt4 bindings for GUI objects
from PySide import QtGui
# Matplotlib Figure object
from matplotlib.figure import Figure
# import the Qt4Agg FigureCanvas object, that binds Figure to
# Qt4Agg backend. It also inherits from QWidget
from matplotlib.backends.backend_qt4agg \
import FigureCanvasQTAgg as FigureCanvas
import argparse

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

        # CONSTANTS
        self.N = jack.get_buffer_size()
        self.Sr = float(jack.get_sample_rate())
        self.plotlength = length #  plot length in seconds
        self.abscissa = -np.arange(self.Sr*self.plotlength) / self.Sr
        
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
        self.plot2()

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
    app = QtGui.QApplication(sys.argv)
    # Create our Matplotlib widget
    widget = JScopeWin(args.nscopes, args.subsample, args.length, args.zoom)
    # set the window title
    widget.setWindowTitle("JScope")
    # show the widget
    widget.show()
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())
    jack.deactivate()
    jack.detach()

