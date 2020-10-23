#!/usr/bin/python3

from tkinter import *
from PIL import Image
from PIL import ImageTk
import subprocess
import xml.etree.ElementTree
import os
import platform
import string

FORE_COLOR="#909090"
EDGE_COLOR="#606060"

CHAOS=False

aliases = [
    ("kf", "Kokiri Forest"),
    ("lw", "Lost Woods"),
    ("wb", "LW Bridge"),
    ("sf", "SF Meadow"),

    ("", ""),

    ("go", "Goron City"),
    ("mc", "DM Crater"),
    ("mt", "DM Trail"),

    ("", ""),

    ("zr", "Z River"),
    ("zd", "Z Domain"),
    ("zf", "Z Fount"),

    ("", ""),

    ("gv", "G Valley"),
    ("gf", "G Fort"),
    ("hw", "H Wasteland"),
    ("dc", "D Colossus"),

    ("", ""),

    ("lh", "Lake Hylia"),
    ("hf", "H Field"),
    ("ll", "LL Ranch"),
    ("ma", "Market"),
    ("hc", "H Castle"),

    ("", ""),

    ("kv", "Kakariko V."),
    ("gr", "Graveyard"),
    ("dw", "Dampes/Windmill"),
    ("po", "Potion Shop"),

    ("", ""),

    ("mi", "Minuet"),
    ("bo", "Bolero"),
    ("se", "Serenade"),
    ("no", "Nocturne"),
    ("re", "Requiem"),
    ("pr", "Prelude"),

    ("", ""),

    ("ad", "Adult"),
    ("ch", "Child")
]

def mangle_path(s):
    if platform.system() == "Windows":
        return s.replace("/", "\\")
    return s

if platform.system() == "Windows":
    os.environ["PATH"] += os.pathsep + mangle_path(os.path.dirname(os.path.realpath(__file__)) + "/windows/graphviz")
sys.path.insert(0, mangle_path(os.path.dirname(os.path.realpath(__file__)) + "/python/site-packages"))

import pydot

def graph_reduce(graph, roots, filename):
    r = list(roots)
    text_file = open(filename, "wb")
    text_file.write(graph.create_dot())
    text_file.close()

    (g,)=pydot.graph_from_dot_file(filename)
    g.set("rankdir", "LR")
    g.set("bgcolor", "#181818")
    gdict = { n.get_name() : [] for n in g.get_node_list() }

    for edge in g.get_edge_list():
        source = edge.get_source()
        dest   = edge.get_destination()
        gdict[source].append(dest)
        gdict[dest].append(source)

    def addRoots(l):
        for root in l:
            if not root in r:
                r.append(root)
                addRoots(gdict[root])

    for root in roots:
        addRoots(gdict[root])

    processed_edges = []

    for edge in g.get_edge_list():
        edge.set("color", EDGE_COLOR)
        edge.set("fontcolor", FORE_COLOR)

        source = edge.get_source()
        dest   = edge.get_destination()

        if ((not source in r) and (not dest in r)) or source == dest:
            g.del_edge(source, dest)
            continue
        if (source in r) != (dest in r):
            raise Exception("Edge half attached to root nodes")

        if (source, dest) in processed_edges or not CHAOS:
            continue
        processed_edges.append((source, dest))

        compound = pydot.Edge(source, dest)
        compound.set("color", EDGE_COLOR)
        compound.set("fontcolor", FORE_COLOR)
        compound_label = ""

        source_node = g.get_node(source)[0]
        source_label_lines = source_node.get("label").replace("\\\n", "").splitlines()

        for l in [ edge1.get("label") for edge1 in  g.get_edge(source, dest)]:
            if not l:
                continue
            for line in source_label_lines:
                if line.split(" : ")[0] == l.strip("\""):
                    compound_label += line + "\n"
                    source_label_lines.remove(line)
                    break

        node_label = ""
        for line in source_label_lines:
            node_label += line + "\n"
        source_node.set("label", node_label)

        g.del_edge(source, dest)

        if (compound_label):
            g.add_edge(compound)
            compound.set("label", "\"" + compound_label + "\"")
        else:
            dest_node = g.get_node(dest)
            if dest_node[0].get("label") == "\"?\"":
                g.del_node(dest)

    for node in g.get_node_list():
        if node.get("color") is None:
            node.set("color", FORE_COLOR)
        if node.get("fontcolor") is None:
            node.set("fontcolor", FORE_COLOR)
        if not node.get_name() in r:
            g.del_node(node.get_name())

    text_file = open(filename, "wb")
    text_file.write(g.create_dot())
    text_file.close()

