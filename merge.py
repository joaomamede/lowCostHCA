import tkinter as tk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
import os
import pandas as pd

class PointListMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NIS Elements Pointlist Merger")

        self.selected_files = []

        # --- UI Setup ---
        self.left_frame = tk.Frame(root)
        self.left_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(self.left_frame, text="Available Files").pack()
        self.file_listbox = tk.Listbox(self.left_frame, selectmode=tk.MULTIPLE, width=50)
        self.file_listbox.pack()

        tk.Button(self.left_frame, text="Browse Files", command=self.browse_files).pack(pady=5)

        tk.Button(self.left_frame, text="-> Add to Merge", command=self.add_to_merge).pack(pady=5)

        tk.Label(self.right_frame, text="Files to Merge").pack()
        self.merge_listbox = tk.Listbox(self.right_frame, width=50)
        self.merge_listbox.pack()

        tk.Button(self.right_frame, text="Remove Selected", command=self.remove_selected).pack(pady=5)

        self.output_path_var = tk.StringVar(value=os.path.expanduser("~/pointlist.xml"))
        tk.Entry(self.right_frame, textvariable=self.output_path_var, width=50).pack(pady=5)
        tk.Button(self.right_frame, text="Save As", command=self.select_output_file).pack()

        tk.Button(self.right_frame, text="Merge & Save", command=self.merge_and_save).pack(pady=10)

    def browse_files(self):
        files = filedialog.askopenfilenames(filetypes=[("XML files", "*.xml")])
        for f in files:
            if f not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, f)

    def add_to_merge(self):
        for idx in self.file_listbox.curselection():
            file = self.file_listbox.get(idx)
            if file not in self.selected_files:
                self.selected_files.append(file)
                self.merge_listbox.insert(tk.END, file)

    def remove_selected(self):
        for idx in reversed(self.merge_listbox.curselection()):
            self.selected_files.pop(idx)
            self.merge_listbox.delete(idx)

    def select_output_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML files", "*.xml")])
        if path:
            self.output_path_var.set(path)

    # def parse_xml_to_df(self, filepath):
    #     tree = ET.parse(filepath)
    #     root = tree.getroot()

    #     # Find all elements that start with "Point" under root -> no_name
    #     points = []
    #     base = os.path.splitext(os.path.basename(filepath))[0]
    #     pointlist_root = root.find("./no_name")

    #     for child in pointlist_root:
    #         if not child.tag.startswith("Point"):
    #             continue
    #         x = float(child.find("dXPosition").attrib["value"])
    #         y = float(child.find("dYPosition").attrib["value"])
    #         z = float(child.find("dZPosition").attrib["value"])
    #         psf = float(child.find("dPFSOffset").attrib["value"])
    #         points.append({"x": x, "y": y, "z": z, "PSF": psf})

    #     df = pd.DataFrame(points)
    #     df["name"] = [f"{base}_P{idx+1:02d}" for idx in range(len(df))]
    #     return df
    def parse_xml_to_df(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()

        points = []
        base = os.path.splitext(os.path.basename(filepath))[0]
        pointlist_root = root.find("./no_name")

        for child in pointlist_root:
            if not child.tag.startswith("Point"):
                continue

            x = float(child.find("dXPosition").attrib["value"])
            y = float(child.find("dYPosition").attrib["value"])
            z = float(child.find("dZPosition").attrib["value"])
            psf = float(child.find("dPFSOffset").attrib["value"])
            strname_elem = child.find("strName")
            orig_name = strname_elem.attrib.get("value", "").strip()
            checked = child.find("bChecked").attrib.get("value", "true")

            if not orig_name:
                orig_name = f"P{len(points)+1:02d}"

            full_name = f"{base}_{orig_name}"
            points.append({
                "name": full_name,
                "x": x,
                "y": y,
                "z": z,
                "PSF": psf,
                "checked": checked
            })

        return pd.DataFrame(points)


    def dataframe_to_xml(self, df):
        xml_lines = [
            '<variant version="1.0">',
            '<no_name runtype="CLxListVariant">',
            '<bIncludeZ runtype="bool" value="false"/>',
            '<bPFSEnabled runtype="bool" value="true"/>'
        ]

        for idx, row in df.iterrows():
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
        return '\n'.join(xml_lines)

    # def dataframe_to_xml(self, df):
    #     xml_lines = [
    #         '<variant version="1.0">',
    #         '<no_name runtype="CLxListVariant">',
    #         '<bIncludeZ runtype="bool" value="false"/>',
    #         '<bPFSEnabled runtype="bool" value="true"/>'
    #     ]

    #     for idx, row in df.iterrows():
    #         point_xml = [
    #             f'<Point{idx:05d} runtype="NDSetupMultipointListItem">',
    #             '<bChecked runtype="bool" value="true"/>',
    #             f'<strName runtype="CLxStringW" value="{row["name"]}"/>',
    #             f'<dXPosition runtype="double" value="{row["x"]}"/>',
    #             f'<dYPosition runtype="double" value="{row["y"]}"/>',
    #             f'<dZPosition runtype="double" value="{row["z"]}"/>',
    #             f'<dPFSOffset runtype="double" value="{row["PSF"]}"/>',
    #             '<baUserData runtype="CLxByteArray" value=""/>',
    #             f'</Point{idx:05d}>'
    #         ]
    #         xml_lines.extend(point_xml)

    #     xml_lines.extend(['</no_name>', '</variant>'])
    #     return '\n'.join(xml_lines)

    def merge_and_save(self):
        if not self.selected_files:
            messagebox.showerror("Error", "No files selected to merge.")
            return

        merged_df = pd.concat([self.parse_xml_to_df(f) for f in self.selected_files], ignore_index=True)
        output_xml = self.dataframe_to_xml(merged_df)

        with open(self.output_path_var.get(), "w", encoding="utf-8") as f:
            f.write(output_xml)

        messagebox.showinfo("Success", f"File saved to: {self.output_path_var.get()}")

# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = PointListMergerApp(root)
    root.mainloop()
