"""
Architectural Room Planner
Run: pip install pygame
     python Architectural_Room_Planner.py

Single-file Pygame application. Project files are saved with Python's pickle
format (no JSON or os module). Export Image saves only the drawing viewport.
"""

import math
import pickle
from pathlib import Path
import pygame

pygame.init()

# ------------------------------- Configuration ------------------------------
WIDTH, HEIGHT = 1440, 850
SIDEBAR_W = 195
HEADER_H = 74
TOOLBAR_H = 54
FOOTER_H = 34
FPS = 60
ROOM_W, ROOM_L = 8.0, 6.0

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Architectural Room Planner")
clock = pygame.time.Clock()

# Poppins is used when installed on the computer or supplied beside this script
# as Poppins-Regular.ttf / Poppins-Bold.ttf. Arial is a fallback only.
FONT_DIR = Path(__file__).resolve().parent
def load_ui_font(size, bold=False):
    candidates = (
        [FONT_DIR / "Poppins-Bold.ttf", FONT_DIR / "Poppins.ttf"]
        if bold else
        [FONT_DIR / "Poppins-Regular.ttf", FONT_DIR / "Poppins.ttf"]
    )
    for font_path in candidates:
        if font_path.exists():
            try:
                return pygame.font.Font(str(font_path), size)
            except pygame.error:
                pass
    match = pygame.font.match_font("poppins", bold=bold)
    if match:
        return pygame.font.Font(match, size)
    return pygame.font.SysFont("Arial", size, bold=bold)

FONT = load_ui_font(15)
SMALL = load_ui_font(12)
TINY = load_ui_font(10)
BOLD = load_ui_font(16, bold=True)
TITLE = load_ui_font(22, bold=True)

# Load logo.jpg beside the script for the app icon and header logo.
APP_LOGO = None
try:
    logo_path = FONT_DIR / "logo.jpg"
    if logo_path.exists():
        APP_LOGO = pygame.image.load(str(logo_path)).convert()
        pygame.display.set_icon(pygame.transform.smoothscale(APP_LOGO, (32, 32)))
except pygame.error:
    APP_LOGO = None

WHITE = (255, 255, 255)
INK = (35, 45, 60)
MUTED = (117, 132, 151)
BLUE = (43, 100, 245)
PALE_BLUE = (239, 245, 255)
BORDER = (218, 229, 243)
VIEW_BG = (219, 229, 240)
FLOOR = (250, 250, 251)
GRID = (222, 228, 235)
SELECT = (43, 100, 245)
RED = (235, 83, 100)
GREEN = (45, 160, 112)

FURNITURE = [
    {"name": "Sofa", "w": 2.0, "l": 0.9, "h": 0.8, "color": (189, 111, 135)},
    {"name": "Bed", "w": 2.0, "l": 1.6, "h": 0.45, "color": (193, 167, 135)},
    {"name": "Desk", "w": 1.4, "l": 0.7, "h": 0.75, "color": (154, 124, 95)},
    {"name": "Dining Table", "w": 1.5, "l": 0.9, "h": 0.75, "color": (174, 145, 111)},
    {"name": "Chair", "w": 0.5, "l": 0.5, "h": 0.85, "color": (104, 165, 143)},
    {"name": "Cabinet", "w": 0.9, "l": 0.45, "h": 1.7, "color": (132, 148, 174)},
    {"name": "Coffee Table", "w": 1.0, "l": 0.6, "h": 0.42, "color": (130, 151, 190)},
    {"name": "Wardrobe", "w": 1.2, "l": 0.6, "h": 2.0, "color": (161, 132, 108)},
    {"name": "Lamp", "w": 0.35, "l": 0.35, "h": 1.5, "color": (224, 190, 91)},
    {"name": "Plant", "w": 0.45, "l": 0.45, "h": 1.0, "color": (93, 157, 106)},
]


