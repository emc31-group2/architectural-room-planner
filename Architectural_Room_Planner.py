"""
Architectural Room Planner
Run: pip install pygame
     python Architectural_Room_Planner.py

Single-file Pygame application. Saved project snapshots are kept in memory for this session.
Export saves only the drawing viewport.
"""

import math
import pickle
from datetime import datetime
from pathlib import Path
import pygame

# Start Pygame before creating fonts, surfaces, or the window.
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

# Poppins is used when installed or supplied beside this script. The system
# default font is used if Poppins cannot be found.
FONT_DIR = Path(__file__).resolve().parent
# Load the requested font, with safe fallbacks if Poppins is unavailable.
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
    return pygame.font.Font(None, size)

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

# Darken a color by subtracting the same amount from each channel.
def shade(color, amount=35):
    return tuple(max(0, channel - amount) for channel in color)

# Furniture catalog: dimensions are in meters; wall_only items attach to a wall.
FURNITURE = [
    {"name": "Single Bed", "w": 1.0, "l": 2.0, "h": 0.45, "color": (193, 167, 135)},
    {"name": "Double Bed", "w": 1.8, "l": 2.0, "h": 0.48, "color": (193, 167, 135)},
    {"name": "Bunk Bed", "w": 1.0, "l": 2.0, "h": 1.8, "color": (174, 145, 111)},
    {"name": "Sofa", "w": 2.0, "l": 0.9, "h": 0.8, "color": (189, 111, 135)},
    {"name": "Table", "w": 1.2, "l": 0.7, "h": 0.75, "color": (174, 145, 111)},
    {"name": "Chair", "w": 0.5, "l": 0.5, "h": 0.85, "color": (104, 165, 143)},
    {"name": "Lamp", "w": 0.35, "l": 0.35, "h": 1.5, "color": (224, 190, 91)},
    {"name": "Big Cabinet", "w": 1.4, "l": 0.55, "h": 2.0, "color": (132, 148, 174)},
    {"name": "Small Cabinet", "w": 0.75, "l": 0.45, "h": 1.0, "color": (151, 166, 187)},
    {"name": "Round Table", "w": 1.1, "l": 1.1, "h": 0.75, "color": (174, 145, 111)},
    {"name": "Big Table", "w": 2.0, "l": 1.0, "h": 0.75, "color": (174, 145, 111)},
    {"name": "Small Table", "w": 0.75, "l": 0.55, "h": 0.48, "color": (130, 151, 190)},
    {"name": "Window", "w": 1.2, "l": 0.12, "h": 1.2, "color": (99, 178, 218), "wall_only": True},
    {"name": "Door", "w": 0.9, "l": 0.12, "h": 2.1, "color": (160, 111, 75), "wall_only": True},
    {"name": "TV", "w": 1.2, "l": 0.16, "h": 0.7, "color": (75, 88, 105), "wall_only": True},
]


# Return the initial furniture list; the room starts empty.
def default_items():
    # Start with an empty room; users add furniture from the Library.
    return []


# Keep a number between a minimum and maximum value.
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# Draw text on a surface using the requested position, color, and font.
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


# Draw text centered inside a rectangle.
def centered(surf, value, rect, color=INK, font=FONT):
    image = font.render(str(value), True, color)
    surf.blit(image, image.get_rect(center=rect.center))


# Draw a rounded rectangle and an optional border.
def rounded(surf, rect, color, radius=7, border=None, width=1):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)


# Find the settings for a furniture type, or use the first type as fallback.
def furniture_def(name):
    return next((f for f in FURNITURE if f["name"] == name), FURNITURE[0])


