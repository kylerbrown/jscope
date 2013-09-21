from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import jack


class RingBuffer():
    "A 1D ring buffer using numpy arrays"
    def __init__(self, length):
        self.data = np.zeros(length, dtype='f')
        self.index = 0
        self.fifo_indexes = np.arange(length)

    def extend(self, x):
        "adds array x to ring buffer"
        x_index = (self.index + np.arange(x.size)) % self.data.size
        self.data[x_index] = x
        self.index = x_index[-1] + 1


    def get(self):
        "Returns the first-in-first-out data in the ring buffer"
        idx = (self.index + np.arange(self.data.size)) % self.data.size
        return self.data[idx]

      
def ReadFromJack(linput_slice=None, loutput_slice=None):
    if linput_slice == None and loutput_slice == None:
        global input_slice, output_slice
    else:
        input_slice = linput_slice
        output_slice = loutput_slice
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

def reset_view():
    [p.setYRange(-1, 1) for p in plots]
    [p.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)]

# initialize jack connections
nscopes = 1
jack.attach('jscope')
for i in range(nscopes):
    jack.register_port("in_%d" %(i), jack.IsInput)
jack.activate()
N = jack.get_buffer_size()
Sr = float(jack.get_sample_rate())
print(Sr)
plotlength = .3
abscissa = np.flipud(-np.arange(Sr*plotlength) / Sr)
print(len(abscissa))
resample_factor = int(abscissa.size / 1000)

rings = [RingBuffer(len(abscissa)) for i in range(nscopes)]

input_slice = np.zeros((nscopes, N), dtype='f')
output_slice = input_slice.copy()


app = pg.mkQApp()
plots = [pg.PlotWidget() for i in range(nscopes)]
lplt = pg.PlotWidget()
label = QtGui.QLabel()
reset_view_button = QtGui.QPushButton("Reset View")
reset_view_button.clicked.connect(reset_view)
layout = pg.LayoutWidget()
layout.addWidget(label)
layout.addWidget(reset_view_button)
for i, p in enumerate(plots):
    p.showGrid(x=True, y=True)
    p.setYRange(-1, 1)
    p.NoDrag=False

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
    global label, lastUpdate, avgFps
    #ReadFromJack(input_slice, output_slice)
    for i, p in enumerate(plots):
        data = np.squeeze(output_slice[i,:])
        rings[i].extend(data)
        p.plot(abscissa, rings[i].get(), clear=True)
    now = pg.ptime.time()
    fps = 1.0 / (now - lastUpdate)
    lastUpdate = now
    avgFps = avgFps * 0.8 + fps * 0.2
    label.setText("Generating %0.2f fps" % avgFps)


jacktimer =  QtCore.QTimer()
jacktimer.timeout.connect(ReadFromJack)
jacktimer.start(0)
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)

def jack_cleanup():
    jack.deactivate()
    jack.detach()
    print('jscope detached from jack')

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
        jack_cleanup()











