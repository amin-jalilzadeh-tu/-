import math
from math import sqrt, radians, cos, sin

def rotate_point(px, py, pz, orientation_rad):
    x_new = cos(orientation_rad) * px - sin(orientation_rad) * py
    y_new = sin(orientation_rad) * px + cos(orientation_rad) * py
    return (x_new, y_new, pz)

def compute_dimensions_from_area_perimeter(area, perimeter):
    """
    Solve for width (w) and length (l) using area (A) and perimeter (P):
      w = A / (P/4)
      l = A / w
    """
    if perimeter <= 0:
        raise ValueError("Perimeter must be positive.")
    if area <= 0:
        raise ValueError("Area must be positive.")
    width = area / (perimeter / 4.0)
    length = area / width
    return width, length

def create_building_base_polygon(width, length, orientation):
    """
    Return 4 points in XY plane for a rectangle, rotate them by orientation degrees.
    """
    A = (0, 0, 0)
    B = (width, 0, 0)
    C = (width, length, 0)
    D = (0, length, 0)

    if orientation != 0:
        orientation_rad = radians(orientation)
        A = rotate_point(*A, orientation_rad)
        B = rotate_point(*B, orientation_rad)
        C = rotate_point(*C, orientation_rad)
        D = rotate_point(*D, orientation_rad)

    return A, B, C, D

def polygon_area(poly):
    """Compute area in XY plane via Shoelace formula."""
    x = [p[0] for p in poly]
    y = [p[1] for p in poly]
    n = len(poly)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += x[i] * y[j] - x[j] * y[i]
    return abs(area) / 2.0

def inward_offset_polygon(A, B, C, D, depth):
    """
    Inward offset of rectangle ABCD by depth, returning [A2,B2,C2,D2] or None if invalid.
    """
    def edge_offset(P1, P2, dist):
        vx = P2[0] - P1[0]
        vy = P2[1] - P1[1]
        length = sqrt(vx*vx + vy*vy)
        nx = -vy / length
        ny = vx / length
        return [
            (P1[0] + nx*dist, P1[1] + ny*dist, P1[2]),
            (P2[0] + nx*dist, P2[1] + ny*dist, P2[2])
        ]

    def line_intersect(p1, p2, p3, p4):
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        x3, y3 = p3[0], p3[1]
        x4, y4 = p4[0], p4[1]
        denom = (y4 - y3)*(x2 - x1) - (x4 - x3)*(y2 - y1)
        if abs(denom) < 1e-12:
            return None
        ua = ((x4 - x3)*(y1 - y3) - (y4 - y3)*(x1 - x3)) / denom
        X = x1 + ua*(x2 - x1)
        Y = y1 + ua*(y2 - y1)
        return (X, Y, p1[2])

    front_line = edge_offset(A, B, depth)
    right_line = edge_offset(B, C, depth)
    rear_line = edge_offset(C, D, depth)
    left_line = edge_offset(D, A, depth)

    A2 = line_intersect(front_line[0], front_line[1], left_line[0], left_line[1])
    B2 = line_intersect(front_line[0], front_line[1], right_line[0], right_line[1])
    C2 = line_intersect(rear_line[0], rear_line[1], right_line[0], right_line[1])
    D2 = line_intersect(rear_line[0], rear_line[1], left_line[0], left_line[1])

    if A2 and B2 and C2 and D2:
        return [A2, B2, C2, D2]
    else:
        return None