def default_items():
    # Objects are placed fully inside the room, with sofa and bed near corners.
    return [
        {"name": "Sofa", "x": 1.05, "y": 0.55, "w": 2.0, "l": 0.9, "angle": 0},
        {"name": "Bed", "x": 6.65, "y": 4.95, "w": 2.0, "l": 1.6, "angle": 0},
        {"name": "Desk", "x": 3.5, "y": 1.15, "w": 1.4, "l": 0.7, "angle": 0},
    ]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def text(surf, value, *args):
    """Draw text; accepts either (position, color, font) or (x, y, color, font)."""
    if not args:
        pos, color, font = (0, 0), INK, FONT
    elif isinstance(args[0], (tuple, list)):
        pos = args[0]
        color = args[1] if len(args) > 1 else INK
        font = args[2] if len(args) > 2 else FONT
    else:
        x = args[0]
        y = args[1] if len(args) > 1 else 0
        pos = (x, y)
        color = args[2] if len(args) > 2 else INK
        font = args[3] if len(args) > 3 else FONT
    surf.blit(font.render(str(value), True, color), pos)


def centered(surf, value, rect, color=INK, font=FONT):
    image = font.render(str(value), True, color)
    surf.blit(image, image.get_rect(center=rect.center))


def rounded(surf, rect, color, radius=7, border=None, width=1):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)


def furniture_def(name):
    return next((f for f in FURNITURE if f["name"] == name), FURNITURE[0])