(world,)=pydot.graph_from_dot_file("OWER.dot")

def unparse_interiors(interiors):
    ret = interiors["title"]
    if (interiors["woth"].get()):
        ret += " (Hero)"
    if (interiors["fool"].get()):
        ret += " (Fool)"
    ret += "\n"
    for segment in interiors["segments"]:
        ret += "\n"
        for interior in segment:
            if interior["checked"].get():
                continue
            ret += interior["name"].strip(">")
            if interior["notes"].get():
                ret += " : " + interior["notes"].get()
            else:
                ret += " ?"
            ret += "\n"
    return ret

def parse_interiors(text):
    ret = None;
    segment = None;
    for line in [ line_unstripped.strip("\"") for line_unstripped in text.splitlines()]:
        if ret is None:
            woth = IntVar()
            woth.set(0)
            fool = IntVar()
            fool.set(0)
            ret = { "title" : line, "segments" : [], "woth" : woth, "fool" : fool }
            continue
        if line:
            checked = IntVar()
            checked.set(0)
            notes = StringVar()
            notes.set("")
            name = line
            if len(line.split(":")) == 2:
                notes.set(line.split(":")[1])
                name = line.split(":")[0]
            segment.append({ "checked" : checked, "name" : name, "notes" : notes })
        else:
            if segment is not None:
                ret["segments"].append(segment)
            segment = []
    if segment and len(segment) != 0:
        ret["segments"].append(segment)
    return ret

window = Tk()
window.title("Rattrack")

#OOTR specific
roots = [ "Adult", "Child" ]

edges = {}
interiorss = {}

def make_external(node, exit, shape, seq):
    name = node.get_name() + "_" + str(seq)
    question = pydot.Node(name)
    question.set("label", "\"?\"")
    question.set("shape", shape)
    world.add_node(question)
    edge = pydot.Edge(node.get_name(), name)
    edge.set("label", "\"" + exit + "\"")
    world.add_edge(edge)

for node in world.get_node_list():
    edges[node.get_name()] = []

    question_seq = 0

    if node.get("shape") == "\"box\"":
        interiors = parse_interiors(node.get("label"))
        for exit in [ item["name"] for item in interiors["segments"][0] ]:
            if exit[0] == ">" or CHAOS:
                make_external(node, exit.strip(">"), "\"box\"", question_seq)
            else:
                make_external(node, exit, "\"circle\"", question_seq)
            question_seq += 1
        if len(interiors["segments"]) > 1 and CHAOS:
            for segment in interiors["segments"][1:]:
                for exit in [ item["name"] for item in segment ]:
                    if exit[0] == ">":
                        make_external(node, exit.strip(">"), "\"box\"", question_seq)
                        question_seq += 1
        if not CHAOS:
            interiors["segments"] = interiors["segments"][1:]
        node.set("label", "\"" + unparse_interiors(interiors) + "\"")
        interiorss[node.get_name()] = interiors

open_windows = []

