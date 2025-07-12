import sys
import os
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QMainWindow, QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QComboBox, QCheckBox
import pyqtgraph as pg
from pyqtgraph import ImageView, ROI, RectROI, EllipseROI, PolyLineROI
from PyQt5.QtWidgets import QGraphicsRectItem
from bioio import BioImage
import bioio_nd2


class ROISelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ND2 ROI Selector (PyQt5)")

        self.image_view = ImageView()
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()

        self.image_data = None
        self.nd2_metadata = None
        self.physical_pixel_size = None
        self.target_pixel_size = 0.160
        self.overlap = 0.05
        self.basename = "Image"

        self.roi_items = []
        self.roi_data = []
        self.fov_items_by_roi = {}
        self.current_roi_type = 'Rectangle'
        self.show_fovs = False
        self.selected_roi = None

        self.shape_selector = QComboBox()
        self.shape_selector.addItems(['Rectangle', 'Ellipse', 'Circle', 'Freehand'])
        self.shape_selector.currentTextChanged.connect(self.change_shape)

        self.fov_checkbox = QCheckBox("Show Fields of View")
        self.fov_checkbox.stateChanged.connect(self.toggle_fovs)

        load_btn = QPushButton("Open ND2")
        load_btn.clicked.connect(self.load_nd2)

        param_btn = QPushButton("Set Imaging Parameters")
        param_btn.clicked.connect(self.set_parameters)

        save_btn = QPushButton("Save Point List")
        save_btn.clicked.connect(self.save_pointlist)

        add_roi_btn = QPushButton("Add ROI")
        add_roi_btn.clicked.connect(self.add_roi)

        controls = QHBoxLayout()
        controls.addWidget(load_btn)
        controls.addWidget(param_btn)
        controls.addWidget(save_btn)
        controls.addWidget(QLabel("ROI Shape:"))
        controls.addWidget(self.shape_selector)
        controls.addWidget(add_roi_btn)
        controls.addWidget(self.fov_checkbox)

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addLayout(controls)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.image_view.scene.sigMouseClicked.connect(self.select_roi)
        self.installEventFilter(self)

    def load_nd2(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open ND2 file", "", "ND2 files (*.nd2)")
        if not path:
            return

        self.basename = os.path.splitext(os.path.basename(path))[0]
        bioimg = BioImage(path, reader=bioio_nd2.Reader)
        self.nd2_metadata = bioimg.metadata.images[0].pixels.planes[0]
        self.physical_pixel_size = bioimg.metadata.images[0].pixels.physical_size_x
        img = bioimg.get_image_data().squeeze()
        if img.ndim == 3:
            img = img[0]
        p1, p99 = np.percentile(img, (1, 99))
        img = np.clip((img - p1) / (p99 - p1), 0, 1)

        self.image_data = img
        self.image_view.setImage(np.flipud(img.T), autoLevels=False)

    def set_parameters(self):
        px, ok1 = QInputDialog.getDouble(self, "Target Pixel Size", "Enter target pixel size (e.g. 0.108):", self.target_pixel_size, 0.001, 10.0, 5)
        ov, ok2 = QInputDialog.getDouble(self, "Overlap (%)", "Enter overlap % (e.g. 10):", self.overlap * 100, 0, 99.9, 1)
        if ok1:
            self.target_pixel_size = px
        if ok2:
            self.overlap = ov / 100.0

    def change_shape(self, shape):
        self.current_roi_type = shape

    def toggle_fovs(self, state):
        self.show_fovs = state == QtCore.Qt.Checked
        self.clear_fovs()
        self.roi_data = []
        if self.show_fovs:
            for roi in self.roi_items:
                self.compute_tiles(roi, update_fovs=True)

    def add_roi(self):
        if self.image_data is None:
            return

        shape = self.current_roi_type
        size = 100
        pos = [self.image_data.shape[1] // 2, self.image_data.shape[0] // 2]

        if shape == 'Rectangle':
            roi = RectROI(pos, [size, size], pen='r')
        elif shape == 'Ellipse' or shape == 'Circle':
            roi = EllipseROI(pos, [size, size], pen='g')
        elif shape == 'Freehand':
            roi = PolyLineROI([pos, [pos[0]+size, pos[1]], [pos[0]+size, pos[1]+size], [pos[0], pos[1]+size]], closed=True, pen='y')
        else:
            return

        roi.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        roi.setZValue(10)

        self.image_view.addItem(roi)
        self.roi_items.append(roi)

    def select_roi(self, event):
        pos = event.scenePos()
        for roi in self.roi_items:
            if roi.boundingRect().contains(roi.mapFromScene(pos)):
                self.selected_roi = roi
                break

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Delete:
            if self.selected_roi and self.selected_roi in self.roi_items:
                self.delete_roi(self.selected_roi)
                self.selected_roi = None
                return True
        return super().eventFilter(source, event)

    def delete_roi(self, roi):
        if roi in self.roi_items:
            self.image_view.removeItem(roi)
            self.roi_items.remove(roi)
            self.clear_fovs()
            self.roi_data = []
            if self.show_fovs:
                for r in self.roi_items:
                    self.compute_tiles(r, update_fovs=True)

    def clear_fovs(self):
        for items in self.fov_items_by_roi.values():
            for item in items:
                self.image_view.removeItem(item)
        self.fov_items_by_roi = {}

    def compute_tiles(self, roi, update_fovs=False):
        if update_fovs:
            for item in self.fov_items_by_roi.get(roi, []):
                self.image_view.removeItem(item)
            self.fov_items_by_roi[roi] = []

            for item in self.fov_items_by_roi.get(roi, []):
                self.image_view.removeItem(item)
            self.fov_items_by_roi[roi] = []

        roi_number = self.roi_items.index(roi) + 1
        px_size_preview = self.physical_pixel_size
        target_pixel_size = self.target_pixel_size
        fov_pixels = 2040
        fov_um = target_pixel_size * fov_pixels
        step_um = fov_um * (1 - self.overlap)

        stage_x_center = self.nd2_metadata.position_x
        stage_y_center = self.nd2_metadata.position_y
        stage_z = self.nd2_metadata.position_z

        x0_img, y0_img = roi.pos()
        w_img, h_img = roi.size()
        img_center_x = self.image_data.shape[1] / 2
        img_center_y = self.image_data.shape[0] / 2

        stage_x0 = stage_x_center + (x0_img - img_center_x) * px_size_preview
        stage_y0 = stage_y_center + (y0_img - img_center_y) * px_size_preview
        stage_x1 = stage_x_center + ((x0_img + w_img) - img_center_x) * px_size_preview
        stage_y1 = stage_y_center + ((y0_img + h_img) - img_center_y) * px_size_preview

        width_um = stage_x1 - stage_x0
        height_um = stage_y1 - stage_y0

        nx = max(1, int(np.floor(width_um / step_um)))
        ny = max(1, int(np.floor(height_um / step_um)))

        # Adjusted start to keep centers within ROI
        x_start = stage_x0 + (width_um - (nx - 1) * step_um) / 2
        y_start = stage_y0 + (height_um - (ny - 1) * step_um) / 2

        roi_mask = roi.getArrayRegion(np.ones_like(self.image_data).T, self.image_view.imageItem).astype(bool).T

        for iy in range(ny):
            row_letter = chr(ord('A') + iy)
            xs = [x_start + i * step_um for i in range(nx)]
            if iy % 2 == 1:
                xs = xs[::-1]
            for ix, px in enumerate(xs):
                py = y_start + iy * step_um
                dx = (px - stage_x_center) / px_size_preview + img_center_x
                dy = (py - stage_y_center) / px_size_preview + img_center_y

                if (0 <= int(dy) < roi_mask.shape[0]) and (0 <= int(dx) < roi_mask.shape[1]):
                    if not roi_mask[int(dy), int(dx)]:
                        continue

                col_number = ix + 1
                name = f"{self.basename}_ROI{roi_number}_{row_letter}{col_number}"

                self.roi_data.append({
                    "name": name,
                    "x": px,
                    "y": py,
                    "z": stage_z,
                    "PSF": 0.0,
                    "checked": "true"
                })

                if update_fovs:
                    fov_px = fov_um / px_size_preview
                    rect = QGraphicsRectItem(dx - fov_px / 2, dy - fov_px / 2, fov_px, fov_px)
                    rect.setPen(pg.mkPen('lime', width=1))
                    rect.setVisible(self.show_fovs)
                    self.image_view.addItem(rect)
                    self.fov_items_by_roi[roi].append(rect)

    def save_pointlist(self):
        if not self.roi_items:
            QMessageBox.warning(self, "Error", "No ROIs defined.")
            return

        self.roi_data = []
        for roi in self.roi_items:
            self.compute_tiles(roi, update_fovs=False)

        if not self.roi_data:
            QMessageBox.warning(self, "Error", "No points to save.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Point List", "", "XML Files (*.xml)")
        if not path:
            return

        xml_lines = [
            '<variant version="1.0">',
            '<no_name runtype="CLxListVariant">',
            '<bIncludeZ runtype="bool" value="false"/>',
            '<bPFSEnabled runtype="bool" value="true"/>'
        ]

        for idx, row in enumerate(self.roi_data):
            point_xml = [
                f'<Point{idx:05d} runtype="NDSetupMultipointListItem">',
                f'<bChecked runtype="bool" value="{row["checked"]}"/>',
                f'<strName runtype="CLxStringW" value="{row["name"]}"/>',
                f'<dXPosition runtype="double" value="{row["x"]}"/>',
                f'<dYPosition runtype="double" value="{row["y"]}"/>',
                f'<dZPosition runtype="double" value="{row["z"]}"/>',
                f'<dPFSOffset runtype="double" value="{row["PSF"]}"/>',
                '<baUserData runtype="CLxByteArray" value=""/>',
                f'</Point{idx:05d}>'
            ]
            xml_lines.extend(point_xml)

        xml_lines.extend(['</no_name>', '</variant>'])
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(xml_lines))

        QMessageBox.information(self, "Saved", f"Point list saved to {path}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = ROISelector()
    win.show()
    sys.exit(app.exec_())