class RoomPlanner:
    def __init__(self):
        self.items = default_items()
        self.mode = "2D"
        self.tab = "Workspace"
        self.selected = None
        self.dragging = False
        self.drag_offset = (0.0, 0.0)
        self.undo_stack = []
        self.redo_stack = []
        self.projects = {}
        self.project_name = "My Room"
        self.width_text = str(ROOM_W)
        self.length_text = str(ROOM_L)
        self.room_w, self.room_l = ROOM_W, ROOM_L
        self.zoom = 1.0
        self.grid_on = True
        self.rulers_on = True
        self.full_view = False
        self.status = "Ready"
        self.status_until = 0
        self.input_focus = None
        self.buttons = {}
        self.furniture_scroll = 0
        self.viewport = pygame.Rect(220, 150, 1000, 600)
        self.floor = pygame.Rect(400, 240, 700, 500)
        self.relayout()

    def status_msg(self, msg):
        self.status = msg
        self.status_until = pygame.time.get_ticks() + 2200

    def snapshot(self):
        return (pickle.dumps((self.items, self.room_w, self.room_l, self.mode)))

    def push_undo(self):
        self.undo_stack.append(self.snapshot())
        self.undo_stack = self.undo_stack[-80:]
        self.redo_stack.clear()

    def restore(self, data):
        self.items, self.room_w, self.room_l, self.mode = pickle.loads(data)
        self.width_text, self.length_text = str(self.room_w), str(self.room_l)
        self.selected = None
        self.keep_all_inside()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self.restore(self.undo_stack.pop())
            self.status_msg("Undo")
        else:
            self.status_msg("Nothing to undo")

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.snapshot())
            self.restore(self.redo_stack.pop())
            self.status_msg("Redo")
        else:
            self.status_msg("Nothing to redo")

    def relayout(self):
        sw, sh = screen.get_size()
        side = 0 if self.full_view else SIDEBAR_W
        self.viewport = pygame.Rect(side + 12, HEADER_H + TOOLBAR_H + 10,
                                    max(260, sw - side - 24),
                                    max(220, sh - HEADER_H - TOOLBAR_H - FOOTER_H - 25))
        # Zoom changes scale around viewport center; dimensions remain proportional.
        max_w = max(120, self.viewport.w - 120)
        max_h = max(120, self.viewport.h - 105)
        scale = min(max_w / self.room_w, max_h / self.room_l) * self.zoom
        fw, fh = int(self.room_w * scale), int(self.room_l * scale)
        fw, fh = min(fw, self.viewport.w * 3), min(fh, self.viewport.h * 3)
        self.floor = pygame.Rect(0, 0, fw, fh)
        self.floor.center = self.viewport.center

    def scale_x(self):
        return self.floor.w / self.room_w

    def scale_y(self):
        return self.floor.h / self.room_l

    def world_to_screen(self, x, y):
        return (self.floor.left + x * self.scale_x(),
                self.floor.top + y * self.scale_y())

    def screen_to_world(self, x, y):
        return ((x - self.floor.left) / max(1, self.scale_x()),
                (y - self.floor.top) / max(1, self.scale_y()))

    def item_points(self, item):
        cx, cy, w, l = item["x"], item["y"], item["w"], item["l"]
        a = math.radians(item["angle"])
        pts = []
        for dx, dy in [(-w/2,-l/2),(w/2,-l/2),(w/2,l/2),(-w/2,l/2)]:
            pts.append((cx + dx*math.cos(a) - dy*math.sin(a),
                        cy + dx*math.sin(a) + dy*math.cos(a)))
        return pts

    def screen_points(self, item):
        return [self.world_to_screen(x, y) for x, y in self.item_points(item)]

    def keep_inside(self, item):
        # Rotated rectangle extents, so furniture is allowed close to every corner.
        a = math.radians(item["angle"])
        ex = abs(math.cos(a))*item["w"]/2 + abs(math.sin(a))*item["l"]/2
        ey = abs(math.sin(a))*item["w"]/2 + abs(math.cos(a))*item["l"]/2
        item["x"] = clamp(item["x"], min(ex, self.room_w/2), max(self.room_w-ex, self.room_w/2))
        item["y"] = clamp(item["y"], min(ey, self.room_l/2), max(self.room_l-ey, self.room_l/2))

    def keep_all_inside(self):
        for item in self.items:
            self.keep_inside(item)

    def add_furniture(self, name):
        definition = furniture_def(name)
        self.push_undo()
        item = {"name": name, "x": self.room_w/2, "y": self.room_l/2,
                "w": definition["w"], "l": definition["l"], "angle": 0}
        self.items.append(item)
        self.selected = len(self.items)-1
        self.keep_inside(item)
        self.status_msg(f"Added {name}")

    def delete_selected(self):
        if self.selected is None:
            return
        self.push_undo()
        name = self.items.pop(self.selected)["name"]
        self.selected = None
        self.status_msg(f"Deleted {name}")

    def resize_selected(self, factor):
        if self.selected is None:
            return
        self.push_undo()
        item = self.items[self.selected]
        item["w"] = clamp(item["w"]*factor, .2, min(4, self.room_w))
        item["l"] = clamp(item["l"]*factor, .2, min(4, self.room_l))
        self.keep_inside(item)
        self.status_msg("Furniture resized")

    def rotate_selected(self, amount):
        if self.selected is None:
            return
        self.push_undo()
        item = self.items[self.selected]
        item["angle"] = (item["angle"] + amount) % 360
        self.keep_inside(item)
        self.status_msg("Furniture rotated")

    def reset_layout(self):
        self.push_undo()
        self.items = default_items()
        self.keep_all_inside()
        self.selected = None
        self.status_msg("Layout reset")

    def update_room(self):
        try:
            w, l = float(self.width_text), float(self.length_text)
            if not (1 <= w <= 50 and 1 <= l <= 50):
                raise ValueError
            self.push_undo()
            self.room_w, self.room_l = w, l
            self.keep_all_inside()
            self.status_msg(f"Room updated: {w:g} m × {l:g} m")
        except ValueError:
            self.status_msg("Enter valid dimensions between 1 and 50 m")

    def save_project(self):
        name = self.project_name.strip() or "Untitled Project"
        self.projects[name] = self.snapshot()
        self.status_msg(f"Saved project: {name}")

    def load_project(self, name):
        if name in self.projects:
            self.push_undo()
            self.restore(self.projects[name])
            self.project_name = name
            self.status_msg(f"Loaded project: {name}")

    def rename_project(self, old):
        if old not in self.projects:
            return
        new = self.project_name.strip()
        if not new:
            self.status_msg("Enter a new project name")
            return
        self.projects[new] = self.projects.pop(old)
        self.status_msg(f"Renamed project to {new}")

    def export_viewport(self):
        # Save only the viewport drawing, excluding header/sidebar/toolbars.
        self.relayout()
        target = pygame.Surface(self.viewport.size)
        target.fill(VIEW_BG)
        self.draw_view(target, offset=(-self.viewport.x, -self.viewport.y))
        try:
            pygame.image.save(target, "Architectural_Room_Planner_Viewport.png")
            self.status_msg("Exported viewport image")
        except pygame.error:
            self.status_msg("Could not export image")

    def hit_test(self, pos):
        for i in range(len(self.items)-1, -1, -1):
            if point_in_polygon(pos, self.screen_points(self.items[i])):
                return i
        return None

    def draw_header(self, surf):
        sw, _ = surf.get_size()
        pygame.draw.rect(surf, WHITE, (0, 0, sw, HEADER_H))
        title_x = 20
        if APP_LOGO is not None:
            logo = pygame.transform.smoothscale(APP_LOGO, (42, 42))
            surf.blit(logo, (18, 15))
            title_x = 70
        text(surf, "Architectural Room Planner", title_x, 11, INK, TITLE)
        text(surf, "Design, measure, and plan your room!", title_x, 43, MUTED, SMALL)
        # Right-side view controls
        x = sw - (12 + 3*54 + 8)
        self.buttons["mode2d"] = pygame.Rect(x, 16, 48, 34)
        self.buttons["mode3d"] = pygame.Rect(x+54, 16, 48, 34)
        self.buttons["full"] = pygame.Rect(x+108, 16, 90, 34)
        for key, label in [("mode2d","2D"),("mode3d","3D"),("full","Full View")]:
            r = self.buttons[key]
            active = (key == "mode2d" and self.mode == "2D") or (key == "mode3d" and self.mode == "3D") or (key == "full" and self.full_view)
            rounded(surf, r, BLUE if active else (247,249,252), 7, BORDER)
            centered(surf, label, r, WHITE if active else MUTED, SMALL)

    def draw_sidebar(self, surf):
        sw, sh = surf.get_size()
        if self.full_view:
            self.buttons["sidebar"] = pygame.Rect(0, 0, 0, 0)
            return
        pygame.draw.rect(surf, WHITE, (0, HEADER_H, SIDEBAR_W, sh-HEADER_H))
        pygame.draw.line(surf, BORDER, (SIDEBAR_W-1, HEADER_H), (SIDEBAR_W-1, sh), 1)
        text(surf, "ROOM PLANNER", 13, HEADER_H+15, MUTED, TINY)
        text(surf, "Workspace", 13, HEADER_H+35, INK, TITLE)
        tab_y = HEADER_H + 68
        for key, label, glyph in [("Workspace","Workspace","▤"),("Furniture","Furniture","▦")]:
            r = pygame.Rect(12 if key == "Workspace" else 104, tab_y, 82, 32)
            self.buttons["tab_"+key] = r
            rounded(surf, r, BLUE if self.tab == key else (247,249,252), 8, BORDER)
            icon_color = WHITE if self.tab == key else BLUE
            text(surf, glyph, r.x+7, r.y+8, icon_color, SMALL)
            # Keep the labels compact so the icons fit within each tab.
            text(surf, label, r.x+23, r.y+9, WHITE if self.tab == key else INK, TINY)

        y = tab_y + 48
        if self.tab == "Workspace":
            text(surf, "SAVED PROJECTS", 13, y, MUTED, TINY)
            y += 18
            r = pygame.Rect(12, y, SIDEBAR_W-24, 34)
            self.buttons["project_name"] = r
            rounded(surf, r, (250,251,253), 7, BORDER)
            shown = self.project_name if self.project_name else "Project name"
            text(surf, shown, (r.x+9, r.y+9), INK if self.project_name else MUTED, SMALL)
            y += 40
            self.buttons["save"] = pygame.Rect(12,y,SIDEBAR_W-24,32)
            rounded(surf,self.buttons["save"],BLUE,7)
            text(surf,"＋",self.buttons["save"].x+12,self.buttons["save"].y+7,WHITE,BOLD); text(surf,"Save Project",self.buttons["save"].x+34,self.buttons["save"].y+9,WHITE,SMALL)
            y += 38
            if not self.projects:
                text(surf, "Not saved yet", (13,y+4), MUTED, TINY)
                y += 26
            else:
                for name in list(self.projects.keys())[-4:]:
                    r = pygame.Rect(12,y,SIDEBAR_W-24,28)
                    self.buttons["project_"+name] = r
                    rounded(surf,r,(247,249,252),6,BORDER)
                    text(surf,name[:20],(r.x+7,r.y+7),INK,TINY)
                    # small rename action
                    rr = pygame.Rect(r.right-28,r.y+2,24,24)
                    self.buttons["rename_"+name] = rr
                    centered(surf,"✎",rr,BLUE,SMALL)
                    y += 32
            self.buttons["reset"] = pygame.Rect(12,y+5,SIDEBAR_W-24,32)
            rounded(surf,self.buttons["reset"],(255,241,243),7,(255,220,225))
            text(surf,"↺",self.buttons["reset"].x+12,self.buttons["reset"].y+7,RED,BOLD); text(surf,"Reset Layout",self.buttons["reset"].x+34,self.buttons["reset"].y+9,RED,SMALL)
            y += 54
            pygame.draw.line(surf,BORDER,(12,y),(SIDEBAR_W-12,y),1)
            y += 14
            text(surf,"ROOM DIMENSIONS",13,y,MUTED,TINY)
            y += 23
            text(surf,"Width (m)",13,y,MUTED,TINY)
            text(surf,"Length (m)",104,y,MUTED,TINY)
            y += 16
            self.buttons["width_input"] = pygame.Rect(12,y,81,34)
            self.buttons["length_input"] = pygame.Rect(101,y,82,34)
            for key, value in [("width_input",self.width_text),("length_input",self.length_text)]:
                r = self.buttons[key]
                rounded(surf,r,(250,251,253),7,BLUE if self.input_focus==key else BORDER)
                text(surf,value,(r.x+8,r.y+9),INK,SMALL)
            y += 40
            self.buttons["update_room"] = pygame.Rect(12,y,SIDEBAR_W-24,32)
            rounded(surf,self.buttons["update_room"],BLUE,7)
            text(surf,"✓",self.buttons["update_room"].x+18,self.buttons["update_room"].y+7,WHITE,SMALL); text(surf,"Update Room",self.buttons["update_room"].x+38,self.buttons["update_room"].y+9,WHITE,SMALL)
            y += 46
            text(surf,"Projects are kept for this session.",13,y,MUTED,TINY)
        else:
            text(surf,"FURNITURE LIBRARY",13,y,MUTED,TINY)
            y += 22
            text(surf,"Click an item to add it",13,y,MUTED,TINY)
            y += 18
            clip = surf.get_clip()
            surf.set_clip(pygame.Rect(0,y, SIDEBAR_W, sh-y-8))
            for idx, definition in enumerate(FURNITURE):
                iy = y + idx*49 - self.furniture_scroll
                r = pygame.Rect(12,iy,SIDEBAR_W-24,42)
                self.buttons["furn_"+definition["name"]] = r
                if iy+42 >= y and iy <= sh:
                    rounded(surf,r,(250,251,253),7,BORDER)
                    pygame.draw.rect(surf,definition["color"],(r.x+8,r.y+8,28,26),border_radius=5)
                    text(surf,definition["name"],(r.x+44,r.y+7),INK,SMALL)
                    text(surf,f'{definition["w"]:g} × {definition["l"]:g} m',(r.x+44,r.y+23),MUTED,TINY)
            surf.set_clip(clip)

    def draw_toolbar(self, surf):
        sw = surf.get_width()
        y = HEADER_H
        pygame.draw.rect(surf,(246,249,255),(0,y,sw,TOOLBAR_H))
        x0 = SIDEBAR_W + 12 if not self.full_view else 12
        controls = [
            ("zoom_out","−"),("zoom_in","+"),("grid","▦"),("rulers","Ruler"),
            ("undo","↶"),("redo","↷"),("export","↓ Export Image")
        ]
        x=x0
        for key,label in controls:
            w = 38 if key not in ("rulers","export") else (60 if key=="rulers" else 112)
            r=pygame.Rect(x,y+10,w,34)
            self.buttons[key]=r
            active=(key=="grid" and self.grid_on) or (key=="rulers" and self.rulers_on)
            rounded(surf,r,BLUE if active else WHITE,7,BORDER)
            centered(surf,label,r,WHITE if active else (BLUE if key in ("zoom_in","zoom_out","undo","redo","grid") else INK),SMALL)
            x += w+7
        # Current room dimensions on the far right
        text(surf,f"{self.room_w:g} m × {self.room_l:g} m", (max(x+8, sw-150), y+21), BLUE, SMALL)

    def draw_rulers(self, surf, ox=0, oy=0):
        if not self.rulers_on:
            return
        f = self.floor.move(ox,oy)
        vp = self.viewport.move(ox,oy)
        # X ruler along top; ticks are placed using exact world-to-pixel scale.
        pygame.draw.rect(surf,(248,250,253),(vp.left, vp.top-19, vp.width, 19))
        for m in range(int(math.floor(max(0, (vp.left-f.left)/max(1,self.scale_x())))), int(self.room_w)+1):
            x=f.left+m*self.scale_x()
            if vp.left <= x <= vp.right:
                pygame.draw.line(surf,MUTED,(int(x),vp.top-3),(int(x),vp.top+3),1)
                text(surf,str(m),(int(x)-3,vp.top-17),MUTED,TINY)
        # Y ruler on the left, values increase downwards in metres.
        pygame.draw.rect(surf,(248,250,253),(vp.left-19,vp.top,19,vp.height))
        for m in range(int(self.room_l)+1):
            y=f.top+m*self.scale_y()
            if vp.top <= y <= vp.bottom:
                pygame.draw.line(surf,MUTED,(vp.left-3,int(y)),(vp.left+3,int(y)),1)
                text(surf,str(m),(vp.left-15,int(y)-5),MUTED,TINY)

    def draw_2d(self, surf, ox=0, oy=0):
        f=self.floor.move(ox,oy)
        pygame.draw.rect(surf,VIEW_BG,self.viewport.move(ox,oy),border_radius=10)
        pygame.draw.rect(surf,FLOOR,f)
        if self.grid_on:
            for m in range(int(self.room_w)+1):
                x=f.left+m*self.scale_x()
                pygame.draw.line(surf,GRID,(int(x),f.top),(int(x),f.bottom),1)
            for m in range(int(self.room_l)+1):
                y=f.top+m*self.scale_y()
                pygame.draw.line(surf,GRID,(f.left,int(y)),(f.right,int(y)),1)
        pygame.draw.rect(surf,(204,213,224),f,1)
        # Door marker, near lower edge
        door_x=f.right-self.scale_x()*0.9
        pygame.draw.line(surf,FLOOR,(int(door_x),f.bottom),(int(door_x+self.scale_x(.7) if False else door_x+32),f.bottom),5)
        for i,item in enumerate(self.items):
            pts=[(int(x+ox),int(y+oy)) for x,y in self.screen_points(item)]
            color=furniture_def(item["name"])["color"]
            pygame.draw.polygon(surf,color,pts)
            pygame.draw.polygon(surf,SELECT if i==self.selected else (100,112,128),pts,3 if i==self.selected else 1)
            center=self.world_to_screen(item["x"],item["y"])
            center=(int(center[0]+ox),int(center[1]+oy))
            label=SMALL.render(item["name"],True,(40,47,57))
            surf.blit(label,label.get_rect(center=center))
        if self.selected is not None and self.selected < len(self.items):
            it=self.items[self.selected]
            label=f'W {it["w"]:.2f} m  ×  L {it["l"]:.2f} m'
            rounded(surf,pygame.Rect(self.viewport.centerx-52+ox,self.viewport.top+8+oy,104,24),WHITE,6,BORDER)
            centered(surf,label,pygame.Rect(self.viewport.centerx-52+ox,self.viewport.top+8+oy,104,24),INK,TINY)

    def draw_3d(self, surf, ox=0, oy=0):
        pygame.draw.rect(surf,VIEW_BG,self.viewport.move(ox,oy),border_radius=10)
        cx=self.viewport.centerx+ox
        top=self.viewport.top+75+oy
        floor_y=self.viewport.bottom-45+oy
        scale=min(self.viewport.w/(self.room_w+1),self.viewport.h/(self.room_l+2))*0.75*self.zoom
        room_w=self.room_w*scale
        room_l=self.room_l*scale*0.28
        back_y=top
        front_y=floor_y
        left=cx-room_w/2
        right=cx+room_w/2
        # One-point perspective room shell
        back_left=(int(cx-room_w*0.38),int(back_y+room_l*0.15))
        back_right=(int(cx+room_w*0.38),int(back_y+room_l*0.15))
        front_left=(int(left),int(front_y))
        front_right=(int(right),int(front_y))
        pygame.draw.polygon(surf,(244,247,251),[back_left,back_right,front_right,front_left])
        pygame.draw.polygon(surf,(231,237,245),[back_left,back_right,(back_right[0],back_right[1]-room_l),(back_left[0],back_left[1]-room_l)])
        for a,b in [(back_left,front_left),(back_right,front_right),(back_left,back_right),(front_left,front_right)]:
            pygame.draw.line(surf,(147,161,180),a,b,2)
        for i,item in enumerate(sorted(self.items,key=lambda q:q["y"])):
            px=left+(item["x"]/self.room_w)*room_w
            py=front_y-(item["y"]/self.room_l)*(front_y-back_y)*0.75
            iw=item["w"]*scale*0.62
            il=item["l"]*scale*0.3
            color=furniture_def(item["name"])["color"]
            p1=(int(px-iw/2),int(py-il/2))
            p2=(int(px+iw/2),int(py-il/2))
            p3=(int(px+iw/2),int(py+il/2))
            p4=(int(px-iw/2),int(py+il/2))
            rise=item.get("h",furniture_def(item["name"])["h"])*scale*0.3
            top_pts=[(p[0],int(p[1]-rise)) for p in (p1,p2,p3,p4)]
            pygame.draw.polygon(surf,color,[p1,p2,p3,p4])
            pygame.draw.polygon(surf,color,top_pts)
            for a,b in zip((p1,p2,p3,p4),top_pts):
                pygame.draw.line(surf,color,a,b,2)
            pygame.draw.lines(surf,SELECT if self.items.index(item)==self.selected else (110,119,133),True,top_pts,2)
            label=SMALL.render(item["name"],True,INK)
            surf.blit(label,label.get_rect(center=(int(px),int(py+8))))

    def draw_view(self, surf, offset=(0,0)):
        ox,oy=offset
        if self.mode=="2D":
            self.draw_2d(surf,ox,oy)
            self.draw_rulers(surf,ox,oy)
        else:
            pygame.draw.rect(surf,VIEW_BG,self.viewport.move(ox,oy),border_radius=10)
            self.draw_3d(surf,ox,oy)

    def draw_footer(self, surf):
        sw,sh=surf.get_size()
        y=sh-FOOTER_H
        pygame.draw.rect(surf,WHITE,(0,y,sw,FOOTER_H))
        text(surf,f"Room X: {self.room_w:.2f} m",(12,y+10),MUTED,TINY)
        text(surf,f"Room Y: {self.room_l:.2f} m",(118,y+10),MUTED,TINY)
        selected="None"
        if self.selected is not None and self.selected<len(self.items):
            selected=self.items[self.selected]["name"]
        text(surf,f"SELECTED OBJECT: {selected}",(max(12,sw-185),y+10),BLUE,TINY)
        if pygame.time.get_ticks()<self.status_until:
            image=SMALL.render(self.status,True,GREEN)
            surf.blit(image,(max(12,sw//2-image.get_width()//2),y+8))

    def draw(self):
        self.relayout()
        screen.fill(WHITE)
        self.draw_header(screen)
        self.draw_toolbar(screen)
        self.draw_sidebar(screen)
        self.draw_view(screen)
        self.draw_footer(screen)
        pygame.display.flip()

    def handle_click(self,pos):
        # Header
        for key in ("mode2d","mode3d","full"):
            if self.buttons.get(key,pygame.Rect(0,0,0,0)).collidepoint(pos):
                if key=="mode2d":
                    self.mode="2D"
                elif key=="mode3d":
                    self.mode="3D"
                else:
                    self.full_view=not self.full_view
                return
        # Toolbar
        for key in ("zoom_out","zoom_in","grid","rulers","undo","redo","export"):
            if self.buttons.get(key,pygame.Rect(0,0,0,0)).collidepoint(pos):
                if key=="zoom_out":
                    self.zoom=clamp(self.zoom/1.15,.4,2.5)
                elif key=="zoom_in":
                    self.zoom=clamp(self.zoom*1.15,.4,2.5)
                elif key=="grid":
                    self.grid_on=not self.grid_on
                elif key=="rulers":
                    self.rulers_on=not self.rulers_on
                elif key=="undo":
                    self.undo()
                elif key=="redo":
                    self.redo()
                elif key=="export":
                    self.export_viewport()
                return
        # Sidebar tabs
        for tab in ("Workspace","Furniture"):
            if self.buttons.get("tab_"+tab,pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.tab=tab
                return
        if self.full_view:
            return
        if self.tab=="Workspace":
            if self.buttons.get("project_name",pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.input_focus="project_name"; return
            if self.buttons.get("width_input",pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.input_focus="width_input"; return
            if self.buttons.get("length_input",pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.input_focus="length_input"; return
            if self.buttons.get("save",pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.save_project(); return
            if self.buttons.get("reset",pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.reset_layout(); return
            if self.buttons.get("update_room",pygame.Rect(0,0,0,0)).collidepoint(pos):
                self.update_room(); return
            for name in list(self.projects):
                if self.buttons.get("project_"+name,pygame.Rect(0,0,0,0)).collidepoint(pos):
                    self.load_project(name); return
                if self.buttons.get("rename_"+name,pygame.Rect(0,0,0,0)).collidepoint(pos):
                    self.rename_project(name); return
        else:
            for definition in FURNITURE:
                if self.buttons.get("furn_"+definition["name"],pygame.Rect(0,0,0,0)).collidepoint(pos):
                    self.add_furniture(definition["name"]); return

        # Furniture viewport interaction
        if self.viewport.collidepoint(pos) and self.mode=="2D":
            index=self.hit_test(pos)
            if index is not None:
                self.selected=index
                self.dragging=True
                self.push_undo()
                wx,wy=self.screen_to_world(*pos)
                item=self.items[index]
                self.drag_offset=(item["x"]-wx,item["y"]-wy)
            else:
                self.selected=None

    def handle_event(self,event):
        if event.type==pygame.VIDEORESIZE:
            return
        if event.type==pygame.MOUSEWHEEL:
            if self.viewport.collidepoint(pygame.mouse.get_pos()):
                self.zoom=clamp(self.zoom*(1.1 if event.y>0 else 1/1.1),.4,2.5)
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            self.handle_click(event.pos)
        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            self.dragging=False
        elif event.type==pygame.MOUSEMOTION and self.dragging and self.selected is not None and self.mode=="2D":
            wx,wy=self.screen_to_world(*event.pos)
            item=self.items[self.selected]
            item["x"],item["y"]=wx+self.drag_offset[0],wy+self.drag_offset[1]
            self.keep_inside(item)
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button in (4,5):
            if self.viewport.collidepoint(event.pos):
                self.zoom=clamp(self.zoom*(1.1 if event.button==4 else 1/1.1),.4,2.5)
        elif event.type==pygame.KEYDOWN:
            if self.input_focus:
                if event.key==pygame.K_RETURN:
                    self.input_focus=None
                    return
                if event.key==pygame.K_ESCAPE:
                    self.input_focus=None
                    return
                if event.key==pygame.K_BACKSPACE:
                    if self.input_focus=="project_name":
                        self.project_name=self.project_name[:-1]
                    elif self.input_focus=="width_input":
                        self.width_text=self.width_text[:-1]
                    elif self.input_focus=="length_input":
                        self.length_text=self.length_text[:-1]
                    return
                if event.unicode and event.unicode.isprintable():
                    if self.input_focus=="project_name" and len(self.project_name)<32:
                        self.project_name+=event.unicode
                    elif self.input_focus in ("width_input","length_input") and event.unicode in "0123456789.":
                        if self.input_focus=="width_input":
                            self.width_text+=event.unicode
                        else:
                            self.length_text+=event.unicode
                return
            mods=pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL and event.key==pygame.K_z:
                self.undo()
            elif mods & pygame.KMOD_CTRL and event.key==pygame.K_y:
                self.redo()
            elif event.key==pygame.K_DELETE or event.key==pygame.K_BACKSPACE:
                self.delete_selected()
            elif event.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS):
                self.resize_selected(1.1)
            elif event.key in (pygame.K_MINUS,pygame.K_KP_MINUS):
                self.resize_selected(1/1.1)
            elif event.key==pygame.K_q:
                self.rotate_selected(-15)
            elif event.key==pygame.K_e:
                self.rotate_selected(15)
            elif event.key==pygame.K_TAB:
                self.mode="3D" if self.mode=="2D" else "2D"
            elif event.key==pygame.K_ESCAPE:
                self.input_focus=None
            elif event.key==pygame.K_x:
                self.delete_selected()
            elif event.key==pygame.K_r:
                self.reset_layout()
            elif event.key==pygame.K_a:
                self.add_furniture("Sofa")


def point_in_polygon(point, polygon):
    x,y=point
    inside=False
    j=len(polygon)-1
    for i in range(len(polygon)):
        xi,yi=polygon[i]; xj,yj=polygon[j]
        if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/((yj-yi) or 1e-9)+xi:
            inside=not inside
        j=i
    return inside


def main():
    app=RoomPlanner()
    running=True
    while running:
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                running=False
            else:
                app.handle_event(event)
        app.draw()
        clock.tick(FPS)
    pygame.quit()


if __name__=="__main__":
    main()