class TextWindow(object):
    def __init__(self, master, node, canvas):
        self.node = node
        self.canvas = canvas
        top = self.top = Toplevel(master)
        top.protocol("WM_DELETE_WINDOW", self.finish)

        self.interiors = interiors = interiorss[node.get_name()]
        top.title(interiors["title"])

        checkedlabel = Label(top, text = "Cleared")
        interiorlabel = Label(top, text = "Check")
        noteslabel = Label(top, text = "Notes")
        checkedlabel.grid(row=0, column=1, padx=15, pady=15)
        interiorlabel.grid(row=0, column=0, padx=15, pady=15, sticky=W)
        noteslabel.grid(row=0, column=2, padx=15, pady=15)

        row = 1
        for segment in interiors["segments"]:
            for interior in segment:
                checkbutton = Checkbutton(top, variable = interior["checked"])
                label = Label(top, text = interior["name"].strip(">"))
                notes = Entry(top, textvariable = interior["notes"])
                checkbutton.grid(row=row, column=1, padx=15)
                label.grid(row=row, column=0, padx=15, sticky=W)
                notes.grid(row=row, column=2, padx=15)
                row += 1
            top.grid_rowconfigure(row, minsize=20)
            row += 1

        if (row == 1):
            self.finish()
            return

        #OOTR specific
        woth = Checkbutton(top, text="Way of the Hero", variable = interiors["woth"])
        fool = Checkbutton(top, text="A Foolish Choice", variable = interiors["fool"])
        woth.grid(row=row, column=0, columnspan=3, sticky=W)
        row += 1
        fool.grid(row=row, column=0, columnspan=3, sticky=W)
        row += 1
        top.grid_rowconfigure(row, minsize=20)
        row += 1

        ok = Button(top, text='Refresh', command=self.refresh)
        ok.grid(row=row, column=0, columnspan=3)

        open_windows.append(self)
        master.window.wait_window(top)

    def refresh(self):
        self.node.set("label", "\"" + unparse_interiors(self.interiors)+ "\"")
        self.canvas.redraw()

    def finish(self):
        self.top.destroy()
        self.refresh()

def new_edge(a_region, b_region, replaces, headlabel=None, taillabel=None, label=None):
    edge = pydot.Edge(a_region, b_region)
    edge.set("color", EDGE_COLOR)
    edge.set("fontcolor", FORE_COLOR)
    edge_data = { "active" : True, "edge":edge, "replaces" : replaces }
    edges[a_region].append(edge_data)
    edges[b_region].append(edge_data)
    name = a_region
    if taillabel is not None:
        name += ":" + taillabel
        edge.set("taillabel", taillabel)
    if label is not None:
        name += ":" + label
        edge.set("label", label)
    name += " <-> " + b_region
    if headlabel is not None:
        name += ":" + headlabel
        edge.set("headlabel", headlabel)
    edge.set("name", name)
    world.add_edge(edge)
    for replace in replaces:
        world.del_edge(replace)
    return edge

