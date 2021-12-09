# -*- coding: utf-8 -*-
""" Localization Tools.

"""

import math
import tkinter as tk
from collections.abc import Callable

import numpy as np
from mindstone.control.graph import DirectedGraph, Node
from mindstone.core.utils import update_item, get_nested

__all__ = ["LocalizationModel"]


def project_point(coordinate: list, x_offset=0, y_offset=0, axis_angle: float = np.pi / 6) -> list:
    """ Project a point described with 3 coordinates (x_axis, y_axis, z_axis) into one that is described with only
    two (x_axis, y_axis)
    Given a 3-dimensional point P its projection P' is given by the following mapping

        (x_axis, y_axis, z_axis) -> ((x_axis - y_axis) * cos(A), z_axis - (x_axis + y_axis) * sin(A))

    Where A is the angle the projected x_axis and y_axis axes make make 2-dimensional x_axis and y_axis axis.

    :param coordinate: x_axis, y_axis, and z_axis coordinates (listed in that order)
    :param x_offset: x_axis shift of the 2-dimensional projected point
    :param y_offset: y_axis shift of the 2-dimensional projected point
    :param axis_angle: the angle the projected x_axis and y_axis axes make make 2-dimensional x_axis and y_axis axis
    :return: projected point in the form [x_axis, y_axis]
    """
    if len(coordinate) != 3:
        raise ValueError("Coordinate requires three values.")
    x, y, z = coordinate
    return [(x - y) * np.cos(axis_angle) + x_offset, y_offset - (z - np.sin(axis_angle) * (x + y))]


def project_line(start: list, end: list, x_offset=0, y_offset=0) -> list:
    return project_point(start, x_offset, y_offset) + project_point(end, x_offset, y_offset)


