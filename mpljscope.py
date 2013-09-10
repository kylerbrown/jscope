import numpy as np
import jack
import sys
from PySide import QtGui, QtCore
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas
import argparse

from multiprocessing import Process, Queue

debug = False

class RingBuffer():
    "A 1D ring buffer using numpy arrays"
    def __init__(self, length):
        self.data = np.zeros(length, dtype='f')
        self.index = 0

    def add(self, x):
        "adds array x to ring buffer"
        x_index = (self.index + np.arange(x.size)) % self.data.size
        self.data[x_index] = x
        self.index = x_index[-1] + 1

    def fifo(self):
        "Returns the first-in-first-out data in the ring buffer"
        idx = (self.index + np.arange(self.data.size)) % self.data.size
        return self.data[idx]

class JScopeWin(FigureCanvas):
    """Widget containing the scolling scope"""
    def __init__(self, nscopes, subsamp_factor, length, zoom):
        self.fig = Figure()
        FigureCanvas.__init__(self, self.fig)

        # setup JACK connections
        self.scopes = range(nscopes)
        jack.attach("jscope")
        for i in self.scopes:
            jack.register_port("in_%d" %(i), jack.IsInput)
        jack.activate()
        self.ACTIVATED = True
        if debug: print("jack ports: " + str(jack.get_ports()))
        #jack.connect(jack.get_ports()[-2], "jscope:in_1")

        self.N = jack.get_buffer_size()
        self.Sr = float(jack.get_sample_rate())
        self.plotlength = length #  plot length in seconds
        self.abscissa = np.flipud(-np.arange(self.Sr*self.plotlength) / self.Sr)
        self.resample_factor = int(self.abscissa.size / 1000)
        

        self.input_slice = np.zeros((nscopes, self.N), dtype='f')
        self.output_slice = self.input_slice.copy()

        # setup plots
        self.subsamp_factor = subsamp_factor
        self.ax = []
        self.plot_data = []
        self.l_plot_data = []
        self.input_ring = []
        self.output_ring = []
        for i in self.scopes:
            self.ax.append(self.fig.add_subplot(nscopes, 1, i+1))
            self.ax[i].set_ylim(-zoom, zoom)
            self.plot_data.append(self.abscissa[::self.subsamp_factor])
            foo, = self.ax[i].plot(self.abscissa[::self.subsamp_factor], self.plot_data[i], 'm')
            self.l_plot_data.append(foo)
            self.input_ring.append(RingBuffer(self.abscissa.size))
            self.output_ring.append(RingBuffer(self.abscissa.size))
            self.ax[i].set_xlim(self.abscissa[0], self.abscissa[-1])
            self.ax[i].grid()

        # initialize two timers, one for reading jack data
        # and a second for plotting
        
        #self.timerEvent(None)
        #self.timer = self.startTimer(1) #  Jack event timer
        self.plot_timer = QtCore.QTimer()
        self.plot_timer.timeout.connect(self.plot_from_pipe)
        self.update_time = 1
        self.plot_timer.start(self.update_time) #  plotting event timer

        self.queue = Queue(1)
        self.p = Process(target=self.jack_process_loop, args=(self.queue,))
        self.p.start()
        self.data_to_plot=[]
        

    def jack_process_loop(self, q):
        while self.ACTIVATED:
            x = self.ReadFromJack()
            for i in self.scopes:
                self.input_ring[i].add(np.squeeze(x[i,:]))
            data_to_plot = [self.input_ring[i].fifo() for i in self.scopes]
            try:
                q.put_nowait(data_to_plot)
            except Exception:
                pass
            

    def plot_from_pipe(self):
        try:
            dat = self.queue.get_nowait()
            for i, x in enumerate(dat):
                self.l_plot_data[i].set_ydata(x[::self.subsamp_factor])
            self.fig.canvas.draw()
        except Exception:
            pass


    def plot_timerEvent(self):
            self.plot()

    def timerEvent(self, evt):
        if self.ACTIVATED:
            x = self.ReadFromJack()
            for i in self.scopes:
                self.input_ring[i].add(np.squeeze(x[i,:]))

    def ReadFromJack(self):
        try:
            jack.process(self.input_slice, self.output_slice)
        except jack.InputSyncError:
            print "Input Sync Error"
            #self.update_time += 20
            #print("setting update time to %d" %(self.update_time))
            pass
        except jack.OutputSyncError:
            print "Output Sync Error"
            pass
        if debug: print("JACK input slice:" + str(self.input_slice))
        if debug: print("JACK output slice:" + str(self.output_slice))
        return self.output_slice

    def plot(self):
        for i in self.scopes:
            x = self.input_ring[i].fifo()
            self.plot_data[i] = x
            self.l_plot_data[i].set_data(x[::self.subsamp_factor])
        self.fig.canvas.draw()

    def closeEvent(self, evt):
        if debug: print('closing')
        jack.deactivate()
        self.ACTIVATED = False
        jack.detach()
        self.p.terminate()
        evt.accept()


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
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    args = parser.parse_args()

    debug = args.verbose
    # create the GUI application
    
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
    
    print('done') #never prints









