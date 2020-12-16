import sys
import os
import numpy as np
import time
from datetime import datetime
from PyQt5 import QtGui, QtCore, QtWidgets, uic, Qt
from PyQt5.QtGui import QPainter, QBrush, QPen

from datetime import datetime
import pyqtgraph_copy.pyqtgraph as pg
import colorsys

from pyecog_plot_item import PyecogPlotCurveItem, PyecogLinearRegionItem, PyecogCursorItem

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


# from .lines import InfiniteOrthogonalLine

# lets get linear region working?y

class PairedGraphicsView():
    '''
    This is pyqgraph implementation of plotting windows.
    This should be focused on working, not particularly elegant.
    '''

    def build_splitter(self):
        # Todo might need to paqss a size in here
        self.splitter = QtWidgets.QSplitter(parent=None)
        # self.splitter.resize(680, 400)  # Todo currently not sure about this
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                           QtWidgets.QSizePolicy.Expanding)
        self.splitter.setSizePolicy(sizePolicy)

    def __init__(self, parent=None):
        # todo clean this method up!
        self.parent = parent
        self.build_splitter()
        self.scale = None  # transform on the childitems of plot

        overview_layout_widget = pg.GraphicsLayoutWidget()
        overview_date_axis = DateAxis(orientation='bottom')
        self.overview_plot = overview_layout_widget.addPlot(axisItems={'bottom':overview_date_axis})
        # self.overview_plot.showAxis('left', show=False)
        # self.overview_plot.setLabel('bottom', text='Time', units='s')

        # this doesnt work (getting the scroll)
        overview_layout_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        insetview_layout_widget = pg.GraphicsLayoutWidget()
        insetview_date_axis = DateAxis(orientation='bottom')
        self.insetview_plot = insetview_layout_widget.addPlot(axisItems={'bottom':insetview_date_axis})
        # self.insetview_plot.showAxis('left', show=False)
        self.insetview_plot.showGrid(x=True, y=True, alpha=0.15)
        self.insetview_plot.setLabel('bottom', text='Time', units='s')

        self.insetview_plot.vb.state['autoRange'] = [False, False]
        self.overview_plot.vb.state['autoRange'] = [False, False]

        self.splitter.addWidget(overview_layout_widget)
        self.splitter.addWidget(insetview_layout_widget)
        # self.splitter.setStretchFactor(1, 6)  # make inset view 6 times larger

        self.insetview_plot.sigRangeChanged.connect(self.insetview_range_changed)
        self.overview_plot.sigRangeChanged.connect(self.overview_range_changed)
        self.insetview_plot.vb.scene().sigMouseClicked.connect(self.inset_clicked) # Get original mouseclick signal with modifiers
        self.overview_plot.vb.scene().sigMouseClicked.connect(self.overview_clicked)
        # hacky use of self.vb, but just rolling with it
        self.is_setting_window_position = False

        x_range, y_range = self.insetview_plot.viewRange()
        pen = pg.mkPen(color=(250, 250, 80), width=2)
        penh = pg.mkPen(color=(100, 100, 250), width=2)

        self.overviewROI = pg.RectROI(pos=(x_range[0], y_range[0]),
                                      size=(x_range[1] - x_range[0], y_range[1] - y_range[0]),
                                      sideScalers=True, pen=penh, rotatable=False, removable=False)
        self.overviewROI.sigRegionChanged.connect(self.overviewROIchanged)
        self.overview_plot.addItem(self.overviewROI)
        self.inset_annotations = []
        self.overview_annotations = []
        # here we will store the plot items in nested dict form
        # {"1" : {'inset': obj,'overview':obj }
        # will be used for an ugly hack to snchonize across plots
        self.channel_plotitem_dict = {}
        self.main_model = parent.main_model
        self.main_model.annotations.sigAnnotationAdded.connect(self.add_annotaion_plot)
        self.main_model.annotations.sigLabelsChanged.connect(
            lambda: self.set_scenes_plot_annotations_data(self.main_model.annotations))

    def set_scenes_plot_channel_data(self, overview_range = [0,3600], pens=None):
        '''
        # Not entirely clear the differences between this and
        set_plotitem_data is snesnible
        pens - a list of len channels containing pens
        '''
        # we need to handle if channel not seen before
        # 6 std devations
        print('Items to delete')
        print(self.overview_plot.items)
        self.overview_plot.clear()
        print('Items after delete')
        print(self.overview_plot.items)
        self.insetview_plot.clear()
        print(overview_range)
        self.overview_plot.setXRange(*overview_range)
        self.insetview_plot.vb.setXRange(overview_range[0],
                                         overview_range[0] + min(30, overview_range[1] - overview_range[0]))
        # if self.scale is None:  # running for the first time
        if True:  # running for the first time
            print('Getting data to compute plot scale factors')
            arr,tarr = self.main_model.project.get_data_from_range(self.overview_plot.vb.viewRange()[0])
            print(arr.shape, tarr.shape)
            self.n_channels = arr.shape[1]
            self.scale = 1 / (6 * np.mean(np.std(arr, axis=0, keepdims=True), axis=1))
            self.overview_plot.vb.setYRange(-2, arr.shape[1] + 1)
            self.insetview_plot.vb.setYRange(-2, arr.shape[1] + 1)

        for i in range(self.n_channels):
            if pens is None:
                pen = pg.mkPen('k')
            else:
                pen = pen[i]
            print('Setting plotitem channel data')
            self.set_plotitem_channel_data(pen, i, self.scale)

        print('settng up extra plot parameters...')
        # prevent scrolling past 0 and end of data
        # self.insetview_plot.vb.setLimits(xMin=0, xMax=arr.shape[0] / fs)
        self.overview_plot.vb.setLimits(maxXRange=3600)
        self.insetview_plot.vb.setLimits(maxXRange=3600)
        self.overview_plot.vb.setLimits(yMin=-3, yMax=self.n_channels + 3)

        self.overview_plot.addItem(self.overviewROI) # put back the overview box

        self.inset_annotations = []
        self.overview_annotations = []
        self.set_scenes_plot_annotations_data(self.main_model.annotations)
        self.main_model.annotations.sigFocusOnAnnotation.connect(self.set_focus_on_annotation)
        self.set_scene_window(self.main_model.window)
        self.set_scene_cursor()

    def set_plotitem_channel_data(self, pen, index, init_scale):
        '''
        If the index exists within the plotitem dict we just set the data, else create
        or delete from the dict. (#todo)

        init_scale is the initial scaling of the channels. Set transform
        '''
        # todo stop passing the vb to construction have it added automatically when add the item to plot
        if True: # index not in self.channel_plotitem_dict.keys(): # This was used before we were clearing the scenes upon file loading
            self.channel_plotitem_dict[index] = {}
            self.channel_plotitem_dict[index]['overview'] = PyecogPlotCurveItem(self.main_model.project, index,
                                                                                viewbox=self.overview_plot.vb)
            self.channel_plotitem_dict[index]['insetview'] = PyecogPlotCurveItem(self.main_model.project, index,
                                                                                 viewbox=self.insetview_plot.vb)
            self.channel_plotitem_dict[index]['overview'].setY(index)
            self.channel_plotitem_dict[index]['insetview'].setY(index)
            m = QtGui.QTransform().scale(1, init_scale)
            self.channel_plotitem_dict[index]['overview'].setTransform(m)
            self.channel_plotitem_dict[index]['insetview'].setTransform(m)
            self.overview_plot.addItem(self.channel_plotitem_dict[index]['overview'])
            self.insetview_plot.addItem(self.channel_plotitem_dict[index]['insetview'])

        # self.channel_plotitem_dict[index]['overview'].set_data(y, fs)
        # self.channel_plotitem_dict[index]['insetview'].set_data(y, fs)
        # self.overview_plot.vb.setXRange(t0, t0 + y.shape[0]/fs, padding=0)
        # self.insetview_plot.vb.setXRange(t0, t0 + min(30, y.shape[0] / fs))

    # The following static methods are auxiliary functions to link several annotation related signals:
    @staticmethod
    def function_generator_link_annotaions_to_graphs(annotation_object, annotation_graph):
        return lambda: annotation_graph.setRegion(annotation_object.getPos())

    @staticmethod
    def function_generator_link_graphs_to_annotations(annotation_object, annotation_graph):
        return lambda: annotation_object.setPos(annotation_graph.getRegion())

    @staticmethod
    def function_generator_link_graphs(annotation_graph_a, annotation_graph_b):
        return lambda: annotation_graph_b.setRegion(annotation_graph_a.getRegion())

    @staticmethod
    def function_generator_link_click(annotationpage, annotation_object):
        return lambda: annotationpage.focusOnAnnotation(annotation_object)

    def add_annotaion_plot(self, annotation):
        color = self.main_model.annotations.label_color_dict[annotation.getLabel()]  # circle hue with constant luminosity an saturation
        brush = pg.functions.mkBrush(color=(*color, 25))
        pen = pg.functions.mkPen(color=(*color, 200))
        annotation_graph_o = PyecogLinearRegionItem((annotation.getStart(), annotation.getEnd()), pen=pen,
                                                    brush=brush, movable=False, id=None)
        annotation_graph_o.setZValue(-1)
        annotation_graph_i = PyecogLinearRegionItem((annotation.getStart(), annotation.getEnd()), pen=pen,
                                                    brush=brush, swapMode='push', label=annotation.getLabel(), id=None)

        annotation_graph_i.sigRegionChangeFinished.connect(
            self.function_generator_link_graphs_to_annotations(annotation, annotation_graph_i))
        annotation_graph_i.sigRegionChangeFinished.connect(
            self.function_generator_link_graphs(annotation_graph_i, annotation_graph_o))
        annotation_graph_i.sigClicked.connect(
            self.function_generator_link_click(self.main_model.annotations, annotation))
        annotation.sigAnnotationElementChanged.connect(
            self.function_generator_link_annotaions_to_graphs(annotation, annotation_graph_i))
        self.overview_plot.addItem(annotation_graph_o)
        self.insetview_plot.addItem(annotation_graph_i)
        self.inset_annotations.append(annotation_graph_i)  # lists to easily keep track of annotations
        self.overview_annotations.append(annotation_graph_o)

        annotation.sigAnnotationElementDeleted.connect(lambda: self.insetview_plot.removeItem(annotation_graph_i))
        annotation.sigAnnotationElementDeleted.connect(lambda: self.overview_plot.removeItem(annotation_graph_o))

    def set_scenes_plot_annotations_data(self, annotations):
        '''
        :param annotations: an annotations object
        :return: None
        '''
        # Clear existing annotations
        for item in self.inset_annotations:
            self.insetview_plot.removeItem(item)
        for item in self.overview_annotations:
            self.overview_plot.removeItem(item)
        # Add annotation plots
        for annotation in annotations.annotations_list:
            self.add_annotaion_plot(annotation)

    def set_focus_on_annotation(self, annotation):
        if annotation is None:
            return
        state = self.overviewROI.getState()
        annotation_pos = annotation.getPos()
        self.main_model.set_time_position(annotation_pos[0]-1)
        self.main_model.set_window_pos([annotation_pos[0]-1, annotation_pos[1]+1])
        if annotation_pos[0] > state['pos'][0] and annotation_pos[0] < state['pos'][0] + state['size'][0]:
            return # skip if start of annotation is already in the plot area

        state['pos'][0] = annotation_pos[0] - .25*(state['size'][0])  # put start of annotation in first quarter of screen
        self.insetview_plot.setRange(xRange=(state['pos'][0], state['pos'][0] + state['size'][0]),
                                     yRange=(state['pos'][1], state['pos'][1] + state['size'][1]),
                                     padding=0)

    def set_scene_cursor(self):
        cursor_o = PyecogCursorItem(pos=0)
        cursor_i = PyecogCursorItem(pos=0)
        # Should these connections be made in the main window code?
        cursor_i.sigPositionChanged.connect(lambda: self.main_model.set_time_position(cursor_i.getXPos()))
        cursor_i.sigPositionChanged.connect(lambda: cursor_o.setPos(cursor_i.getPos()))
        cursor_o.sigPositionChanged.connect(lambda: cursor_i.setPos(cursor_o.getPos()))
        self.main_model.sigTimeChanged.connect(lambda: cursor_i.setPos(self.main_model.time_position))
        self.main_model.sigTimeChanged.connect(lambda: cursor_o.setPos(self.main_model.time_position))
        self.overview_plot.addItem(cursor_o)
        self.insetview_plot.addItem(cursor_i)


    def set_scene_window(self, window):
        brush = pg.functions.mkBrush(color=(0, 0, 0, 10))
        pen = pg.functions.mkPen(color=(0, 0, 0, 200))
        # window_item_o = pg.LinearRegionItem(window, brush=brush,movable=False)
        window_item_o = PyecogLinearRegionItem(window, pen=pen, brush=brush, movable=False, id=None)
        self.overview_plot.addItem(window_item_o)
        # window_item_i = pg.LinearRegionItem(window, brush=brush)
        window_item_i = PyecogLinearRegionItem(window, pen=pen, brush=brush, movable=True, id=None)
        window_item_i.setZValue(-2) # Bellow traces 0 and annotations -1
        self.insetview_plot.addItem(window_item_i)
        window_item_i.sigRegionChangeFinished.connect(lambda: window_item_o.setRegion(window_item_i.getRegion()))
        window_item_i.sigRegionChangeFinished.connect(lambda: self.main_model.set_window_pos(window_item_i.getRegion()))
        # window_item_i.sigRegionChangeFinished.connect(lambda: self.main_model.annotations.focusOnAnnotation(None))
        window_item_i.sigRegionChangeFinished.connect(lambda: self.main_model.set_time_position(self.main_model.window[0]-1))
        window_item_i.sigClicked.connect(lambda: self.main_model.annotations.focusOnAnnotation(None))
        window_item_i.sigClicked.connect(lambda: self.main_model.set_time_position(self.main_model.window[0]-1))
        self.main_model.sigWindowChanged.connect(window_item_i.setRegion)

    def graphics_object_xchanged(self):
        print('xChanged grahics object')

    def overviewROIchanged(self):
        state = self.overviewROI.getState()
        self.insetview_plot.setRange(xRange=(state['pos'][0], state['pos'][0] + state['size'][0]),
                                     yRange=(state['pos'][1], state['pos'][1] + state['size'][1]),
                                     padding=0)

    def overview_clicked(self, ev):
        '''
        ev pos is postion in 'scene' coords of mouse click
        '''
        # print('hit', ev_pos)
        # print(event, event.pos())
        pos = self.overview_plot.vb.mapSceneToView(ev.scenePos())
        center = pos
        xmin, xmax = self.insetview_plot.viewRange()[0]
        ymin, ymax = self.insetview_plot.viewRange()[1]
        # print(ymin, ymax, center.y())
        x_range = xmax - xmin
        y_range = ymax - ymin
        new_xrange = (center.x() - x_range / 2, center.x() + x_range / 2)
        # new_xrange = new_xrange - new_xrange

        new_yrange = (center.y() - y_range / 2, center.y() + y_range / 2)

        print(new_xrange)
        self.insetview_plot.setRange(xRange=new_xrange,
                                     yRange=new_yrange,
                                     padding=0)

        modifiers = ev.modifiers()
        if modifiers == QtCore.Qt.ControlModifier:
            # self.main_model.annotations.focusOnAnnotation(None)
            self.main_model.set_time_position(pos.x())

    def inset_clicked(self, ev):
        pos = self.insetview_plot.vb.mapSceneToView(ev.scenePos())
        print('insetclicked ', pos)
        print('modifiers:',ev.modifiers())
        modifiers = ev.modifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.main_model.annotations.focusOnAnnotation(None)
            if not self.is_setting_window_position:
                self.main_model.set_window_pos([pos.x(), pos.x()])
                self.is_setting_window_position = True
                return
            else:
                current_pos = self.main_model.window
                self.main_model.set_window_pos([current_pos[0], pos.x()])
        self.is_setting_window_position = False

        if modifiers == QtCore.Qt.ControlModifier:
            # self.main_model.annotations.focusOnAnnotation(None)
            self.main_model.set_time_position(pos.x())

    def overview_range_changed(self, mask=None):
        x_range, y_range = self.overview_plot.viewRange()

    def insetview_range_changed(self, mask=None):
        '''connected to signal from insetview_plot'''
        x_range, y_range = self.insetview_plot.viewRange()
        self.overviewROI.setPos((x_range[0], y_range[0]))
        self.overviewROI.setSize((x_range[1] - x_range[0], y_range[1] - y_range[0]))

        ox_range, oy_range = self.overview_plot.viewRange() # scroll the overview if the inset is on the edge
        if x_range[0] < ox_range[0]:
            self.overview_plot.vb.setXRange(x_range[0], x_range[0] + ox_range[1] - ox_range[0], padding=0)
        elif x_range[1] > ox_range[1]:
            self.overview_plot.vb.setXRange(x_range[1] - (ox_range[1] - ox_range[0]), x_range[1], padding=0)

class DateAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strns = []
        rng = self.range[1] - self.range[0] #max(values)-min(values)
        #if rng < 120:
        #    return pg.AxisItem.tickStrings(self, values, scale, spacing)
        if rng <= 2:
            string = '%H:%M:%S.%f'
            label1 = '%b %d -'
            label2 = ' %b %d, %Y'
        elif rng < 3600*24:
            string = '%H:%M:%S'
            label1 = '%b %d -'
            label2 = ' %b %d, %Y'
        elif rng >= 3600*24 and rng < 3600*24*30:
            string = '%d'
            label1 = '%b - '
            label2 = '%b, %Y'
        elif rng >= 3600*24*30 and rng < 3600*24*30*24:
            string = '%b'
            label1 = '%Y -'
            label2 = ' %Y'
        elif rng >=3600*24*30*24:
            string = '%Y'
            label1 = ''
            label2 = ''

        for x in values:
            try:
                strns.append(datetime.strftime(datetime.fromtimestamp(x),string))
            except ValueError:  ## Windows can't handle dates before 1970
                strns.append('err')
        try:
            label = time.strftime(label1, time.localtime(min(values)))+time.strftime(label2, time.localtime(max(values)))
        except ValueError:
            label = ''
        self.setLabel(text=label)
        return strns