def unit_vector(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def x_axis_rotation_matrix(angle: float) -> np.ndarray:
    return np.array([
        [1, 0, 0],
        [0, np.cos(angle), -np.sin(angle)],
        [0, np.sin(angle), np.cos(angle)]
    ], dtype=np.float32)


def y_axis_rotation_matrix(angle: float) -> np.ndarray:
    return np.array([
        [np.cos(angle), 0, np.sin(angle)],
        [0, 1, 0],
        [-np.sin(angle), 0, np.cos(angle)]
    ], dtype=np.float32)


def z_axis_rotation_matrix(angle: float) -> np.ndarray:
    return np.array([
        [np.cos(angle), -np.sin(angle), 0],
        [np.sin(angle), np.cos(angle), 0],
        [0, 0, 1]
    ], dtype=np.float32)


def cartesian_to_spherical(v: np.ndarray) -> tuple:
    if not (v.ndim == 1 and v.size == 3):
        raise ValueError("Invalid array provided.")
    r = np.linalg.norm(v)
    if r == 0:
        # this means that all the components in the vector
        # are equal to zero.
        return 0, 0, 0
    x, y, z = v
    theta = np.arccos(z / r)
    if theta == 0:
        return r, 0, 0
    # had to round to mitigate domain errors => 1.00000000002
    phi = np.arccos(round(x / (r * np.sin(theta)), 5))
    return r, theta, phi


def spherical_to_cartesian(r, theta, phi) -> tuple:
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    z = r * np.cos(theta)
    return x, y, z


def _handle_distance_measurement(surroundings: list, point: np.ndarray, position: np.ndarray, value: float) -> None:
    """ Create a new point from a distance measurement and adapt the environment to suite the measurement.

    :param surroundings: the initial space.
    :param point: Vector that describes the orientation of the measuring device.
    :param position: The position of the measuring device in space.
    :param value: The measured value.
    :return: The adapted space.
    """
    precision = 1
    unit_direction = np.around(unit_vector(point), precision)
    new_point = position + unit_direction * value
    if surroundings:
        # remove any intersecting measured points
        for i, point in enumerate(surroundings):
            if (np.around(unit_vector(point - position), precision) == unit_direction).all():
                surroundings.pop(i)
    surroundings.append(new_point)


def _change_theta_parameter(p: np.ndarray, value: float) -> None:
    r, theta, phi = cartesian_to_spherical(p)
    for i, c in enumerate(spherical_to_cartesian(r, theta, value)):
        p.__setitem__(i, c)


def _change_phi_parameter(p: np.ndarray, value: float) -> None:
    r, theta, phi = cartesian_to_spherical(p)
    for i, c in enumerate(spherical_to_cartesian(r, theta, value)):
        p.__setitem__(i, c)


_surrounding_adapters = {
    "d": _handle_distance_measurement
}

_parameter_setters = {
    "x": lambda p, value: p.__setitem__(0, value),
    "y": lambda p, value: p.__setitem__(1, value),
    "z": lambda p, value: p.__setitem__(2, value),
    "r": lambda p, value: unit_vector(p) * value,
    "theta": _change_theta_parameter,
    "phi": _change_phi_parameter,
}

_parameter_getters = {
    "x": lambda p: p[0],
    "y": lambda p: p[1],
    "z": lambda p: p[2],
    "r": lambda p: cartesian_to_spherical(p)[0],
    "theta": lambda p: cartesian_to_spherical(p)[1],
    "phi": lambda p: cartesian_to_spherical(p)[2],
}

_angle_parameters = {"theta", "phi"}

_to_radians_converters = {
    "radians": lambda a: a,
    "degrees": lambda a: math.radians(a)
}


class LocalizationModel(DirectedGraph):
    """ Localization model class.

    The location model object is used to define the location of points in 3d space.
    """

    def __init__(self, angle_units: str = "degrees"):
        super(LocalizationModel, self).__init__()
        self._core_tag = None
        self._surrounding_points = []
        self._body_points = {}
        self._angle_units = angle_units
        self._observables = []
        # set: stores component observables in tuple of the form (key, parameter, component, observable)
        self._x_rotation_matrix = x_axis_rotation_matrix(0)
        self._y_rotation_matrix = y_axis_rotation_matrix(0)
        self._z_rotation_matrix = z_axis_rotation_matrix(0)

    def __call__(self, gate, payload: dict):
        self.adapt(payload)
        return payload

    @property
    def orientation(self) -> np.ndarray:
        return self._x_rotation_matrix * self._y_rotation_matrix * self._z_rotation_matrix

    def add_edge(self, from_tag: str, to_tag: str):
        super(LocalizationModel, self).add_edge(from_tag, to_tag)
        if not self.is_acyclic:
            raise RuntimeError("The edge '{}' to '{}' creates a cycle.".format(from_tag, to_tag))

    def body_point(self, tag: str, x: float, y: float, z: float, is_core: bool = False):
        self.add_node(key=tag, node=Node())
        self._body_points[tag] = np.array([x, y, z])
        self._core_tag = tag if is_core else self._core_tag
        return self

    def observable(self, tag: str, type: str, location: str, transformer: Callable = lambda x: x):
        if tag not in self:
            raise ValueError("Provided tag '{}' does not exists".format(tag))
        allowed_types = set(_parameter_setters).union(_surrounding_adapters)
        if type not in allowed_types:
            raise ValueError("Provided observable type '{}' is invalid. Allowed types: {}".format(
                tag, ", ".join(allowed_types)))
        self._observables.append((tag, type, location, transformer))
        return self

    def get_parameter(self, tag: str, type: str):
        parameter = _parameter_getters[type](self._body_points[tag])
        return _to_radians_converters[self._angle_units](parameter) if type in _angle_parameters else parameter

    def set_parameter(self, tag: str, type: str, value):
        value = _to_radians_converters[self._angle_units](value) if type in _angle_parameters else value
        _parameter_setters[type](self._body_points[tag], value)

    def adapt_surroundings(self, tag: str, type, value):
        _surrounding_adapters[type](self._surrounding_points, self._body_points[tag], self.get_location(tag), value)

    def adapt(self, observations: dict):
        for tag, type, location, transformer in self._observables:
            observation = get_nested(location, observations)
            if observation is None:
                continue
            if type in _parameter_setters:
                self.set_parameter(tag, type, transformer(observation))
            elif type in _surrounding_adapters:
                self.adapt_surroundings(tag, type, transformer(observation))

    def translate(self, x_shift: float = 0, y_shift: float = 0, z_shift: float = 0):
        self._body_points[self._core_tag] += np.array([x_shift, y_shift, z_shift])

    def change_orientation(self, roll: float = None, pitch: float = None, yaw: float = None):
        if roll is not None:
            self._x_rotation_matrix = x_axis_rotation_matrix(_to_radians_converters[self._angle_units](roll))
        if pitch is not None:
            self._y_rotation_matrix = x_axis_rotation_matrix(_to_radians_converters[self._angle_units](pitch))
        if yaw is not None:
            self._z_rotation_matrix = x_axis_rotation_matrix(_to_radians_converters[self._angle_units](yaw))

    def get_location(self, tag: str) -> np.ndarray:
        if tag == self._core_tag:
            return self._body_points[tag]
        return self.orientation.dot(self._location_util(tag, np.array([0, 0, 0]))) + self._body_points[self._core_tag]

    def get_all_locations(self) -> dict:
        positions = {}
        for key in self._body_points.keys():
            positions[key] = self.get_location(key)
        return positions

    def display(self, window_width: int = 500, window_height: int = 500):
        """ display the given localization model visually to the user.

        :param window_width: width of the display window.
        :param window_height: height of the display window
        """
        # get the center point of the window
        x_offset = window_width // 2
        y_offset = window_height // 2

        # 1. setup tkinter
        root = tk.Tk()
        root.title("Model Display")
        root.configure(bg="blue")
        root.geometry("{}x{}".format(window_width, window_height))
        canvas = tk.Canvas(
            root,
            width=window_width,
            height=window_height,
            borderwidth=0,
            highlightthickness=0,
            bg="black"
        )
        canvas.pack()

        size = 200

        # display grid
        gap = 20
        for y in range(-size, size, gap):
            canvas.create_line(*project_line([-size, y, 0], [size, y, 0], x_offset, y_offset), fill="#222")
        for x in range(-size, size, gap):
            canvas.create_line(*project_line([x, -size, 0], [x, size, 0], x_offset, y_offset), fill="#222")

        # 2. render axes
        x_axis_line = ([size, 0, 0], [-size, 0, 0])
        y_axis_line = ([0, size, 0], [0, -size, 0])
        z_axis_line = ([0, 0, size], [0, 0, -size])
        axes = [x_axis_line, y_axis_line, z_axis_line]

        canvas.create_text(project_point(x_axis_line[0], x_offset, y_offset), text="x-axis", fill="#fff")
        canvas.create_text(project_point(y_axis_line[0], x_offset, y_offset), text="y-axis", fill="#fff")
        canvas.create_text(project_point(z_axis_line[0], x_offset, y_offset), text="z-axis", fill="#fff")

        for start, end in axes:
            canvas.create_line(*project_line(start, end, x_offset, y_offset),
                               fill="grey", dash=(4, 2))

        positions = self.get_all_locations()

        # 3. render _points lines
        edges = self.edges
        for from_, to in edges:
            canvas.create_line(project_line(positions[from_], positions[to], x_offset, y_offset), fill="red")
            canvas.create_text(*project_point(positions[from_], x_offset, y_offset), text=from_, fill="#fff")
            canvas.create_text(*project_point(positions[to], x_offset, y_offset), text=to, fill="#fff")

        # 4. display measured _points and labels
        diameter = 4
        for point in self._surrounding_points:
            x, y = project_point(point, x_offset, y_offset)
            canvas.create_oval(
                x - diameter // 2,
                y - diameter // 2,
                x + diameter // 2,
                y + diameter // 2,
                fill="#fff")

        root.mainloop()

    def _location_util(self, tag: str, reference: np.ndarray) -> np.ndarray:
        parents = self.in_neighbors(tag)
        if not parents:
            return reference
        return self._location_util(parents.pop(), self._body_points[tag] + reference)