# Main application class: stores the room state and draws/handles the interface.
class RoomPlanner:
    # Set up the room, interface state, furniture, and controls.
    def __init__(self):
        self.items = default_items()
        self.mode = "2D"
        self.tab = "Workspace"
        self.selected = None
        self.dragging = False
        self.drag_offset = (0.0, 0.0)
        self.rotating_view = False
        self.last_mouse_pos = None
        self.camera_yaw = -0.65
        self.camera_pitch = 0.55
        self.undo_stack = []
        self.redo_stack = []
        self.projects = {}
        self.project_timestamps = {}
        self.last_saved = None
        self.project_name = "Project Name"
        self.width_text = str(ROOM_W)
        self.length_text = str(ROOM_L)
        self.room_w, self.room_l = ROOM_W, ROOM_L
        self.zoom = 1.0
        self.grid_on = True
        self.rulers_on = True
        self.color_mode = "colored"  # Colored appearance is enabled by default.
        self.full_view = False
        self.controls_open = False
        self.status = "Ready"
        self.status_until = 0
        self.input_focus = None
        self.buttons = {}
        self.furniture_scroll = 0
        self.viewport = pygame.Rect(220, 150, 1000, 600)
        self.floor = pygame.Rect(400, 240, 700, 500)
        self.relayout()

    # Show a short status message at the bottom of the app.
    def status_msg(self, msg):
        self.status = msg
        self.status_until = pygame.time.get_ticks() + 2200

    # Return the normal or grayscale version of a furniture color.
    def display_color(self, color):
        """Return furniture colors in the active grayscale/colored display mode."""
        if self.color_mode == "colored":
            return color
        gray = round(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])
        return (gray, gray, gray)

    # Pack the current layout into data for undo and redo.
    def snapshot(self):
        return (pickle.dumps((self.items, self.room_w, self.room_l, self.mode)))

    # Save the current layout before making a change.
    def push_undo(self):
        self.undo_stack.append(self.snapshot())
        self.undo_stack = self.undo_stack[-80:]
        self.redo_stack.clear()

    # Restore a saved layout and keep furniture within the room.
    def restore(self, data):
        self.items, self.room_w, self.room_l, self.mode = pickle.loads(data)
        self.width_text, self.length_text = str(self.room_w), str(self.room_l)
        self.selected = None
        self.keep_all_inside()

    # Return to the previous layout, if one is available.
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self.restore(self.undo_stack.pop())
            self.status_msg("Undo")
        else:
            self.status_msg("Nothing to undo")

    # Reapply a layout that was undone, if available.
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.snapshot())
            self.restore(self.redo_stack.pop())
            self.status_msg("Redo")
        else:
            self.status_msg("Nothing to redo")

    # Recalculate the viewport and room size after window/layout changes.
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

    # Get the horizontal screen scale for one room meter.
    def scale_x(self):
        return self.floor.w / self.room_w

    # Get the vertical screen scale for one room meter.
    def scale_y(self):
        return self.floor.h / self.room_l

    # Convert room coordinates in meters into screen coordinates.
    def world_to_screen(self, x, y):
        return (self.floor.left + x * self.scale_x(),
                self.floor.top + y * self.scale_y())

    # Convert screen coordinates into room coordinates in meters.
    def screen_to_world(self, x, y):
        return ((x - self.floor.left) / max(1, self.scale_x()),
                (y - self.floor.top) / max(1, self.scale_y()))

    # Calculate the rotated corners of a furniture item in the room.
    def item_points(self, item):
        cx, cy, w, l = item["x"], item["y"], item["w"], item["l"]
        a = math.radians(item["angle"])
        pts = []
        for dx, dy in [(-w/2,-l/2),(w/2,-l/2),(w/2,l/2),(-w/2,l/2)]:
            pts.append((cx + dx*math.cos(a) - dy*math.sin(a),
                        cy + dx*math.sin(a) + dy*math.cos(a)))
        return pts

    # Convert a furniture item’s room corners into screen positions.
    def screen_points(self, item):
        return [self.world_to_screen(x, y) for x, y in self.item_points(item)]

    # Keep furniture inside the room while respecting wall clearance.
    def keep_inside(self, item):
        # Doors and windows are constrained to a wall, never free-standing.
        if furniture_def(item["name"]).get("wall_only"):
            wall = item.get("wall", "top")
            if wall in ("top", "bottom"):
                item["x"] = clamp(item["x"], item["w"] / 2, self.room_w - item["w"] / 2)
                item["y"] = 0 if wall == "top" else self.room_l
                item["angle"] = 0
            else:
                item["y"] = clamp(item["y"], item["w"] / 2, self.room_l - item["w"] / 2)
                item["x"] = 0 if wall == "left" else self.room_w
                item["angle"] = 90
            return
        # Keep a 0.3 m clearance between furniture and every room wall.
        a = math.radians(item["angle"])
        ex = abs(math.cos(a))*item["w"]/2 + abs(math.sin(a))*item["l"]/2
        ey = abs(math.sin(a))*item["w"]/2 + abs(math.cos(a))*item["l"]/2
        margin = 0.3
        min_x, max_x = margin + ex, self.room_w - margin - ex
        min_y, max_y = margin + ey, self.room_l - margin - ey
        item["x"] = clamp(item["x"], min(min_x, self.room_w / 2), max(max_x, self.room_w / 2))
        item["y"] = clamp(item["y"], min(min_y, self.room_l / 2), max(max_y, self.room_l / 2))

    # Align a furniture item to the chosen grid spacing.
    def snap_item_to_grid(self, item, step=0.25):
        """Snap a furniture center to a quarter-metre grid."""
        item["x"] = round(item["x"] / step) * step
        item["y"] = round(item["y"] / step) * step
        self.keep_inside(item)

    # Keep doors, windows, and TVs attached to a room wall.
    def update_wall_attachment(self, item):
        """Attach doors/windows to whichever room wall is nearest."""
        if not furniture_def(item["name"]).get("wall_only"):
            return
        x, y = item["x"], item["y"]
        distances = [(abs(y), "top"), (abs(self.room_l-y), "bottom"),
                     (abs(x), "left"), (abs(self.room_w-x), "right")]
        item["wall"] = min(distances, key=lambda pair: pair[0])[1]
        self.keep_inside(item)

    # Check every furniture item and correct its position if needed.
    def keep_all_inside(self):
        for item in self.items:
            self.keep_inside(item)

    # Create a new furniture item and place it in the room.
    def add_furniture(self, name):
        definition = furniture_def(name)
        self.push_undo()
        item = {"name": name, "x": self.room_w/2, "y": self.room_l/2,
                "w": definition["w"], "l": definition["l"], "angle": 0}
        if definition.get("wall_only"):
            item["wall"] = "top"
            item["x"], item["y"] = self.room_w / 2, 0
            item["angle"] = 0
        self.items.append(item)
        self.selected = len(self.items)-1
        self.keep_inside(item)
        self.status_msg(f"Added {name}")

    # Remove the currently selected furniture item.
    def delete_selected(self):
        if self.selected is None:
            return
        self.push_undo()
        name = self.items.pop(self.selected)["name"]
        self.selected = None
        self.status_msg(f"Deleted {name}")

    # Change the selected item’s width and length.
    def resize_selected(self, factor):
        if self.selected is None:
            return
        self.push_undo()
        item = self.items[self.selected]
        item["w"] = clamp(item["w"]*factor, .2, min(4, self.room_w if item.get("wall", "top") in ("top", "bottom") else self.room_l))
        if not furniture_def(item["name"]).get("wall_only"):
            item["l"] = clamp(item["l"]*factor, .2, min(4, self.room_l))
        self.keep_inside(item)
        self.status_msg("Furniture resized")

    # Rotate the selected item or move a wall fixture to another wall.
    def rotate_selected(self, amount):
        if self.selected is None:
            return
        self.push_undo()
        item = self.items[self.selected]
        if furniture_def(item["name"]).get("wall_only"):
            walls = ["top", "right", "bottom", "left"]
            current = item.get("wall", "top")
            item["wall"] = walls[(walls.index(current) + (1 if amount > 0 else -1)) % len(walls)]
            self.keep_inside(item)
        else:
            item["angle"] = (item["angle"] + amount) % 360
            self.keep_inside(item)
        self.status_msg("Furniture rotated")

    # Clear the room and return the planner to its default layout state.
    def reset_layout(self):
        self.push_undo()
        self.items = []
        self.selected = None
        self.status_msg("Layout cleared")

    # Read the room width and length fields and apply valid dimensions.
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

    # Save a named snapshot of the current room layout.
    def save_project(self):
        # Allow only three saved layouts; existing names can still be updated.
        name = self.project_name.strip() or "Untitled Project"
        if name not in self.projects and len(self.projects) >= 3:
            self.status_msg("All 3 save slots are full. Delete a saved layout first.")
            return

        self.projects[name] = self.snapshot()
        self.last_saved = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p").replace(", 0", ", ", 1)
        self.project_timestamps[name] = self.last_saved
        self.status_msg(f"Saved project: {name}")

    # Load one of the saved project snapshots.
    def load_project(self, name):
        if name in self.projects:
            self.push_undo()
            self.restore(self.projects[name])
            self.project_name = name
            self.status_msg(f"Loaded project: {name}")

    # Rename a saved project.
    def rename_project(self, old):
        if old not in self.projects:
            return
        new = self.project_name.strip()
        if not new:
            self.status_msg("Enter a new project name")
            return
        self.projects[new] = self.projects.pop(old)
        self.status_msg(f"Renamed project to {new}")

    # Export an image of the room viewport.
    def export_viewport(self):
        # Save only the viewport drawing, excluding header/sidebar/toolbars.
        self.relayout()
        target = pygame.Surface(self.viewport.size, pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        self.draw_view(target, offset=(-self.viewport.x, -self.viewport.y))
        # Keep the exported viewport image rounded at the corners.
        mask = pygame.Surface(self.viewport.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=12)
        target.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        try:
            pygame.image.save(target, "Architectural_Room_Planner_Viewport.png")
            self.status_msg("Exported viewport image")
        except pygame.error:
            self.status_msg("Could not export image")

    # Move an item to the top drawing layer so it stays in front.
    def bring_to_front(self, index):
        """Move the chosen object to the end of the draw list so it renders on top."""
        if index is None or not (0 <= index < len(self.items)):
            self.selected = None
            return
        chosen = self.items.pop(index)
        self.items.append(chosen)
        self.selected = len(self.items) - 1

    # Find which visible 2D furniture item is under the mouse.
    def hit_test(self, pos):
        px, py = pos
        for i in range(len(self.items)-1, -1, -1):
            item = self.items[i]
            if item["name"] == "Round Table":
                cx, cy = self.world_to_screen(item["x"], item["y"])
                rx = max(8, item["w"] * self.scale_x() / 2)
                ry = max(8, item["w"] * self.scale_y() / 2)
                if ((px-cx)/rx)**2 + ((py-cy)/ry)**2 <= 1.0:
                    return i
                continue
            if furniture_def(item["name"]).get("wall_only"):
                cx, cy = self.world_to_screen(item["x"], item["y"])
                length = item["w"] * (self.scale_x() if item.get("wall", "top") in ("top", "bottom") else self.scale_y())
                if item.get("wall", "top") in ("top", "bottom"):
                    rect = pygame.Rect(int(cx-length/2-8), int(cy-12), int(length+16), 24)
                else:
                    rect = pygame.Rect(int(cx-12), int(cy-length/2-8), 24, int(length+16))
                if rect.collidepoint(pos):
                    return i
            if point_in_polygon(pos, self.screen_points(item)):
                return i
        return None

    # Draw the top bar with the project title and view controls.
    def draw_header(self, surf):
        sw, _ = surf.get_size()
        pygame.draw.rect(surf, WHITE, (0, 0, sw, HEADER_H))
        title_x = 20
        if APP_LOGO is not None:
            logo = pygame.transform.smoothscale(APP_LOGO, (42, 42))
            # Clip the logo to a rounded rectangle so its corners are soft.
            logo_mask = pygame.Surface((42, 42), pygame.SRCALPHA)
            pygame.draw.rect(logo_mask, (255, 255, 255, 255), (0, 0, 42, 42), border_radius=9)
            logo = logo.convert_alpha()
            logo.blit(logo_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(logo, (18, 15))
            title_x = 70
        text(surf, "Architectural Room Planner", title_x, 11, INK, TITLE)
        text(surf, "Design, measure, and plan your room!", title_x, 43, MUTED, SMALL)
        # Right-side view controls (Full button removed).
        button_total = 48 + 6 + 48
        x = max(title_x + 270, sw - button_total - 18)
        x = min(x, max(8, sw - button_total - 8))
        self.buttons["mode2d"] = pygame.Rect(x, 16, 48, 34)
        self.buttons["mode3d"] = pygame.Rect(x+54, 16, 48, 34)
        for key, label in [("mode2d", "2D"), ("mode3d", "3D")]:
            r = self.buttons[key]
            active = (key == "mode2d" and self.mode == "2D") or (key == "mode3d" and self.mode == "3D")
            rounded(surf, r, BLUE if active else (247,249,252), 7, BORDER)
            centered(surf, label, r, WHITE if active else MUTED, SMALL)

    # Draw the Workspace/Furniture sidebar and saved projects/library.
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
        for key, label in [("Workspace", "Workspace"), ("Furniture", "Furniture")]:
            r = pygame.Rect(12 if key == "Workspace" else 104, tab_y, 82, 32)
            self.buttons["tab_"+key] = r
            rounded(surf, r, BLUE if self.tab == key else (247,249,252), 8, BORDER)
            centered(surf, label, r, WHITE if self.tab == key else INK, TINY)

        y = tab_y + 48
        if self.tab == "Workspace":
            text(surf, "SAVED PROJECTS", 13, y, MUTED, TINY)
            y += 18
            r = pygame.Rect(12, y, SIDEBAR_W-24, 34)
            self.buttons["project_name"] = r
            rounded(surf, r, (250,251,253), 7, BORDER)
            shown = self.project_name if self.project_name else "Project Name"
            text(surf, shown, (r.x+9, r.y+9), INK if self.project_name else MUTED, SMALL)
            y += 40
            self.buttons["save"] = pygame.Rect(12,y,SIDEBAR_W-24,32)
            rounded(surf,self.buttons["save"],BLUE,7)
            centered(surf, "Save Project", self.buttons["save"], WHITE, SMALL)
            y += 38
            if not self.projects:
                text(surf, "Not saved yet", (13,y+4), MUTED, TINY)
                y += 26
            else:
                for name in list(self.projects.keys())[-3:]:
                    y += 5  # breathing room above each saved project name
                    name_rect = pygame.Rect(12, y, SIDEBAR_W-24, 18)
                    self.buttons["project_"+name] = name_rect
                    text(surf, name[:24], (name_rect.x+1, name_rect.y+1), INK, TINY)
                    y += 17
                    text(surf, "Last saved:", (13, y), MUTED, TINY)
                    y += 12
                    saved_value = self.project_timestamps.get(name, "Not available")
                    text(surf, saved_value, (13, y), MUTED, TINY)
                    y += 19  # a little gap after the timestamp before the buttons
                    open_rect = pygame.Rect(12, y, 76, 24)
                    delete_rect = pygame.Rect(94, y, 89, 24)
                    self.buttons["project_open_"+name] = open_rect
                    self.buttons["project_delete_"+name] = delete_rect
                    rounded(surf, open_rect, (231,241,255), 5, (201,220,255))
                    centered(surf, "Open", open_rect, BLUE, TINY)
                    rounded(surf, delete_rect, (255,239,241), 5, (255,220,225))
                    centered(surf, "Delete", delete_rect, RED, TINY)
                    y += 31
            self.buttons["reset"] = pygame.Rect(12,y+5,SIDEBAR_W-24,32)
            rounded(surf,self.buttons["reset"],(255,241,243),7,(255,220,225))
            centered(surf, "Reset Layout", self.buttons["reset"], RED, SMALL)
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
            centered(surf, "Update Room", self.buttons["update_room"], WHITE, SMALL)
            y += 46
        else:
            text(surf,"LIBRARY",13,y,MUTED,TINY)
            y += 22
            y += 8
            clip = surf.get_clip()
            list_bottom = sh - FOOTER_H - 14
            list_rect = pygame.Rect(0, y, SIDEBAR_W, max(1, list_bottom-y))
            surf.set_clip(list_rect)
            row_step = 49
            content_height = len(FURNITURE) * row_step + 22  # extra gap below final item
            max_scroll = max(0, content_height - list_rect.height)
            self.furniture_scroll = clamp(self.furniture_scroll, 0, max_scroll)
            for idx, definition in enumerate(FURNITURE):
                iy = y + idx*row_step - self.furniture_scroll
                r = pygame.Rect(12,iy,SIDEBAR_W-24,42)
                self.buttons["furn_"+definition["name"]] = r
                if iy+42 >= list_rect.top and iy <= list_rect.bottom:
                    rounded(surf,r,(250,251,253),7,BORDER)
                    pygame.draw.rect(surf,self.display_color(definition["color"]),(r.x+8,r.y+8,28,26),border_radius=5)
                    text(surf,definition["name"],(r.x+44,r.y+7),INK,SMALL)
                    text(surf,f'{definition["w"]:g} × {definition["l"]:g} m',(r.x+44,r.y+23),MUTED,TINY)
            surf.set_clip(clip)

    # Draw the room tools, view options, and appearance controls.
    def draw_toolbar(self, surf):
        sw = surf.get_width()
        y = HEADER_H
        pygame.draw.rect(surf, (246, 249, 255), (0, y, sw, TOOLBAR_H))
        left = SIDEBAR_W + 12 if not self.full_view else 12
        controls = [("grid", "Grid", 58), ("rulers", "Ruler", 62),
                    ("grayscale", "Grayscale", 86), ("colored", "Colored", 76)]
        for index, (key, label, width) in enumerate(controls):
            # The separator is a visual divider, not a button.
            if index == 2:
                # Subtle, fixed divider between view tools and color mode controls.
                pygame.draw.line(surf, (190, 190, 190), (left+1, y+13), (left+1, y+41), 1)
                left += 12
            rect = pygame.Rect(left, y + 10, width, 34)
            self.buttons[key] = rect
            if key == "grid":
                active = self.grid_on
            elif key == "rulers":
                active = self.rulers_on
            else:
                active = self.color_mode == key
            rounded(surf, rect, BLUE if active else WHITE, 7, BORDER)
            centered(surf, label, rect, WHITE if active else INK, SMALL)
            left += width + 7
        help_rect = pygame.Rect(sw - 88, y + 10, 76, 34)
        export_rect = pygame.Rect(sw - 166, y + 10, 70, 34)
        self.buttons["help"] = help_rect
        self.buttons["export"] = export_rect
        rounded(surf, export_rect, WHITE, 7, BORDER)
        centered(surf, "Export", export_rect, INK, SMALL)
        rounded(surf, help_rect, BLUE, 7, BLUE)
        centered(surf, "Controls", help_rect, WHITE, SMALL)

    # Draw room measurement marks around the viewport.
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

    # Draw the room and furniture from a flat top-down view.
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
        for i, item in enumerate(self.items):
            definition = furniture_def(item["name"])
            color = self.display_color(definition["color"])
            selected_color = SELECT if i == self.selected else (100, 112, 128)
            center = self.world_to_screen(item["x"], item["y"])
            center = (int(center[0] + ox), int(center[1] + oy))
            if definition.get("wall_only"):
                # Door/window are drawn as wall-mounted symbols and can only sit on a wall.
                horizontal_wall = item.get("wall", "top") in ("top", "bottom")
                along = item["w"] * (self.scale_x() if horizontal_wall else self.scale_y())
                if item["name"] == "Door":
                    thickness = 15
                elif item["name"] == "TV":
                    thickness = 17
                else:
                    thickness = 12
                if horizontal_wall:
                    rect = pygame.Rect(round(center[0]-along/2), round(center[1]-thickness/2), max(10,round(along)), thickness)
                else:
                    rect = pygame.Rect(round(center[0]-thickness/2), round(center[1]-along/2), thickness, max(10,round(along)))
                pygame.draw.rect(surf, FLOOR, rect.inflate(4,4))
                # Door and window are plain solid rectangles; wall orientation
                # determines whether the rectangle lies horizontally or vertically.
                pygame.draw.rect(surf, color, rect)
                pygame.draw.rect(surf, selected_color, rect, 2)
            else:
                pts=[(int(x+ox),int(y+oy)) for x,y in self.screen_points(item)]
                # Keep furniture as simple geometric shapes with no decorative marks.
                if item["name"] == "Round Table":
                    radius_x = max(5, int(item["w"] * self.scale_x() / 2))
                    radius_y = max(5, int(item["w"] * self.scale_y() / 2))
                    circle_rect = pygame.Rect(center[0]-radius_x, center[1]-radius_y, radius_x*2, radius_y*2)
                    pygame.draw.ellipse(surf, color, circle_rect)
                    pygame.draw.ellipse(surf, selected_color, circle_rect, 3 if i == self.selected else 1)
                else:
                    pygame.draw.polygon(surf, color, pts)
                    pygame.draw.polygon(surf, selected_color, pts, 3 if i == self.selected else 1)
            label=SMALL.render(item["name"],True,(40,47,57))
            surf.blit(label,label.get_rect(center=center))
        if self.selected is not None and self.selected < len(self.items):
            it=self.items[self.selected]
            label=f'W {it["w"]:.2f} m  ×  L {it["l"]:.2f} m'
            rounded(surf,pygame.Rect(self.viewport.centerx-52+ox,self.viewport.top+8+oy,104,24),WHITE,6,BORDER)
            centered(surf,label,pygame.Rect(self.viewport.centerx-52+ox,self.viewport.top+8+oy,104,24),INK,TINY)

    # Return the current camera projection settings for the 3D view.
    def projection_3d(self):
        """Return the shared 3D projection parameters used for drawing and picking."""
        scale = min(self.viewport.w / (self.room_w + self.room_l * 0.95),
                    self.viewport.h / (self.room_w * 0.34 + self.room_l * 0.34 + 2.8)) * 0.82
        return scale, self.camera_yaw, max(0.22, min(0.8, self.camera_pitch))

    # Convert a 3D room point into a 2D screen position.
    def project_3d(self, x, y, z=0, ox=0, oy=0):
        """Project room coordinates and keep the rotated floor centered in the viewport."""
        scale, yaw, depth = self.projection_3d()
        ca, sa = math.cos(yaw), math.sin(yaw)

        def raw(px, py, pz=0):
            px -= self.room_w / 2
            py -= self.room_l / 2
            rx = px * ca - py * sa
            ry = px * sa + py * ca
            return (rx * scale, ry * scale * depth - pz * scale * 0.72)

        floor_points = [raw(0, 0), raw(self.room_w, 0),
                        raw(self.room_w, self.room_l), raw(0, self.room_l)]
        min_x = min(p[0] for p in floor_points)
        max_x = max(p[0] for p in floor_points)
        min_y = min(p[1] for p in floor_points)
        max_y = max(p[1] for p in floor_points)
        target_x = self.viewport.centerx + ox
        target_y = self.viewport.centery + oy + 8
        rx, ry = raw(x, y, z)
        return (int(target_x + rx - (min_x + max_x) / 2),
                int(target_y + ry - (min_y + max_y) / 2))

    # Calculate projected points used to draw a 3D furniture item.
    def object_points_3d(self, item, ox=0, oy=0, raised=True):
        rise = furniture_def(item["name"])["h"] if raised else 0
        return [self.project_3d(x, y, rise, ox, oy) for x, y in self.item_points(item)]

    # Find the furniture item closest to the mouse in the 3D view.
    def hit_test_3d(self, pos):
        # Test top layers first. The list order is the persistent draw/layer order.
        for i in range(len(self.items) - 1, -1, -1):
            item = self.items[i]
            definition = furniture_def(item["name"])
            if definition.get("wall_only"):
                wall = item.get("wall", "top")
                if item["name"] == "Window":
                    fixture_h, base_z = 1.2, 0.75
                elif item["name"] == "TV":
                    fixture_h, base_z = 0.7, 1.15
                else:
                    fixture_h, base_z = 2.1, 0.0
                if wall in ("top", "bottom"):
                    yy = 0 if wall == "top" else self.room_l
                    x1, x2 = item["x"]-item["w"]/2, item["x"]+item["w"]/2
                    poly = [self.project_3d(x1,yy,base_z), self.project_3d(x2,yy,base_z),
                            self.project_3d(x2,yy,base_z+fixture_h), self.project_3d(x1,yy,base_z+fixture_h)]
                else:
                    xx = 0 if wall == "left" else self.room_w
                    y1, y2 = item["y"]-item["w"]/2, item["y"]+item["w"]/2
                    poly = [self.project_3d(xx,y1,base_z), self.project_3d(xx,y2,base_z),
                            self.project_3d(xx,y2,base_z+fixture_h), self.project_3d(xx,y1,base_z+fixture_h)]
                if point_in_polygon(pos, poly):
                    return i
            elif point_in_polygon(pos, self.object_points_3d(item, raised=True)) or point_in_polygon(pos, self.object_points_3d(item, raised=False)):
                return i
        return None

    # Draw the room, walls, furniture, grid, and measurements in 3D.
    def draw_3d(self, surf, ox=0, oy=0):
        """Draw a three-quarter room with floor grid, rulers, and selectable furniture."""
        previous_clip = surf.get_clip()
        viewport_clip = self.viewport.move(ox, oy).clip(previous_clip)
        surf.set_clip(viewport_clip)
        pygame.draw.rect(surf, VIEW_BG, self.viewport.move(ox, oy), border_radius=10)
        corners = [self.project_3d(0, 0, ox=ox, oy=oy),
                   self.project_3d(self.room_w, 0, ox=ox, oy=oy),
                   self.project_3d(self.room_w, self.room_l, ox=ox, oy=oy),
                   self.project_3d(0, self.room_l, ox=ox, oy=oy)]
        pygame.draw.polygon(surf, (244, 247, 251), corners)
        wall_height = max(1.2, min(self.room_w, self.room_l) * 0.42)
        rear_a = self.project_3d(0, 0, wall_height, ox, oy)
        rear_b = self.project_3d(self.room_w, 0, wall_height, ox, oy)
        rear_d = self.project_3d(0, self.room_l, wall_height, ox, oy)
        pygame.draw.polygon(surf, (231, 237, 245), [corners[0], corners[1], rear_b, rear_a])
        pygame.draw.polygon(surf, (238, 242, 248), [corners[0], corners[3], rear_d, rear_a])
        # Grid lines are projected onto the floor plane.
        if self.grid_on:
            for m in range(int(self.room_w) + 1):
                a = self.project_3d(m, 0, ox=ox, oy=oy)
                b = self.project_3d(m, self.room_l, ox=ox, oy=oy)
                pygame.draw.line(surf, GRID, a, b, 1)
            for m in range(int(self.room_l) + 1):
                a = self.project_3d(0, m, ox=ox, oy=oy)
                b = self.project_3d(self.room_w, m, ox=ox, oy=oy)
                pygame.draw.line(surf, GRID, a, b, 1)
        for a, b in zip(corners, corners[1:] + corners[:1]):
            pygame.draw.line(surf, (147, 161, 180), a, b, 2)
        pygame.draw.line(surf, (147, 161, 180), rear_a, rear_b, 2)
        pygame.draw.line(surf, (147, 161, 180), rear_a, rear_d, 2)

        # 3D rulers: labelled metre ticks along the two visible floor edges.
        if self.rulers_on:
            for m in range(int(self.room_w) + 1):
                pt = self.project_3d(m, self.room_l, ox=ox, oy=oy)
                tick = self.project_3d(m, max(0, self.room_l - 0.14), ox=ox, oy=oy)
                pygame.draw.line(surf, MUTED, pt, tick, 1)
                label = TINY.render(str(m), True, MUTED)
                surf.blit(label, (pt[0] - label.get_width() // 2, pt[1] + 5))
            for m in range(int(self.room_l) + 1):
                pt = self.project_3d(0, m, ox=ox, oy=oy)
                pygame.draw.line(surf, MUTED, pt, (pt[0] - 4, pt[1] + 2), 1)
                label = TINY.render(str(m), True, MUTED)
                surf.blit(label, (pt[0] - label.get_width() - 5, pt[1] - label.get_height() // 2))

        # Paint furniture in depth order. Tops are solid, side faces are shaded, and details
        # are tailored to the item instead of adding generic stripes across every object.
        # Draw in persistent layer order. Selecting an object moves it to the end
        # of self.items, so it remains in front even after it is deselected.
        for original_index, item in enumerate(self.items):
            definition = furniture_def(item["name"])
            color = self.display_color(definition["color"])
            outline = SELECT if original_index == self.selected else shade(color, 48)
            if definition.get("wall_only"):
                wall = item.get("wall", "top")
                # Keep fixture geometry local to each item so no undefined values
                # leak in from the 2D drawing or hit-testing functions.
                if item["name"] == "Window":
                    fixture_h, base_z = 1.2, 0.75
                elif item["name"] == "TV":
                    fixture_h, base_z = 0.7, 1.15
                else:  # Door
                    fixture_h, base_z = 2.1, 0.0
                if wall in ("top", "bottom"):
                    x1, x2 = item["x"]-item["w"]/2, item["x"]+item["w"]/2
                    ywall = 0 if wall == "top" else self.room_l
                    fixture_pts = [self.project_3d(x1,ywall,base_z,ox,oy),
                                   self.project_3d(x2,ywall,base_z,ox,oy),
                                   self.project_3d(x2,ywall,base_z+fixture_h,ox,oy),
                                   self.project_3d(x1,ywall,base_z+fixture_h,ox,oy)]
                    if item["name"] == "TV":
                        front_y = item.get("l", 0.16) if wall == "top" else self.room_l-item.get("l", 0.16)
                        front_pts = [self.project_3d(x1,front_y,base_z,ox,oy),
                                     self.project_3d(x2,front_y,base_z,ox,oy),
                                     self.project_3d(x2,front_y,base_z+fixture_h,ox,oy),
                                     self.project_3d(x1,front_y,base_z+fixture_h,ox,oy)]
                else:
                    y1, y2 = item["y"]-item["w"]/2, item["y"]+item["w"]/2
                    xwall = 0 if wall == "left" else self.room_w
                    fixture_pts = [self.project_3d(xwall,y1,base_z,ox,oy),
                                   self.project_3d(xwall,y2,base_z,ox,oy),
                                   self.project_3d(xwall,y2,base_z+fixture_h,ox,oy),
                                   self.project_3d(xwall,y1,base_z+fixture_h,ox,oy)]
                    if item["name"] == "TV":
                        front_x = item.get("l", 0.16) if wall == "left" else self.room_w-item.get("l", 0.16)
                        front_pts = [self.project_3d(front_x,y1,base_z,ox,oy),
                                     self.project_3d(front_x,y2,base_z,ox,oy),
                                     self.project_3d(front_x,y2,base_z+fixture_h,ox,oy),
                                     self.project_3d(front_x,y1,base_z+fixture_h,ox,oy)]
                fixture_outline = SELECT if original_index == self.selected else shade(color, 48)
                if item["name"] == "TV":
                    # A simple, solid TV rectangle with visible depth projecting inward from the wall.
                    for edge in range(4):
                        nxt = (edge + 1) % 4
                        pygame.draw.polygon(surf, shade(color, 24),
                                            [fixture_pts[edge], fixture_pts[nxt], front_pts[nxt], front_pts[edge]])
                    pygame.draw.polygon(surf, color, front_pts)
                    pygame.draw.polygon(surf, fixture_outline, front_pts, 2)
                    label_center = (sum(pt[0] for pt in front_pts)//4, sum(pt[1] for pt in front_pts)//4)
                else:
                    pygame.draw.polygon(surf, color, fixture_pts)
                    pygame.draw.polygon(surf, fixture_outline, fixture_pts, 2)
                    label_center = (sum(pt[0] for pt in fixture_pts)//4,
                                    sum(pt[1] for pt in fixture_pts)//4)
                label = SMALL.render(item["name"], True, INK)
                surf.blit(label, label.get_rect(center=(label_center[0], label_center[1]-13)))
                continue

            center = self.project_3d(item["x"], item["y"], 0, ox, oy)
            height = definition["h"]
            base_points = [self.project_3d(x, y, 0, ox, oy) for x, y in self.item_points(item)]
            top_points = self.object_points_3d(item, ox=ox, oy=oy, raised=True)

            if item["name"] == "Round Table":
                # A plain filled cylinder: circular top plus a solid extruded body, no legs/details.
                angles = [2 * math.pi * j / 48 for j in range(48)]
                radius = item["w"] / 2
                bottom_ring = [self.project_3d(item["x"] + radius*math.cos(a),
                                               item["y"] + radius*math.sin(a), 0, ox, oy)
                               for a in angles]
                top_ring = [self.project_3d(item["x"] + radius*math.cos(a),
                                            item["y"] + radius*math.sin(a), height, ox, oy)
                            for a in angles]
                # Draw solid side faces without internal outlines so the table reads as one object.
                for j in range(len(angles)):
                    k = (j + 1) % len(angles)
                    face_color = shade(color, 18)
                    pygame.draw.polygon(surf, face_color,
                                        [bottom_ring[j], bottom_ring[k], top_ring[k], top_ring[j]])
                pygame.draw.polygon(surf, color, top_ring)
                if original_index == self.selected:
                    pygame.draw.polygon(surf, SELECT, top_ring, 3)
            else:
                # Vertical sides are shaded, while the top is a clean solid silhouette.
                for j in range(4):
                    k = (j+1) % 4
                    face = [base_points[j], base_points[k], top_points[k], top_points[j]]
                    pygame.draw.polygon(surf, shade(color, 28 + j*2), face)
                pygame.draw.polygon(surf, color, top_points)
                pygame.draw.lines(surf, outline, True, top_points, 3 if original_index == self.selected else 1)


            label = SMALL.render(item["name"], True, INK)
            label_pos = self.project_3d(item["x"], item["y"], height + 0.08, ox, oy)
            surf.blit(label, label.get_rect(center=(label_pos[0], label_pos[1]+12)))

        # Selected-object measurements match the 2D label.
        if self.selected is not None and self.selected < len(self.items):
            it = self.items[self.selected]
            label = f'W {it["w"]:.2f} m  ×  L {it["l"]:.2f} m'
            r = pygame.Rect(self.viewport.centerx-88+ox, self.viewport.top+8+oy, 176, 24)
            rounded(surf, r, WHITE, 6, BORDER)
            centered(surf, label, r, INK, TINY)
        surf.set_clip(previous_clip)

    # Draw the active 2D or 3D room view inside the viewport.
    def draw_view(self, surf, offset=(0,0)):
        ox,oy=offset
        if self.mode=="2D":
            self.draw_2d(surf,ox,oy)
            self.draw_rulers(surf,ox,oy)
        else:
            pygame.draw.rect(surf,VIEW_BG,self.viewport.move(ox,oy),border_radius=10)
            self.draw_3d(surf,ox,oy)

    # Draw status information and the selected object details.
    def draw_footer(self, surf):
        sw,sh=surf.get_size()
        y=sh-FOOTER_H
        pygame.draw.rect(surf,WHITE,(0,y,sw,FOOTER_H))
        text(surf,f"Room X: {self.room_w:.2f} m",(12,y+10),MUTED,TINY)
        text(surf,f"Room Y: {self.room_l:.2f} m",(118,y+10),MUTED,TINY)
        selected="None"
        if self.selected is not None and self.selected<len(self.items):
            selected=self.items[self.selected]["name"]
        # Emphasize only the label; the selected object's name stays regular.
        label_img = load_ui_font(10, bold=True).render("SELECTED OBJECT:", True, BLUE)
        value_img = TINY.render(f" {selected}", True, BLUE)
        total_width = label_img.get_width() + value_img.get_width()
        label_x = max(12, sw - total_width - 14)
        surf.blit(label_img, (label_x, y+10))
        surf.blit(value_img, (label_x + label_img.get_width(), y+10))
        if pygame.time.get_ticks()<self.status_until:
            image=SMALL.render(self.status,True,GREEN)
            surf.blit(image,(max(12,sw//2-image.get_width()//2),y+8))

    # Show the keyboard and mouse controls help panel.
    def draw_controls_menu(self, surf):
        """Show the combined keyboard and mouse help panel."""
        sw, sh = surf.get_size()
        panel = pygame.Rect(max(24, sw // 2 - 270), max(70, sh // 2 - 205), 540, 410)
        shade = pygame.Surface((sw, sh), pygame.SRCALPHA)
        shade.fill((20, 30, 45, 105))
        surf.blit(shade, (0, 0))
        rounded(surf, panel, WHITE, 12, BORDER, 2)
        text(surf, "Controls", panel.x + 22, panel.y + 18, BLUE, TITLE)
        entries = [
            ("H / Controls", "Show or hide this guide"),
            ("Tab", "Switch between 2D and 3D"),
            ("Ctrl + Z / Ctrl + Y", "Undo / redo"),
            ("Delete / Backspace / X", "Delete selected furniture"),
            ("+ / -", "Increase / decrease selected size"),
            ("Q / E", "Rotate selected furniture / wall fixture"),
            ("Alt + drag", "Snap furniture to the 0.25 m grid"),
            ("R", "Clear the layout"),
            ("Left-Click", "Move select / objects; rotate the room view"),
            ("Mouse wheel", "Scroll the Library list"),
        ]
        y = panel.y + 62
        for key, description in entries:
            text(surf, key, panel.x + 24, y, BLUE if key.startswith("3D") else INK, SMALL)
            text(surf, description, panel.x + 225, y, MUTED, SMALL)
            y += 27
        text(surf, "Click Controls or press H to close", panel.x + 22, panel.bottom - 25, MUTED, TINY)

    # Draw the full application interface for the current frame.
    def draw(self):
        self.relayout()
        self.buttons = {}
        screen.fill(WHITE)
        self.draw_header(screen)
        self.draw_toolbar(screen)
        self.draw_sidebar(screen)
        self.draw_view(screen)
        self.draw_footer(screen)
        if self.controls_open:
            self.draw_controls_menu(screen)
        pygame.display.flip()

    # Handle mouse clicks on buttons, furniture, and the room view.
    def handle_click(self,pos):
        # Clicking anywhere else commits/leaves text inputs so shortcuts keep working.
        self.input_focus = None
        # Header
        for key in ("mode2d", "mode3d"):
            if self.buttons.get(key,pygame.Rect(0,0,0,0)).collidepoint(pos):
                if key=="mode2d":
                    self.mode="2D"
                elif key == "mode3d":
                    self.mode = "3D"
                return
        # Toolbar
        for key in ("grid", "rulers", "grayscale", "colored", "export", "help"):
            if self.buttons.get(key,pygame.Rect(0,0,0,0)).collidepoint(pos):
                if key == "grid":
                    self.grid_on = not self.grid_on
                elif key == "rulers":
                    self.rulers_on = not self.rulers_on
                elif key in ("grayscale", "colored"):
                    self.color_mode = key
                elif key == "export":
                    self.export_viewport()
                elif key == "help":
                    self.controls_open = not self.controls_open
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
                if self.buttons.get("project_open_"+name, pygame.Rect(0,0,0,0)).collidepoint(pos):
                    self.load_project(name); return
                if self.buttons.get("project_delete_"+name, pygame.Rect(0,0,0,0)).collidepoint(pos):
                    del self.projects[name]
                    self.project_timestamps.pop(name, None)
                    self.status_msg(f"Deleted saved project: {name}")
                    return
                if self.buttons.get("project_"+name,pygame.Rect(0,0,0,0)).collidepoint(pos):
                    self.load_project(name); return
        else:
            for definition in FURNITURE:
                if self.buttons.get("furn_"+definition["name"],pygame.Rect(0,0,0,0)).collidepoint(pos):
                    self.add_furniture(definition["name"]); return

        # In 2D, drag furniture. In 3D, left-drag rotates the camera.
        if self.viewport.collidepoint(pos):
            if self.mode == "2D":
                index = self.hit_test(pos)
                if index is not None:
                    self.push_undo()
                    self.bring_to_front(index)
                    self.dragging = True
                    wx, wy = self.screen_to_world(*pos)
                    item = self.items[self.selected]
                    self.drag_offset = (item["x"] - wx, item["y"] - wy)
                    self.last_mouse_pos = pos
                else:
                    self.selected = None
            else:
                index = self.hit_test_3d(pos)
                if index is not None:
                    self.push_undo()
                    self.bring_to_front(index)
                    self.dragging = True
                    self.last_mouse_pos = pos
                    self.drag_offset = (self.items[self.selected]["x"], self.items[self.selected]["y"])
                else:
                    self.selected = None
                    self.rotating_view = True
                    self.last_mouse_pos = pos

    # Calculate the visible scrolling range for the furniture list.
    def library_scroll_bounds(self):
        """Return the exact visible Library list area and its maximum scroll."""
        sh = screen.get_height()
        # Keep this in sync with draw_sidebar's Furniture tab layout.
        list_top = HEADER_H + 68 + 48 + 22 + 8
        list_bottom = sh - FOOTER_H - 14
        visible_height = max(1, list_bottom - list_top)
        row_step = 49
        content_height = len(FURNITURE) * row_step + 22  # room after final item
        max_scroll = max(0, content_height - visible_height)
        return pygame.Rect(0, list_top, SIDEBAR_W, visible_height), max_scroll

    # Scroll the furniture list up or down when the pointer is over it.
    def scroll_library(self, amount, mouse_pos):
        """Scroll only when the pointer is over the Furniture Library list."""
        if self.full_view or self.tab != "Furniture":
            return
        list_rect, max_scroll = self.library_scroll_bounds()
        if list_rect.collidepoint(mouse_pos):
            self.furniture_scroll = clamp(self.furniture_scroll + amount, 0, max_scroll)

    # Process mouse, keyboard, and window events.
    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.relayout()
            return
        if event.type == pygame.MOUSEWHEEL:
            # Pygame 2 wheel events report positive y for up and negative y for down.
            mouse_pos = (getattr(event, "mouse_x", pygame.mouse.get_pos()[0]),
                         getattr(event, "mouse_y", pygame.mouse.get_pos()[1]))
            self.scroll_library(-event.y * 42, mouse_pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self.mode == "3D" and self.viewport.collidepoint(event.pos):
            self.rotating_view = True
            self.last_mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
            self.dragging = False
            self.rotating_view = False
            self.last_mouse_pos = None
        elif event.type == pygame.MOUSEMOTION:
            if self.rotating_view and self.mode == "3D" and self.last_mouse_pos is not None:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                self.camera_yaw += dx * 0.008
                self.camera_pitch = clamp(self.camera_pitch + dy * 0.003, 0.28, 0.68)
                self.last_mouse_pos = event.pos
            elif self.dragging and self.selected is not None and self.last_mouse_pos is not None:
                item = self.items[self.selected]
                if self.mode == "2D":
                    wx, wy = self.screen_to_world(*event.pos)
                    item["x"], item["y"] = wx + self.drag_offset[0], wy + self.drag_offset[1]
                else:
                    # Invert the same yaw/depth transform used to project the floor.
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    scale, yaw, depth = self.projection_3d()
                    rx = dx / max(1, scale)
                    ry = dy / max(1, scale * depth)
                    ca, sa = math.cos(yaw), math.sin(yaw)
                    item["x"] += rx * ca + ry * sa
                    item["y"] += -rx * sa + ry * ca
                if furniture_def(item["name"]).get("wall_only"):
                    self.update_wall_attachment(item)
                else:
                    self.keep_inside(item)
                if pygame.key.get_mods() & pygame.KMOD_ALT:
                    self.snap_item_to_grid(item, 0.25)
                self.last_mouse_pos = event.pos
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.controls_open = not self.controls_open
                return
            if self.input_focus:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.input_focus = None
                    return
                if event.key == pygame.K_BACKSPACE:
                    if self.input_focus == "project_name":
                        self.project_name = self.project_name[:-1]
                    elif self.input_focus == "width_input":
                        self.width_text = self.width_text[:-1]
                    elif self.input_focus == "length_input":
                        self.length_text = self.length_text[:-1]
                    return
                if event.unicode and event.unicode.isprintable():
                    if self.input_focus == "project_name" and len(self.project_name) < 32:
                        self.project_name += event.unicode
                    elif self.input_focus in ("width_input", "length_input") and event.unicode in "0123456789.":
                        if self.input_focus == "width_input":
                            self.width_text += event.unicode
                        else:
                            self.length_text += event.unicode
                return
            mods = getattr(event, "mod", pygame.key.get_mods())
            ctrl_down = bool(mods & pygame.KMOD_CTRL)
            if ctrl_down and event.key == pygame.K_z:
                self.undo()
            elif ctrl_down and event.key == pygame.K_y:
                self.redo()
            elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE, pygame.K_x):
                self.delete_selected()
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS) or event.unicode == "+":
                self.resize_selected(1.1)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS) or event.unicode == "-":
                self.resize_selected(1 / 1.1)
            elif event.key == pygame.K_q:
                self.rotate_selected(-15)
            elif event.key == pygame.K_e:
                self.rotate_selected(15)
            elif event.key == pygame.K_TAB:
                self.mode = "3D" if self.mode == "2D" else "2D"
            elif event.key == pygame.K_r:
                self.reset_layout()


# Check whether a point falls inside a polygon.
# -------------------------- Geometry helper -------------------------------
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


# Create the planner and run the Pygame event/drawing loop.
# ------------------------------ App entry point ----------------------------
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
