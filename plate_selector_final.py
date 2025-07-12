import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QGridLayout, QLabel, QFileDialog, QHBoxLayout, QSlider
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QPen
import json

class WellPlateSelector(QWidget):
    def __init__(self):
        super().__init__()

        self.number_per_well = 10 
        self.well_diameter = 3.5
        self.distance = 0.340432#0.5
        self.offset = {'x':48510,'y':-31800}
        self.PSF = 7050
        self.well_to_well_distance = 9
        self.initUI()
        self.drag_start_pos = None
        self.ctrl_pressed = False
        self.drag_end_pos = None

    def initUI(self):
        self.selected_wells = set()

        self.setWindowTitle('96-Well Plate Selector')
        self.setGeometry(100, 100, 800, 600)

        main_layout = QHBoxLayout()

        # Left Side Layout
        left_layout = QVBoxLayout()

        grid_layout = QGridLayout()
        self.button_grid = []

        rows = 'ABCDEFGH'
        columns = range(1, 13)

        for i, row_char in enumerate(rows):  # Alphabetic rows
            row = []
            for j, col_num in enumerate(columns):  # Numeric columns
                label = f'{row_char}{col_num}'
                button = QPushButton(label)
                button.setFixedSize(50, 50)
                button.clicked.connect(self.buttonClicked)
                button.setCheckable(True)
                
                # Set button style to make it circular
                button.setStyleSheet("QPushButton {"
                                      "border-radius: 25px;"
                                      "border: 2px solid black;"
                                      "}"
                                      "QPushButton::pressed"
                                      "{"
                                      "background-color : yellow;"
                                      "}"
                                      "QPushButton::checked"
                                      "{"
                                      "background-color : red;"
                                      "}")
                
                row.append(button)
                grid_layout.addWidget(button, i, j)
            self.button_grid.append(row)

        left_layout.addLayout(grid_layout)

        self.output_label = QLabel('Selected Wells: ')
        left_layout.addWidget(self.output_label)

        # Save File Button
        self.save_button = QPushButton('Save File')
        self.save_button.clicked.connect(self.saveToFile)
        left_layout.addWidget(self.save_button)

        main_layout.addLayout(left_layout)

        # Right Side Layout
        right_layout = QVBoxLayout()

        # Number Per Well Slider
        self.number_per_well_slider = self.createSlider_int('Number Per Well', 1, 50, self.number_per_well)
        right_layout.addLayout(self.number_per_well_slider)
        
        #Distance between wells
        self.well_to_well_distance_slider = self.createSlider_float('Distance Between Wells in mm', 1, 20, self.well_to_well_distance )
        right_layout.addLayout(self.well_to_well_distance_slider)
        
        # Well Diameter Slider
        self.well_diameter_slider = self.createSlider_float('Well Diameter in mm', 0, 10, self.well_diameter)
        right_layout.addLayout(self.well_diameter_slider)

        # Distance Slider
        self.distance_slider = self.createSlider_float('Distance in mm', 0.15, 1.5, self.distance)
        right_layout.addLayout(self.distance_slider)

        # Offset X Slider
        self.offset_x_slider = self.createSlider_int('Offset X in mm', -57000, 57000, self.offset['x'])
        right_layout.addLayout(self.offset_x_slider)

        # Offset Y Slider
        self.offset_y_slider = self.createSlider_int('Offset Y in mm', -37500, 37500, self.offset['y'])
        right_layout.addLayout(self.offset_y_slider)

        # PSF Slider
        self.PSF_slider = self.createSlider_int('PSF', 0, 20000, self.PSF)
        right_layout.addLayout(self.PSF_slider)

        main_layout.addLayout(right_layout)


        self.setLayout(main_layout)
    def createSlider_float(self, label, min_val, max_val, default_val):
        slider_layout = QVBoxLayout()

        slider_label = QLabel(f'{label}: {default_val:.2f}')
        
        # Create QSlider with float values
        slider = QSlider(Qt.Horizontal)
        slider.setRange(int(min_val * 100), int(max_val * 100))  # Multiply by 100 to allow 2 decimal places
        slider.setValue(int(default_val * 100))
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(int((max_val - min_val) * 100 // 10))  # Multiply by 100 to allow 2 decimal places
        slider.valueChanged.connect(lambda value, l=slider_label: self.sliderChanged(value / 100.0, l))  # Divide by 100 to get float value

        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(slider)

        return slider_layout

    def createSlider_int(self, label, min_val, max_val, default_val):
        slider_layout = QVBoxLayout()

        slider_label = QLabel(f'{label}: {default_val}')
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval((max_val - min_val) // 10)
        slider.valueChanged.connect(lambda value, l=slider_label: self.sliderChanged(value, l))

        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(slider)

        return slider_layout

    def sliderChanged(self, value, label):
        label.setText(f'{label.text().split(":")[0]}: {value}')

    # ... (rest of the methods remain the same)

    def buttonClicked(self):
        button = self.sender()
        index = self.getButtonIndex(button)

        if button.isChecked():
            self.selected_wells.add(index)
        else:
            self.selected_wells.discard(index)

        self.updateOutput()

    def getButtonIndex(self, button):
        for i, row in enumerate(self.button_grid):
            for j, btn in enumerate(row):
                if btn is button:
                    return i*12 + j + 1
        return -1

    def updateOutput(self):
        # mapped_wells = [self.mapIndexToWellID(index) for index in sorted(self.selected_wells)]
        ordered_indices = self.getSnakeOrderedWells()
        mapped_wells = [self.mapIndexToWellID(index) for index in ordered_indices]
        selected_wells_str = ', '.join(mapped_wells)
        self.output_label.setText(f'Selected Wells: {selected_wells_str}')

    def mapIndexToWellID(self, index):
        print(self.selected_wells, self.well_diameter_slider.itemAt(1).widget().value() / 100.0 )
        row = 'ABCDEFGH'[(index -1) // 12]
        col = (index )% 12
        if col == 0:
            col = 12
        return f'{row}{col}'

    def getSnakeOrderedWells(self):
        rows = 'ABCDEFGH'
        cols = list(range(1, 13))

        # Create a dictionary to group selected wells by row
        wells_by_row = {r: [] for r in rows}

        for index in self.selected_wells:
            row_char = rows[(index - 1) // 12]
            col_num = (index % 12)
            if col_num == 0:
                col_num = 12
            wells_by_row[row_char].append(col_num)

        ordered_indices = []

        for i, row in enumerate(rows):
            cols_in_row = wells_by_row[row]
            if not cols_in_row:
                continue
            # Sort columns in desired order
            if i % 2 == 0:
                cols_in_row_sorted = sorted(cols_in_row)
            else:
                cols_in_row_sorted = sorted(cols_in_row, reverse=True)

            for col in cols_in_row_sorted:
                # Calculate index again: row * 12 + col
                idx = i * 12 + col
                ordered_indices.append(idx)

        return ordered_indices

    def wells_to_coordinates(self):
        import numpy as np
        import pandas as pd
        def generate_coordinates(x_center, y_center, diameter, euclidean_distance, num_points=10):
            import math,random
            coordinates = []
            
            while len(coordinates) < num_points:
                x = random.uniform(x_center - diameter/2, x_center + diameter/2)
                y = random.uniform(y_center - diameter/2, y_center + diameter/2)
                
                valid = True
                for coord in coordinates:
                    distance = math.sqrt((x - coord[0])**2 + (y - coord[1])**2)
                    if distance < euclidean_distance:
                        valid = False
                        break
                        
                if valid:
                    coordinates.append((x, y))
            
            return coordinates


        #todo get from sliders
        self.number_per_well = self.number_per_well_slider.itemAt(1).widget().value()
        self.well_diameter = self.well_diameter_slider.itemAt(1).widget().value() / 100.0
        self.distance = self.distance_slider.itemAt(1).widget().value()/ 100.0
        self.offset = {'x':(self.offset_x_slider.itemAt(1).widget().value()),
                       'y':(self.offset_y_slider.itemAt(1).widget().value())}
        self.PSF = self.PSF_slider.itemAt(1).widget().value()
        print(self.well_diameter,self.distance,self.offset)
        #transform A1 to H12 to [1*number*offset , 1* letter*offset]
        #ord('D')-ord('A')
        lista = []
        
        # for _well in self.selected_wells:
        ordered_indices = self.getSnakeOrderedWells()
        for _well in ordered_indices:
            #col, x
            print('selected wells:', _well)
            lista.append([self.mapIndexToWellID(_well), 
                          #           Y
                          #          -30
                          #           ^
                          #           |
                          #           |
                          #           |
                          #           |
                          #           |
                          # 48<-------x-----> -48
                          #           |
                          #           |
                          #           |
                          #           |
                          #           |
                          #           30  
                          #X coordinates reduce when moving top down
                          # pos neg pos again....
                          #index starts at 1 somehow?
                          
                          ((self.offset['x']/1000.0) - (((_well-1) %12 )*  self.well_to_well_distance)) *1000,
                          #y coordinates are negative on the left and positive moving to the right
                          ((self.offset['y']/1000.0) + (((_well-1) // 12) * self.well_to_well_distance)) *1000,
                          self.PSF ])
            
            #row, y
        # lista_final = lista
        lista_final = []
        
        for sub_well in lista:
            #if you want all random coords offset to be the same in all wells, move this up
            _coords = np.asarray(generate_coordinates(sub_well[1],sub_well[2], 
                                self.well_diameter*1000,
                                self.distance*2000,
                                num_points = self.number_per_well)
                            )
            for i in range(self.number_per_well):
                lista_final.append([ sub_well[0]+'_'+str(i) , #name
                                _coords[i,0], #x are mm and xml uses um
                                _coords[i,1], #y are mm and xml uses um
                                sub_well[3], #PSF
                ]
                )
        
            
        df = pd.DataFrame(lista_final,columns=['name','x','y',"PSF"])
        df.sort_values(by=['name'])
        return df
    
    def dataframe_to_xml(self,df):
        xml_lines = [
            '<variant version="1.0">',
            '<no_name runtype="CLxListVariant">',
            '<bIncludeZ runtype="bool" value="false"/>',
            '<bPFSEnabled runtype="bool" value="true"/>'
        ]

        for idx, row in df.iterrows():
            point_xml = [
                f'<Point{idx:05d} runtype="NDSetupMultipointListItem">',
                '<bChecked runtype="bool" value="true"/>',
                f'<strName runtype="CLxStringW" value="{row["name"]}"/>',
                f'<dXPosition runtype="double" value="{row["x"]}"/>',
                f'<dYPosition runtype="double" value="{row["y"]}"/>',
                '<dZPosition runtype="double" value="100"/>',  # Constant Z position
                f'<dPFSOffset runtype="double" value="{row["PSF"]}"/>',
                '<baUserData runtype="CLxByteArray" value=""/>',
                '</Point{:05d}>'.format(idx)
            ]
            xml_lines.extend(point_xml)

        xml_lines.extend([
            '</no_name>',
            '</variant>'
        ])

        xml_str = '\n'.join(xml_lines)
        return xml_str


    
    def mousePressEvent(self, event):
        self.drag_start_pos = event.pos()
        self.ctrl_pressed = QApplication.keyboardModifiers() & Qt.ControlModifier
        
        # Clearing previous selection unless Ctrl key is pressed
        if not self.ctrl_pressed:
            for row in self.button_grid:
                for btn in row:
                    btn.setChecked(False)

    def mouseReleaseEvent(self, event):
        if self.drag_start_pos is None:
            return
        
        drag_end_pos = event.pos()
        
        # Getting selection rectangle
        selection_rect = QRect(self.drag_start_pos, drag_end_pos).normalized()
        
        for row in self.button_grid:
            for btn in row:
                if selection_rect.contains(btn.geometry().center()):
                    btn.setChecked(True)
                    self.selected_wells.add(self.getButtonIndex(btn))
        
        self.updateOutput()
        self.drag_start_pos = None
        self.drag_end_pos = None
        self.update()

    def mouseMoveEvent(self, event):
        if self.drag_start_pos is None:
            return

        self.drag_end_pos = event.pos()
        self.update()

    def paintEvent(self, event):
        if self.drag_start_pos and self.drag_end_pos:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
            selection_rect = QRect(self.drag_start_pos, self.drag_end_pos).normalized()
            painter.drawRect(selection_rect)

    def saveToFile(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save Selected Wells", "", "Text Files (*.txt);;All Files (*)", options=options)
        df = self.wells_to_coordinates()
        print(df)
        output_xml = (self.dataframe_to_xml(
            df
            # self.wells_to_coordinates()
            ))
        if fileName:
            with open(fileName, 'w') as f:
                f.write(output_xml)
                    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WellPlateSelector()
    window.show()
    sys.exit(app.exec_())