class TrackerCanvas(Canvas):

    def __init__(self, window):
        super().__init__(window)
        self.zoom_factor = 1000
        self.window = window
        self.bind("<ButtonPress-1>", self.startDrag)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<ButtonRelease-1>", self.stopDrag)
        self.bind("<ButtonPress-3>", self.menu)
        self.location = "Select"
        self.headline = ""
        self.redraw()

    def add_root(self, r):
        roots.append(r)
        self.redraw()

    def del_root(self, r):
        roots.remove(r)
        self.redraw()

    def svg_get_clicked_thing(self, x, y):

        def prune_svg_junk(s):
            return s.split("}")[1]

        svg_x = float(self.et.attrib["width"].split("pt")[0]) * float(x) / float(self.width)
        svg_y = float(self.et.attrib["height"].split("pt")[0]) * (float(y) / float(self.height) - 1)
        for level1 in self.et:
            for level2 in level1:
                tag = prune_svg_junk(level2.tag)
                if tag == "g":
                    hit = False
                    title = None
                    for level3 in level2:
                        tag = prune_svg_junk(level3.tag)
                        attrib = level3.attrib
                        if      tag == "ellipse" and \
                                float(svg_x) > float(attrib["cx"]) - float(attrib["rx"]) and \
                                float(svg_x) < float(attrib["cx"]) + float(attrib["rx"]) and \
                                float(svg_y) > float(attrib["cy"]) - float(attrib["ry"]) and \
                                float(svg_y) < float(attrib["cy"]) + float(attrib["ry"]):
                            hit = True;
                        if      tag == "polygon":
                            points = [ (float(point.split(",")[0]), float(point.split(",")[1])) \
                                            for point in attrib["points"].split(" ") ]
                            (x_max, y_max) = points[0]
                            (x_min, y_min) = points[0]
                            for (x, y) in points:
                                if x > x_max:
                                    x_max = x;
                                if y > y_max:
                                    y_max = y;
                                if x < x_min:
                                    x_min = x;
                                if y < y_min:
                                    y_min = y;
                            if  float(svg_x) > x_min and float(svg_x) < x_max and \
                                float(svg_y) > y_min and float(svg_y) < y_max:
                                hit = True;
                        if      tag == "title":
                            title = level3.text
                    if hit:
                        return title
        return None

    def text_redraw(self):
        os.system('cls' if os.name=='nt' else 'clear')
        print(self.headline)
        print("")
        if (self.location == "Select" or self.location == "Select1"):
            for (alias, longform) in aliases:
                print(("[" + alias + "] " if alias else "") + longform)

    def redraw(self):

        self.text_redraw()

        graph_reduce(world, roots, "reduced.dot")

        if platform.system() == "Windows":
            stem = os.path.dirname(os.path.realpath(__file__)) + "/windows/"
            dot_path = mangle_path(stem + "graphviz/dot.exe")
        else:
            dot_path = "dot"

        subprocess.call((dot_path + " -Tpng -o " + mangle_path("docs/reduced.png") + " reduced.dot").split(" "))
        subprocess.call((dot_path + " -Tsvg -o reduced.svg reduced.dot").split(" "))

        self.et = xml.etree.ElementTree.parse('reduced.svg').getroot()

        img = Image.open(mangle_path("docs/reduced.png"))
        if (self.zoom_factor != 1000):
            img = img.resize((int(img.width * self.zoom_factor / 1000), \
                              int(img.height * self.zoom_factor / 1000)), Image.ANTIALIAS);

        self.f = ImageTk.PhotoImage(img)

        self.width = self.f.width()
        self.height = self.f.height()

        self.window.geometry(str(self.width) + "x" + str(self.height))
        self.config(width=self.width, height=self.height)
        self.create_image(0, 0, anchor=NW, image=self.f)
        self.pack()

    def del_edge(self, edge_data):
        #Just leak it
        edge_data["active"] = False;
        world.del_edge(edge_data["edge"])
        for replace in edge_data["replaces"]:
            world.add_edge(replace)
        self.redraw()

    def name_del(self, label, clicked):
        for piece in label.split(" <-> "):
            try:
                subpieces = piece.split(":")
                if subpieces[0] == clicked:
                    return "disconnect " + subpieces[1] + " exit"
            except:
                pass
        if label.split(" <-> ")[1] == clicked:
            return "disconnect " + label.split(" <-> ")[0]
        return None

    def key(self, event=None):

        if (event.keysym == "w"):
            self.location = "Select"
            self.headline = ""
            self.text_redraw()
            return

        if (event.keysym == "x"):
            self.redraw()
            return

        if   (self.location == "Select"):
            self.char1 = event.keysym
            self.location = "Select1"
            return

        if (self.location == "Select1"):
            entered = "" + self.char1 + event.keysym
            print("Entered:" + entered) 
            for (alias, longform) in aliases:
                print(entered + "." + alias)
                if (entered == alias):
                    self.headline = "Moved Link to " + longform
                    self.location = longform
                    self.text_redraw()
                    popup = TextWindow(window, world.get_node(longform)[0], self)
                    return
            self.headline = "Region \"" + entered + "\" not valid"
            self.location = "Select"
            self.text_redraw()
            return

    def zoom_in(self, event=None):
        self.zoom_factor += 100;
        if (self.zoom_factor > 1500):
            self.zoom_factor = 1500;
        self.redraw()

    def zoom_out(self, event=None):
        self.zoom_factor -= 100;
        if (self.zoom_factor < 500):
            self.zoom_factor = 500;
        self.redraw()

    def menu(self, event):
        popup = Menu(window, tearoff=0)
        submenus = dict()
        space = True

        clicked = self.svg_get_clicked_thing(event.x, event.y)
        if clicked is not None:
            clickedn = world.get_node(clicked)[0]
            if clickedn.get("shape") == "\"box\"":
                space = False
                connected_to_something = False
                for edge_data in edges[clicked]:
                    if edge_data["active"]:
                        d = self.name_del(edge_data["edge"].get("name"), clicked)
                        def add_del_command(edge_data):
                            popup.add_command(label=d, command = lambda : self.del_edge(edge_data))
                        if d is not None:
                            add_del_command(edge_data)
                            connected_to_something = True
                if not connected_to_something:
                    if not clicked in roots:
                        return
                    def add_remove_command(name):
                        popup.add_command(label="remove", command = lambda : self.del_root(name))
                    add_remove_command(clicked)

        if space:
            for n in world.get_node_list():
                if not n.get_name() in roots and n.get("label") != "\"?\"":
                    def add_command(pop, name):
                        pop.add_command(label=interiorss[n.get_name()]["title"], \
                                        command = lambda : self.add_root(name))
                    sub_name = n.get("submenu")
                    if sub_name is not None:
                        # Adds a submenu category
                        sub_name = sub_name.strip('"')
                        if sub_name not in submenus:
                            submenus[sub_name] = Menu(window, tearoff=False)
                            popup.add_cascade(label=sub_name, menu=submenus[sub_name])
                        add_command(submenus[sub_name], n.get_name())
                    else:
                        # Add normal option to menu.
                        add_command(popup, n.get_name())

        popup.add_separator()
        popup.add_command(label="Zoom In (+)", command = lambda : self.zoom_in())
        popup.add_command(label="Zoom Out (-)", command = lambda : self.zoom_out()) 
        popup.add_separator()
        popup.add_command(label="Cancel")
        try:
            popup.tk_popup(event.x_root, event.y_root, 0)
        finally:
            popup.grab_release()

    def startDrag(self, event):
        self.startx = event.x
        self.starty = event.y

    def drag(self, event):
        self.delete(self.find_withtag('line'))
        self.create_line(self.startx, self.starty, event.x, event.y, arrow=BOTH, width=3, tag='line', fill="blue")

    def stopDrag(self, event):
        self.delete(self.find_withtag('line'))
        start = self.svg_get_clicked_thing(self.startx, self.starty)
        finish = self.svg_get_clicked_thing(event.x, event.y)
        self.do_connection(start, finish)

    def do_connection_unidirectional(self, a, b):
        if a is None or b is None:
            return False
        an = world.get_node(a)[0]
        bn = world.get_node(b)[0]
        if      a == b and \
                an.get("shape") == "\"box\"" and \
                an.get("label") != "\"?\"":
                popup = TextWindow(window, an, self)
                return True
        if      an.get("shape") == "\"circle\"" and \
                an.get("label") == "\"?\"":
            if  a == b or \
                bn.get("shape") != "\"circle\"" or \
                bn.get("label") != "\"?\"":
                return False
            a_region = None
            b_region = None
            a_label = None
            b_label = None
            replaces = []
            for edge in world.get_edge_list():
                if edge.get_destination() == a:
                    a_label = edge.get("label")
                    a_region = edge.get_source()
                    replaces.append(edge)
                if edge.get_destination() == b:
                    b_label = edge.get("label")
                    b_region = edge.get_source()
                    replaces.append(edge)
            connector = new_edge(a_region, b_region, replaces, taillabel=a_label, headlabel=b_label)
            connector.set("arrowhead", "\"none\"")
            connector.set("arrowtail", "\"none\"")
            connector.set("minlen", "2.0")
            self.redraw()
            return True
        elif    an.get("shape") == "\"box\"" and \
                an.get("label") == "\"?\""   and \
                bn.get("shape") == "\"box\"" and \
                bn.get("label") != "\"?\"":
            for edge in world.get_edge_list():
                if edge.get_destination() == a:
                    a_label = edge.get("label")
                    a_region = edge.get_source()
                    a_edge = edge
            connector = new_edge(a_region, b, [a_edge], label = a_label)
            self.redraw()
            return True
        elif    an.get("shape") == "\"circle\"" and \
                bn.get("shape") == "\"box\"":
            connector = new_edge(a, b, [])
            self.redraw()
            return True
        else:
            return False

    def do_connection(self, a, b):
        if (not self.do_connection_unidirectional(a, b)) :
            self.do_connection_unidirectional(b, a)

canvas = TrackerCanvas(window)

pos = 0

window.bind("<plus>", canvas.zoom_in)
window.bind("<minus>", canvas.zoom_out)

for c in string.ascii_lowercase:
    window.bind("" + c, canvas.key)

for i in range(10):
    window.bind(str(i), canvas.key)

window.mainloop()
