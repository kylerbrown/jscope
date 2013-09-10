from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from pyqtgraph.widgets import RemoteGraphicsView
import numpy as np
import jack

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


def ReadFromJack(input_slice, output_slice):
        try:
            jack.process(input_slice, output_slice)
        except jack.InputSyncError:
            print "Input Sync Error"
            #self.update_time += 20
            #print("setting update time to %d" %(self.update_time))
            pass
        except jack.OutputSyncError:
            print "Output Sync Error"
            pass


# initialize jack connections
nscopes = 2
jack.attach('jscope')
for i in range(nscopes):
    jack.register_port("in_%d" %(i), jack.IsInput)
jack.activate()
N = jack.get_buffer_size()
Sr = float(jack.get_sample_rate())
plotlength = 1
abscissa = np.flipud(-np.arange(Sr*plotlength) / Sr)
resample_factor = int(abscissa.size / 1000)

input_slice = np.zeros((nscopes, N), dtype='f')
output_slice = input_slice.copy()


app = pg.mkQApp()
#view = RemoteGraphicsView.RemoteGraphicsView()
#view.pg.setConfigOptions(antialias=False)
#view.setWindowTitle('pyqtgraph example: RemoteSpeedTest')
plots = [pg.PlotWidget() for i in range(nscopes)]
lplt = pg.PlotWidget()
label = QtGui.QLabel()
layout = pg.LayoutWidget()
layout.addWidget(label)
for i, p in enumerate(plots):
    p.showGrid(x=True, y=True)
    layout.addWidget(p, row=i+1, col=0, colspan=3)
layout.resize(800,800)
layout.show()

## Create a PlotItem in the remote process that will be displayed locally
#rplt = view.pg.PlotItem()
#rplt._setProxyOptions(deferGetattr=True)  ## speeds up access to rplt.plot
#view.setCentralItem(rplt)

lastUpdate = pg.ptime.time()
avgFps = 0.0

def update():
    global label, lastUpdate, avgFps, rpltfunc, input_slice, output_slice, plots
    ReadFromJack(input_slice, output_slice)
#    data = np.random.randn(100) #np.squeeze(output_slice[0,:])
#    rplt.plot(data, clear=True, _callSync='off')  ## We do not expect a return value.
                                                      ## By turning off callSync, we tell
                                                      ## the proxy that it does not need to 
                                                      ## wait for a reply from the remote
                                                      ## process.
    for i, p in enumerate(plots):
        data = np.squeeze(output_slice[i,:])
        p.plot(data, clear=True)
    now = pg.ptime.time()
    fps = 1.0 / (now - lastUpdate)
    lastUpdate = now
    avgFps = avgFps * 0.8 + fps * 0.2
    label.setText("Generating %0.2f fps" % avgFps)
        
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)

def jack_cleanup():
    jack.deactivate()
    jack.detach()
    print('detached from jack!')

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
        jack_cleanup()











