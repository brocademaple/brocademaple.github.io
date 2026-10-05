#!/usr/bin/env python3
"""Build the local-only Atlantis Gallery Master V2 structural graybox.

The script deliberately creates a lightweight, reproducible review model:

- asymmetric crescent campus instead of the V1 axial palace;
- one continuous 3.2 m visitor loop plus accessible rising routes;
- a large three-level Grand Tide Archive;
- one long glass-vault gallery and three terraced pavilions;
- four review cameras, low-cost Eevee renders, a compact GLB, and an audit.

It never writes to ``master-v1`` or Hugo's ``static``/``public`` trees. All
review outputs stay under ignored local folders until the user approves V2.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TAU = math.tau
RNG = random.Random(20260819)


def cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--skip-renders", action="store_true")
    argv = sys.argv
    return parser.parse_args(argv[argv.index("--") + 1 :] if "--" in argv else [])


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def make_collection(name: str, color_tag: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    collection.color_tag = color_tag
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj: bpy.types.Object, collection: bpy.types.Collection) -> bpy.types.Object:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.65,
    transmission: float = 0.0,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = color[3]
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if color[3] < 1.0:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
        mat.use_transparency_overlap = False
    return mat


def add_box(
    name: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    rotation_z: float = 0.0,
    bevel: float = 0.08,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=(0, 0, rotation_z))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("SoftenedEdges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return move_to(obj, collection)


def add_cylinder(
    name: str,
    radius: float,
    depth: float,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    vertices: int = 48,
    scale_xy: tuple[float, float] = (1.0, 1.0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale.x = scale_xy[0]
    obj.scale.y = scale_xy[1]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return move_to(obj, collection)


def add_ico(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    subdivisions: int = 1,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), RNG.uniform(0, TAU))
    obj.data.materials.append(mat)
    return move_to(obj, collection)


def mesh_object(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    return obj


def add_ellipse_band(
    name: str,
    center: tuple[float, float],
    radii: tuple[float, float],
    width: float,
    z: float,
    thickness: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    start: float = 0.0,
    end: float = TAU,
    segments: int = 96,
) -> bpy.types.Object:
    cx, cy = center
    rx, ry = radii
    inner_rx = rx - width
    inner_ry = ry - width
    bottom = z - thickness / 2
    top = z + thickness / 2
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for index in range(segments + 1):
        angle = start + (end - start) * index / segments
        co = math.cos(angle)
        si = math.sin(angle)
        vertices.extend(
            [
                (cx + rx * co, cy + ry * si, top),
                (cx + inner_rx * co, cy + inner_ry * si, top),
                (cx + rx * co, cy + ry * si, bottom),
                (cx + inner_rx * co, cy + inner_ry * si, bottom),
            ]
        )
    for index in range(segments):
        a = index * 4
        b = (index + 1) * 4
        faces.extend(
            [
                (a, b, b + 1, a + 1),
                (a + 2, a + 3, b + 3, b + 2),
                (a, a + 2, b + 2, b),
                (a + 1, b + 1, b + 3, a + 3),
            ]
        )
    if end - start < TAU - 1e-4:
        faces.extend([(0, 1, 3, 2), (segments * 4, segments * 4 + 2, segments * 4 + 3, segments * 4 + 1)])
    return mesh_object(name, vertices, faces, mat, collection)


def add_arc_wall(
    name: str,
    center: tuple[float, float],
    radius: float,
    thickness: float,
    base_z: float,
    height: float,
    start: float,
    end: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    segments: int = 72,
) -> bpy.types.Object:
    cx, cy = center
    outer = radius
    inner = radius - thickness
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for index in range(segments + 1):
        angle = start + (end - start) * index / segments
        co = math.cos(angle)
        si = math.sin(angle)
        vertices.extend(
            [
                (cx + outer * co, cy + outer * si, base_z),
                (cx + inner * co, cy + inner * si, base_z),
                (cx + outer * co, cy + outer * si, base_z + height),
                (cx + inner * co, cy + inner * si, base_z + height),
            ]
        )
    for index in range(segments):
        a = index * 4
        b = (index + 1) * 4
        faces.extend(
            [
                (a, b, b + 2, a + 2),
                (a + 1, a + 3, b + 3, b + 1),
                (a + 2, b + 2, b + 3, a + 3),
                (a, a + 1, b + 1, b),
            ]
        )
    faces.extend([(0, 2, 3, 1), (segments * 4, segments * 4 + 1, segments * 4 + 3, segments * 4 + 2)])
    return mesh_object(name, vertices, faces, mat, collection)


def add_path_strip(
    name: str,
    points: list[tuple[float, float, float]],
    width: float,
    thickness: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for index, point in enumerate(points):
        previous = Vector(points[max(0, index - 1)])
        following = Vector(points[min(len(points) - 1, index + 1)])
        tangent = following - previous
        tangent.z = 0
        if tangent.length == 0:
            tangent = Vector((1, 0, 0))
        tangent.normalize()
        side = Vector((-tangent.y, tangent.x, 0)) * width / 2
        center = Vector(point)
        top_left = center + side
        top_right = center - side
        vertices.extend(
            [
                tuple(top_left),
                tuple(top_right),
                (top_left.x, top_left.y, top_left.z - thickness),
                (top_right.x, top_right.y, top_right.z - thickness),
            ]
        )
    for index in range(len(points) - 1):
        a = index * 4
        b = (index + 1) * 4
        faces.extend(
            [
                (a, b, b + 1, a + 1),
                (a + 2, a + 3, b + 3, b + 2),
                (a, a + 2, b + 2, b),
                (a + 1, b + 1, b + 3, a + 3),
            ]
        )
    last = (len(points) - 1) * 4
    faces.extend([(0, 1, 3, 2), (last, last + 2, last + 3, last + 1)])
    return mesh_object(name, vertices, faces, mat, collection)


def add_tube(
    name: str,
    points: list[tuple[float, float, float]],
    radius: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    bevel_resolution: int = 1,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name + "_curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = bevel_resolution
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for control, point in zip(spline.points, points):
        control.co = (*point, 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    return obj


def add_dome(
    name: str,
    center: tuple[float, float],
    base_z: float,
    radius: float,
    height: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    rings: int = 8,
    segments: int = 40,
) -> bpy.types.Object:
    cx, cy = center
    vertices: list[tuple[float, float, float]] = [(cx, cy, base_z + height)]
    faces: list[tuple[int, ...]] = []
    for ring in range(1, rings + 1):
        phi = (math.pi / 2) * ring / rings
        ring_radius = radius * math.sin(phi)
        z = base_z + height * math.cos(phi)
        for segment in range(segments):
            angle = TAU * segment / segments
            vertices.append((cx + ring_radius * math.cos(angle), cy + ring_radius * math.sin(angle), z))
    for segment in range(segments):
        faces.append((0, 1 + segment, 1 + (segment + 1) % segments))
    for ring in range(rings - 1):
        start = 1 + ring * segments
        next_start = start + segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((start + segment, next_start + segment, next_start + next_segment, start + next_segment))
    return mesh_object(name, vertices, faces, mat, collection)


def add_vault_surface(
    name: str,
    center: tuple[float, float],
    base_z: float,
    width: float,
    length: float,
    rise: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    arch_segments: int = 18,
    length_segments: int = 12,
) -> bpy.types.Object:
    cx, cy = center
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for yi in range(length_segments + 1):
        y = cy - length / 2 + length * yi / length_segments
        for ai in range(arch_segments + 1):
            angle = math.pi - math.pi * ai / arch_segments
            x = cx + math.cos(angle) * width / 2
            z = base_z + math.sin(angle) * rise
            vertices.append((x, y, z))
    row = arch_segments + 1
    for yi in range(length_segments):
        for ai in range(arch_segments):
            a = yi * row + ai
            b = (yi + 1) * row + ai
            faces.append((a, b, b + 1, a + 1))
    return mesh_object(name, vertices, faces, mat, collection)


def add_text(
    name: str,
    body: str,
    location: tuple[float, float, float],
    rotation: tuple[float, float, float],
    size: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.015
    obj.data.bevel_depth = 0.006
    obj.data.materials.append(mat)
    return move_to(obj, collection)


def add_light(
    name: str,
    light_type: str,
    location: tuple[float, float, float],
    color: tuple[float, float, float],
    energy: float,
    collection: bpy.types.Collection,
    *,
    size: float = 5.0,
    target: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    data = bpy.data.lights.new(name + "_data", light_type)
    data.energy = energy
    data.color = color
    if light_type == "AREA":
        data.shape = "DISK"
        data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    if target is not None:
        direction = Vector(target) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def add_camera(
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    lens: float,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    data = bpy.data.cameras.new(name + "_data")
    data.lens = lens
    data.sensor_width = 36
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    obj["review_target"] = list(target)
    collection.objects.link(obj)
    return obj


def add_steps(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
    count: int,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    start_vec = Vector(start)
    end_vec = Vector(end)
    direction = end_vec - start_vec
    heading = math.atan2(direction.y, direction.x)
    horizontal = math.hypot(direction.x, direction.y)
    tread = horizontal / count
    for index in range(count):
        t = (index + 0.5) / count
        center = start_vec.lerp(end_vec, t)
        height = max(0.16, direction.z * (index + 1) / count)
        add_box(
            f"{name}_{index:02d}",
            (tread * 1.08, width, height),
            (center.x, center.y, start_vec.z + height / 2),
            mat,
            collection,
            rotation_z=heading,
            bevel=0.03,
        )


def build_environment(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> None:
    env = collections["environment"]
    eco = collections["ecology"]
    add_box("V2_Seabed", (112, 86, 1.2), (0, 0, -1.1), mats["seabed"], env, bevel=0)
    add_cylinder("V2_CampusReefPlate", 46, 1.7, (0, 0, -0.2), mats["reef"], env, vertices=64, scale_xy=(1.0, 0.76))
    for index in range(30):
        angle = TAU * index / 30 + RNG.uniform(-0.08, 0.08)
        radius_x = RNG.uniform(42, 50)
        radius_y = RNG.uniform(31, 37)
        x = math.cos(angle) * radius_x
        y = math.sin(angle) * radius_y
        add_ico(
            f"V2_BoundaryReef_{index:02d}",
            (x, y, RNG.uniform(0.2, 1.2)),
            (RNG.uniform(3.5, 7.0), RNG.uniform(2.5, 5.5), RNG.uniform(2.0, 5.2)),
            mats["reef"],
            eco,
            subdivisions=1,
        )
    for index in range(34):
        angle = RNG.uniform(0, TAU)
        radius = RNG.uniform(12, 40)
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.72
        add_ico(
            f"V2_GardenRock_{index:02d}",
            (x, y, RNG.uniform(2.7, 4.0)),
            (RNG.uniform(0.4, 1.5), RNG.uniform(0.4, 1.3), RNG.uniform(0.5, 1.7)),
            mats["rock"],
            eco,
            subdivisions=1,
        )
    # The graybox keeps the water volume implicit. A full translucent ceiling
    # made top-down review unreadable and added dither noise without helping the
    # spatial audit. The local viewer supplies water-coloured fog instead.


def build_circulation(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> dict:
    circulation = collections["circulation"]
    add_cylinder("V2_GardenPlinth", 18.5, 0.7, (0, 0, 2.75), mats["foundation"], circulation, vertices=64, scale_xy=(1.0, 0.72))
    add_ellipse_band("V2_PrimaryVisitorLoop", (0, 0), (23.5, 17.5), 3.2, 3.2, 0.42, mats["floor"], circulation)
    add_ellipse_band("V2_GardenInnerBorder", (0, 0), (16.0, 11.5), 0.55, 3.12, 0.38, mats["bronze"], circulation)
    add_box("V2_ArrivalTerrace", (15, 11, 0.8), (-38, -27, 0.0), mats["floor"], circulation, rotation_z=0.12)
    add_box("V2_ArrivalThreshold", (6.5, 3.0, 0.45), (-33, -20.5, 0.65), mats["bronze"], circulation, rotation_z=0.55)

    arrival_ramp_xy = [
        (-38.0, -21.5),
        (-38.0, -11.0),
        (-35.0, -1.0),
        (-29.0, 7.5),
        (-21.0, 13.5),
        (-13.0, 16.0),
    ]
    cumulative = [0.0]
    for start_xy, end_xy in zip(arrival_ramp_xy, arrival_ramp_xy[1:]):
        cumulative.append(cumulative[-1] + math.dist(start_xy, end_xy))
    arrival_ramp = [
        (x, y, 0.45 + (3.20 - 0.45) * distance / cumulative[-1])
        for (x, y), distance in zip(arrival_ramp_xy, cumulative)
    ]
    add_path_strip("V2_AccessibleArrivalRamp", arrival_ramp, 3.2, 0.36, mats["floor"], circulation)
    for edge_sign in (-1, 1):
        edge_points = []
        for index, point in enumerate(arrival_ramp):
            previous = Vector(arrival_ramp[max(0, index - 1)])
            following = Vector(arrival_ramp[min(len(arrival_ramp) - 1, index + 1)])
            tangent = following - previous
            tangent.z = 0
            tangent.normalize()
            side = Vector((-tangent.y, tangent.x, 0)) * (1.62 * edge_sign)
            edge_points.append((point[0] + side.x, point[1] + side.y, point[2] + 0.75))
        add_tube(f"V2_ArrivalRampRail_{edge_sign:+d}", edge_points, 0.055, mats["bronze"], circulation)

    add_steps("V2_ArrivalGrandStair", (-34, -21, 0.4), (-20, -13.5, 3.2), 5.0, 16, mats["stone"], circulation)

    upper_route: list[tuple[float, float, float]] = []
    samples = 28
    start = math.radians(-78)
    end = math.radians(152)
    for index in range(samples):
        t = index / (samples - 1)
        angle = start + (end - start) * t
        upper_route.append((29.5 * math.cos(angle), 23.0 * math.sin(angle), 3.2 + 3.2 * t))
    add_path_strip("V2_RisingCrescentWalk", upper_route, 3.2, 0.38, mats["floor"], circulation)
    add_tube("V2_RisingCrescentGoldLine", [(x, y, z + 0.03) for x, y, z in upper_route], 0.07, mats["bronze"], circulation)

    bridge_points = [(-1.5, 18.0, 7.0), (8.0, 19.5, 7.1), (17.5, 20.0, 7.1), (23.5, 19.0, 6.8)]
    add_path_strip("V2_ArchiveSkyBridge", bridge_points, 2.4, 0.45, mats["floor"], circulation)
    for x, y, z in (bridge_points[0], bridge_points[-1]):
        add_cylinder(f"V2_BridgeSupport_{x:+.0f}", 0.65, z - 0.2, (x, y, (z - 0.2) / 2), mats["foundation"], circulation, vertices=16)

    def path_slope(points: list[tuple[float, float, float]]) -> float:
        maximum = 0.0
        for start_point, end_point in zip(points, points[1:]):
            horizontal = math.hypot(end_point[0] - start_point[0], end_point[1] - start_point[1])
            maximum = max(maximum, abs(end_point[2] - start_point[2]) / horizontal)
        return maximum

    return {
        "primary_loop_width_m": 3.2,
        "arrival_ramp_max_slope": path_slope(arrival_ramp),
        "rising_crescent_max_slope": path_slope(upper_route),
        "bridge_width_m": 2.4,
    }


def build_glass_gallery(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> None:
    gallery = collections["glass_gallery"]
    center = (-31.0, 1.5)
    base_z = 6.4
    width = 9.0
    length = 34.0
    add_box("V2_GlassGalleryFoundation", (11.0, 36.0, 1.2), (center[0], center[1], base_z - 0.6), mats["foundation"], gallery, bevel=0.28)
    add_box("V2_GlassGalleryFloor", (9.0, 34.0, 0.45), (center[0], center[1], base_z), mats["floor"], gallery)
    for side in (-1, 1):
        x = center[0] + side * width / 2
        add_box(f"V2_GlassGalleryWallBase_{side:+d}", (0.45, length, 1.1), (x, center[1], base_z + 0.55), mats["stone"], gallery)
        add_box(f"V2_GlassGalleryWallGlass_{side:+d}", (0.14, length - 1.2, 3.7), (x, center[1], base_z + 2.8), mats["glass"], gallery, bevel=0.02)
    add_vault_surface("V2_GlassGalleryVault", center, base_z + 4.65, width, length, 3.3, mats["glass"], gallery)
    for index, y in enumerate([center[1] - length / 2 + 1.0 + 2.65 * n for n in range(13)]):
        arch_points = []
        for step in range(17):
            angle = math.pi - math.pi * step / 16
            arch_points.append((center[0] + math.cos(angle) * width / 2, y, base_z + 4.65 + math.sin(angle) * 3.3))
        add_tube(f"V2_GlassVaultRib_{index:02d}", arch_points, 0.075, mats["bronze"], gallery)
    for side in (-1, 1):
        for index, y in enumerate([center[1] - 12.8, center[1] - 6.4, center[1], center[1] + 6.4, center[1] + 12.8]):
            x = center[0] + side * (width / 2 - 0.18)
            add_box(f"V2_GlassGalleryArtFrame_{side:+d}_{index}", (0.20, 3.6, 2.75), (x, y, base_z + 2.75), mats["bronze"], gallery, bevel=0.05)
            add_box(f"V2_GlassGalleryArt_{side:+d}_{index}", (0.12, 3.2, 2.35), (x - side * 0.08, y, base_z + 2.75), mats["art"], gallery, bevel=0.02)
    portal_y = center[1] - length / 2
    for side in (-1, 1):
        add_box(
            f"V2_GlassGalleryPortalPier_{side:+d}",
            (2.1, 0.8, 5.6),
            (center[0] + side * 3.95, portal_y, base_z + 2.8),
            mats["bronze"],
            gallery,
            bevel=0.25,
        )
    add_box("V2_GlassGalleryPortalLintel", (10.0, 0.8, 1.0), (center[0], portal_y, base_z + 5.1), mats["bronze"], gallery, bevel=0.22)
    add_box("V2_GlassGalleryDoor", (5.0, 0.25, 4.4), (center[0], center[1] - length / 2 - 0.35, base_z + 2.3), mats["glass"], gallery, bevel=0.12)
    add_text("V2_GlassGallerySign", "GLASS GALLERY", (center[0], center[1] - length / 2 - 0.55, base_z + 5.45), (math.pi / 2, 0, 0), 0.55, mats["gold_glow"], gallery)


def build_grand_archive(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> dict:
    archive = collections["archive"]
    center = (-12.0, 23.0)
    ground_z = 6.4
    lower_z = 2.2
    upper_z = 11.2
    radius = 13.0
    # Foundations and three usable floors.
    add_cylinder("V2_ArchiveFoundation", radius + 1.2, 1.2, (center[0], center[1], ground_z - 0.6), mats["foundation"], archive, vertices=64)
    add_cylinder("V2_ArchiveLowerFloor", 10.8, 0.45, (center[0], center[1], lower_z), mats["floor"], archive, vertices=64)
    add_cylinder("V2_ArchiveGroundFloor", 11.8, 0.45, (center[0], center[1], ground_z), mats["floor"], archive, vertices=64)
    add_ellipse_band("V2_ArchiveUpperRing", center, (10.7, 10.7), 3.0, upper_z, 0.42, mats["floor"], archive, segments=72)
    # Open a generous wedge centred on the south entrance. The previous east
    # opening left the signed entrance sitting in front of a solid wall.
    add_arc_wall("V2_ArchiveOuterDrum", center, radius, 1.0, ground_z, 6.2, math.radians(-20), math.radians(220), mats["stone"], archive)
    add_arc_wall("V2_ArchiveLowerWall", center, 11.3, 0.75, lower_z - 0.2, 4.2, math.radians(-20), math.radians(220), mats["foundation"], archive)
    add_dome("V2_ArchiveGlassDome", center, ground_z + 6.2, radius, 6.2, mats["glass"], archive, rings=9, segments=48)
    for rib in range(20):
        angle = TAU * rib / 20
        points = []
        for step in range(10):
            phi = (math.pi / 2) * step / 9
            points.append((center[0] + radius * math.sin(phi) * math.cos(angle), center[1] + radius * math.sin(phi) * math.sin(angle), ground_z + 6.2 + 6.2 * math.cos(phi)))
        add_tube(f"V2_ArchiveDomeRib_{rib:02d}", points, 0.07, mats["bronze"], archive)
    # Central water-light shaft and ring railings.
    add_cylinder("V2_ArchiveLightShaft", 1.45, 16.5, (center[0], center[1], 8.0), mats["light_glass"], archive, vertices=32)
    add_ellipse_band("V2_ArchiveGroundLightRim", center, (3.2, 3.2), 0.25, ground_z + 0.2, 0.28, mats["bronze"], archive, segments=48)
    add_ellipse_band("V2_ArchiveUpperRailing", center, (8.15, 8.15), 0.12, upper_z + 1.0, 1.05, mats["bronze"], archive, segments=64)
    add_path_strip("V2_ArchiveUpperBridge", [(center[0] - 8.0, center[1], upper_z + 0.18), (center[0] + 8.0, center[1], upper_z + 0.18)], 2.2, 0.32, mats["floor"], archive)
    # Four radial rooms read as a real museum program rather than one hall.
    chamber_specs = (
        ("North", (center[0], center[1] + 10.8), (8.0, 6.4, 5.0), 0.0),
        ("West", (center[0] - 10.8, center[1]), (6.4, 8.0, 5.0), 0.0),
        ("East", (center[0] + 10.8, center[1]), (6.4, 8.0, 5.0), 0.0),
        ("Rear", (center[0], center[1] + 5.4), (6.5, 5.5, 4.8), 0.0),
    )
    for label, chamber_center, size, rotation in chamber_specs:
        add_box(f"V2_Archive{label}ChamberFloor", (size[0], size[1], 0.35), (chamber_center[0], chamber_center[1], ground_z + 0.12), mats["floor"], archive, rotation_z=rotation)
        add_box(f"V2_Archive{label}ChamberBack", (size[0], 0.45, size[2]), (chamber_center[0], chamber_center[1] + size[1] / 2 - 0.22, ground_z + size[2] / 2), mats["stone"], archive, rotation_z=rotation)
    # Twelve structural columns define the rotunda and preserve sightlines.
    for index in range(12):
        angle = TAU * index / 12
        x = center[0] + math.cos(angle) * 8.9
        y = center[1] + math.sin(angle) * 8.9
        add_cylinder(f"V2_ArchiveColumn_{index:02d}", 0.32, 5.2, (x, y, ground_z + 2.6), mats["bronze"], archive, vertices=16)
    # Representative art surfaces around the ground and upper rings.
    for index in range(12):
        angle = TAU * index / 12
        x = center[0] + math.cos(angle) * 10.75
        y = center[1] + math.sin(angle) * 10.75
        rotation = angle + math.pi / 2
        add_box(f"V2_ArchiveGroundArt_{index:02d}", (2.5, 0.18, 2.2), (x, y, ground_z + 2.5), mats["art"], archive, rotation_z=rotation, bevel=0.03)
    for index in range(8):
        angle = TAU * index / 8 + math.pi / 8
        x = center[0] + math.cos(angle) * 9.5
        y = center[1] + math.sin(angle) * 9.5
        add_box(f"V2_ArchiveUpperArt_{index:02d}", (2.1, 0.16, 1.8), (x, y, upper_z + 2.0), mats["art"], archive, rotation_z=angle + math.pi / 2, bevel=0.03)
    # Two explicit stair flights visibly land on the upper ring and lower floor.
    add_steps("V2_ArchiveUpperStairL", (center[0] - 6.5, center[1] - 2.0, ground_z + 0.2), (center[0] - 6.5, center[1] + 5.5, upper_z), 2.1, 18, mats["stone"], archive)
    add_steps("V2_ArchiveLowerStairR", (center[0] + 5.8, center[1] + 4.8, lower_z + 0.2), (center[0] + 5.8, center[1] - 2.5, ground_z), 2.1, 18, mats["stone"], archive)
    # Lower archive furniture keeps the level legible as storage/conservation.
    for side in (-1, 1):
        for index in range(4):
            add_box(f"V2_ArchiveShelf_{side:+d}_{index}", (0.65, 2.6, 2.2), (center[0] + side * 7.8, center[1] - 5.0 + index * 3.2, lower_z + 1.15), mats["bronze"], archive, bevel=0.04)
    add_box("V2_ArchiveConservationTable", (5.0, 1.8, 0.85), (center[0], center[1] + 5.8, lower_z + 0.55), mats["warm"], archive, bevel=0.12)
    # Entrance portal and embedded identity.
    portal_y = center[1] - radius + 0.5
    for side in (-1, 1):
        add_box(
            f"V2_ArchiveEntrancePier_{side:+d}",
            (1.5, 1.0, 6.1),
            (center[0] + side * 3.25, portal_y, ground_z + 3.05),
            mats["bronze"],
            archive,
            bevel=0.28,
        )
    add_box("V2_ArchiveEntranceLintel", (8.0, 1.0, 1.0), (center[0], portal_y, ground_z + 5.6), mats["bronze"], archive, bevel=0.25)
    add_box("V2_ArchiveEntranceGlass", (5.2, 0.22, 4.5), (center[0], center[1] - radius - 0.05, ground_z + 2.35), mats["glass"], archive, bevel=0.12)
    add_text("V2_ArchiveSign", "GRAND TIDE ARCHIVE", (center[0], center[1] - radius - 0.22, ground_z + 5.75), (math.pi / 2, 0, 0), 0.52, mats["gold_glow"], archive)
    return {
        "center": [center[0], center[1], ground_z],
        "diameter_m": radius * 2,
        "height_m": 18.6,
        "levels": {"lower": lower_z, "ground": ground_z, "upper": upper_z},
        "representative_art_capacity": 20,
    }


def build_pavilion(
    label: str,
    center: tuple[float, float],
    base_z: float,
    radius: float,
    collections: dict[str, bpy.types.Collection],
    mats: dict[str, bpy.types.Material],
) -> None:
    pavilions = collections["pavilions"]
    add_cylinder(f"V2_{label}Foundation", radius + 1.0, 0.9, (center[0], center[1], base_z - 0.45), mats["foundation"], pavilions, vertices=40)
    add_cylinder(f"V2_{label}Floor", radius, 0.35, (center[0], center[1], base_z), mats["floor"], pavilions, vertices=40)
    add_arc_wall(f"V2_{label}Drum", center, radius, 0.65, base_z, 4.6, math.radians(-50), math.radians(230), mats["stone"], pavilions, segments=40)
    add_dome(f"V2_{label}Dome", center, base_z + 4.6, radius, 3.0, mats["glass"], pavilions, rings=6, segments=32)
    for index in range(10):
        angle = TAU * index / 10
        x = center[0] + math.cos(angle) * (radius - 0.3)
        y = center[1] + math.sin(angle) * (radius - 0.3)
        add_cylinder(f"V2_{label}Column_{index:02d}", 0.22, 4.5, (x, y, base_z + 2.25), mats["bronze"], pavilions, vertices=12)
    for index, angle in enumerate((math.radians(70), math.radians(125), math.radians(235), math.radians(290))):
        x = center[0] + math.cos(angle) * (radius - 0.55)
        y = center[1] + math.sin(angle) * (radius - 0.55)
        add_box(f"V2_{label}Art_{index}", (2.0, 0.16, 2.3), (x, y, base_z + 2.3), mats["art"], pavilions, rotation_z=angle + math.pi / 2, bevel=0.03)
    portal_y = center[1] - radius + 0.25
    for side in (-1, 1):
        add_box(f"V2_{label}PortalPier_{side:+d}", (1.0, 0.8, 4.8), (center[0] + side * 1.8, portal_y, base_z + 2.4), mats["bronze"], pavilions, bevel=0.20)
    add_box(f"V2_{label}PortalLintel", (4.6, 0.8, 0.8), (center[0], portal_y, base_z + 4.4), mats["bronze"], pavilions, bevel=0.18)
    add_text(f"V2_{label}Sign", label.upper().replace("_", " "), (center[0], center[1] - radius - 0.22, base_z + 4.35), (math.pi / 2, 0, 0), 0.36, mats["gold_glow"], pavilions)


def build_pavilions(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> list[dict]:
    specs = [
        ("RECOMPOSITION", (25.0, -10.0), 3.2, 5.7),
        ("MATERIAL", (31.0, 5.0), 4.8, 6.2),
        ("MOOD_OBJECT", (24.0, 21.0), 6.4, 6.8),
    ]
    for label, center, base_z, radius in specs:
        build_pavilion(label, center, base_z, radius, collections, mats)
    return [
        {"id": label.lower(), "center": [center[0], center[1], base_z], "diameter_m": radius * 2}
        for label, center, base_z, radius in specs
    ]


def build_garden(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> None:
    garden = collections["ecology"]
    center_z = 3.45
    add_cylinder("V2_GardenSculpturePlinth", 3.0, 0.65, (0, 0, center_z), mats["foundation"], garden, vertices=32)
    add_cylinder("V2_GardenSculptureStem", 0.45, 5.0, (0, 0, center_z + 2.7), mats["bronze"], garden, vertices=16)
    bpy.ops.mesh.primitive_torus_add(major_radius=2.0, minor_radius=0.12, major_segments=32, minor_segments=8, location=(0, 0, center_z + 5.2), rotation=(math.pi / 2, 0, 0))
    torus = bpy.context.object
    torus.name = "V2_GardenSculptureHalo"
    torus.data.materials.append(mats["bronze"])
    move_to(torus, garden)
    add_ico("V2_GardenSculptureCore", (0, 0, center_z + 5.2), (0.9, 0.9, 1.25), mats["light_glass"], garden, subdivisions=2)
    # Lighting is carried by real lamps. A giant translucent cylinder here
    # blocked the visitor-loop camera and read as an opaque tank in the GLB.
    for index in range(20):
        angle = TAU * index / 20 + RNG.uniform(-0.12, 0.12)
        radius = RNG.uniform(7.5, 14.5)
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.72
        height = RNG.uniform(0.8, 2.2)
        add_cylinder(f"V2_CoralStem_{index:02d}", 0.12 + height * 0.06, height, (x, y, 3.35 + height / 2), mats["coral_warm" if index % 3 == 0 else "coral_cool"], garden, vertices=8)


def configure_scene(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 32
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.use_nodes = True
    background = next(node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.006, 0.08, 0.13, 1.0)
    background.inputs["Strength"].default_value = 0.52

    lighting = collections["lighting"]
    add_light("V2_SurfaceSun", "AREA", (-22, -18, 32), (0.48, 0.86, 1.0), 3200, lighting, size=20, target=(0, 0, 3))
    add_light("V2_GardenFill", "AREA", (8, -8, 20), (0.24, 0.66, 0.82), 1900, lighting, size=16, target=(0, 0, 4))
    add_light("V2_ArchiveWarmKey", "AREA", (-12, 18, 18), (1.0, 0.62, 0.28), 1450, lighting, size=12, target=(-12, 23, 8))
    add_light("V2_GlassGalleryWarm", "AREA", (-31, 2, 14), (1.0, 0.68, 0.34), 1100, lighting, size=10, target=(-31, 2, 8))
    for index, location in enumerate(((25, -10, 10), (31, 5, 12), (24, 21, 14))):
        add_light(f"V2_PavilionWarm_{index}", "POINT", location, (1.0, 0.60, 0.30), 760, lighting)
    add_light("V2_LightShaftGlow", "POINT", (-12, 23, 9), (0.16, 0.82, 1.0), 850, lighting)

    cameras = collections["cameras"]
    specs = [
        (1, "V2_HERO", add_camera("V2_HeroCamera", (-64, -50, 34), (0, 5, 6), 48, cameras)),
        (20, "V2_PLAN", add_camera("V2_PlanCamera", (0, -6, 130), (0, 1, 2.2), 32, cameras)),
        (40, "V2_LOOP", add_camera("V2_LoopCamera", (-18, -16, 6.0), (16, -3, 6.0), 40, cameras)),
        (60, "V2_ARCHIVE_CUTAWAY", add_camera("V2_ArchiveCutawayCamera", (12, -16, 22), (-12, 23, 8.5), 52, cameras)),
    ]
    for frame, label, camera in specs:
        marker = scene.timeline_markers.new(label, frame=frame)
        marker.camera = camera
    scene.frame_start = 1
    scene.frame_end = 60
    scene.frame_set(1)
    scene.camera = specs[0][2]
    return [camera for _, _, camera in specs]


def evaluated_triangles() -> int:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return total


VIEWER_HTML = """<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Atlantis Gallery V2 · Local Graybox</title>
<style>
:root{color-scheme:dark;--blue:#062a42;--cyan:#49b9d3;--gold:#e8b54a;--cream:#f6edda}*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:var(--blue);font-family:ui-serif,Georgia,serif;color:var(--cream)}canvas{display:block}.hud{position:fixed;z-index:3;inset:24px 26px auto 26px;display:flex;justify-content:space-between;align-items:flex-start;pointer-events:none}.brand{max-width:430px;padding:18px 20px;background:rgba(3,30,48,.72);border:1px solid rgba(232,181,74,.36);backdrop-filter:blur(14px)}h1{font-size:24px;margin:0 0 8px;color:#ffe29a}.brand p{margin:0;color:rgba(246,237,218,.72);line-height:1.5;font-family:system-ui,sans-serif;font-size:13px}.buttons{display:flex;gap:8px;pointer-events:auto}.buttons button{appearance:none;border:1px solid rgba(255,226,154,.38);background:rgba(4,36,63,.76);color:var(--cream);padding:10px 14px;border-radius:99px;cursor:pointer}.buttons button:hover,.buttons button.active{background:var(--gold);color:#062a42}.status{position:fixed;z-index:3;left:26px;bottom:22px;background:rgba(3,30,48,.72);border-left:2px solid var(--gold);padding:10px 14px;font:12px/1.5 system-ui,sans-serif;color:rgba(246,237,218,.76)}.warning{position:fixed;inset:auto 26px 22px auto;z-index:3;font:12px system-ui,sans-serif;color:rgba(246,237,218,.58)}
</style></head><body><div class=\"hud\"><div class=\"brand\"><h1>Atlantis Gallery V2 · Structural Graybox</h1><p>本地评审：月牙园区、3.2 m 环路、玻璃长廊、三层潮汐档案馆与三座阶梯展馆。此版本不会部署线上。</p></div><div class=\"buttons\"><button data-view=\"hero\" class=\"active\">园区</button><button data-view=\"plan\">总平面</button><button data-view=\"loop\">步行环路</button><button data-view=\"archive\">档案馆</button></div></div><div class=\"status\" id=\"status\">正在读取本地 GLB…</div><div class=\"warning\">拖动旋转 · 滚轮缩放 · 右键平移</div><script type=\"module\">
import * as THREE from 'https://esm.sh/three@0.160.0';
import {GLTFLoader} from 'https://esm.sh/three@0.160.0/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js';
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.08;document.body.append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x05283d);scene.fog=new THREE.FogExp2(0x08364b,.0065);const camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.1,300);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.07;
scene.add(new THREE.HemisphereLight(0x74d6ed,0x03151f,2.2));const sun=new THREE.DirectionalLight(0xb9efff,3.2);sun.position.set(-25,45,30);scene.add(sun);const warm=new THREE.PointLight(0xffa75c,58,90,1.3);warm.position.set(-12,12,-23);scene.add(warm);
const views={hero:{p:[-64,34,50],t:[0,6,-5]},plan:{p:[0,130,6],t:[0,2.2,-1]},loop:{p:[-18,6,16],t:[16,6,3]},archive:{p:[12,22,16],t:[-12,8.5,-23]}};
function view(id){const v=views[id];camera.position.set(...v.p);controls.target.set(...v.t);controls.update();document.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.view===id))}document.querySelectorAll('button').forEach(b=>b.onclick=()=>view(b.dataset.view));view('hero');
new GLTFLoader().load('./atlantis-gallery-master-v2-graybox.glb',g=>{scene.add(g.scene);document.getElementById('status').textContent='V2 灰盒已加载 · 仅本地预览';},undefined,e=>{document.getElementById('status').textContent='GLB 加载失败：请使用桌面 command 启动本地服务器';console.error(e)});
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera)});
</script></body></html>"""


def write_outputs(
    repo: Path,
    cameras: list[bpy.types.Object],
    route_audit: dict,
    archive_audit: dict,
    pavilions: list[dict],
    *,
    skip_renders: bool,
) -> tuple[Path, Path, Path]:
    scene = bpy.context.scene
    working_dir = repo / "assets/gallery/blender/working"
    output_dir = repo / "output/gallery/master-v2-graybox"
    working_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = working_dir / "atlantis-gallery-master-v2-graybox.blend"
    glb_path = output_dir / "atlantis-gallery-master-v2-graybox.glb"
    viewer_path = output_dir / "index.html"

    scene["gallery_version"] = "2.0-graybox"
    scene["publication_state"] = "local-only"
    scene["source_of_truth"] = str(Path(__file__).resolve())
    scene["spatial_contract"] = "crescent campus + 3.2m loop + grand three-level archive"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    # Export a compact all-in-one review GLB. Production V2 will be split into
    # proximity-loaded modules after the graybox is approved.
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_visible=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )
    viewer_path.write_text(VIEWER_HTML, encoding="utf-8")

    triangle_count = evaluated_triangles()
    audit = {
        "version": "2.0-graybox",
        "publication_state": "local-only",
        "blend": str(blend_path),
        "glb": str(glb_path),
        "glb_bytes": glb_path.stat().st_size,
        "objects": len(scene.objects),
        "mesh_objects": sum(obj.type == "MESH" for obj in scene.objects),
        "curve_objects": sum(obj.type in {"CURVE", "FONT"} for obj in scene.objects),
        "evaluated_triangles": triangle_count,
        "materials": len(bpy.data.materials),
        "cameras": [camera.name for camera in cameras],
        "campus_envelope_m": [95, 70],
        "circulation": route_audit,
        "grand_archive": archive_audit,
        "terraced_pavilions": pavilions,
        "gates": {
            "primary_loop_width_at_least_3_2m": route_audit["primary_loop_width_m"] >= 3.2,
            "arrival_ramp_at_most_1_in_12": route_audit["arrival_ramp_max_slope"] <= 1 / 12,
            "rising_crescent_at_most_1_in_12": route_audit["rising_crescent_max_slope"] <= 1 / 12,
            "three_archive_levels": len(archive_audit["levels"]) == 3,
            "four_review_cameras": len(cameras) == 4,
            "graybox_under_160k_triangles": triangle_count <= 160_000,
            "graybox_glb_under_20mb": glb_path.stat().st_size <= 20_000_000,
        },
    }
    audit["passed"] = all(audit["gates"].values())
    audit_path = output_dir / "audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not audit["passed"]:
        failed = [name for name, passed in audit["gates"].items() if not passed]
        raise RuntimeError("V2 graybox audit failed: " + ", ".join(failed))

    if not skip_renders:
        render_specs = [
            (cameras[0], output_dir / "01-campus-hero.png"),
            (cameras[1], output_dir / "02-campus-plan.png"),
            (cameras[2], output_dir / "03-visitor-loop.png"),
            (cameras[3], output_dir / "04-grand-archive-cutaway.png"),
        ]
        marker_specs = [(marker.name, marker.frame, marker.camera) for marker in scene.timeline_markers]
        for marker in list(scene.timeline_markers):
            scene.timeline_markers.remove(marker)
        for camera, render_path in render_specs:
            scene.camera = camera
            scene.render.filepath = str(render_path)
            bpy.ops.render.render(write_still=True)
            print(f"V2_RENDER={render_path}")
        for name, frame, camera in marker_specs:
            marker = scene.timeline_markers.new(name, frame=frame)
            marker.camera = camera
    scene.frame_set(1)
    scene.camera = cameras[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    return blend_path, glb_path, audit_path


def build(repo: Path, *, skip_renders: bool) -> None:
    clear_scene()
    collections = {
        "environment": make_collection("00_V2_ENVIRONMENT", "COLOR_04"),
        "circulation": make_collection("01_V2_CIRCULATION", "COLOR_03"),
        "glass_gallery": make_collection("02_V2_GLASS_GALLERY", "COLOR_05"),
        "archive": make_collection("03_V2_GRAND_TIDE_ARCHIVE", "COLOR_02"),
        "pavilions": make_collection("04_V2_TERRACED_PAVILIONS", "COLOR_06"),
        "ecology": make_collection("05_V2_GARDEN_ECOLOGY", "COLOR_01"),
        "lighting": make_collection("06_V2_LIGHTING", "COLOR_07"),
        "cameras": make_collection("07_V2_REVIEW_CAMERAS", "COLOR_08"),
    }
    mats = {
        "stone": material("V2_PaleLimestone", (0.52, 0.69, 0.70, 1), roughness=0.72),
        "foundation": material("V2_DeepTealFoundation", (0.025, 0.13, 0.17, 1), roughness=0.82),
        "floor": material("V2_SiltMosaicFloor", (0.28, 0.46, 0.48, 1), roughness=0.66),
        "bronze": material("V2_OxidizedBronze", (0.34, 0.24, 0.09, 1), metallic=0.82, roughness=0.32),
        "glass": material("V2_ProtectedGlass", (0.08, 0.45, 0.57, 0.28), roughness=0.12, transmission=0.72),
        "light_glass": material("V2_WaterLightGlass", (0.05, 0.72, 0.88, 0.40), roughness=0.18, transmission=0.48, emission=(0.04, 0.72, 0.94, 1), emission_strength=1.7),
        "water": material("V2_WaterCeiling", (0.03, 0.42, 0.58, 0.22), roughness=0.18, transmission=0.58),
        "shaft": material("V2_SunShaft", (0.13, 0.72, 0.92, 0.08), roughness=0.2, transmission=0.65, emission=(0.05, 0.55, 0.78, 1), emission_strength=0.32),
        "seabed": material("V2_Seabed", (0.025, 0.13, 0.16, 1), roughness=0.94),
        "reef": material("V2_ReefRock", (0.022, 0.10, 0.12, 1), roughness=0.90),
        "rock": material("V2_GardenRock", (0.06, 0.18, 0.19, 1), roughness=0.88),
        "warm": material("V2_ArchiveWorkbench", (0.34, 0.21, 0.12, 1), roughness=0.55),
        "art": material("V2_ArtworkPlaceholder", (0.58, 0.30, 0.20, 1), roughness=0.42, emission=(0.50, 0.19, 0.08, 1), emission_strength=0.25),
        "gold_glow": material("V2_GoldWayfinding", (0.82, 0.54, 0.13, 1), metallic=0.48, roughness=0.28, emission=(0.95, 0.55, 0.12, 1), emission_strength=1.4),
        "coral_warm": material("V2_CoralWarm", (0.55, 0.13, 0.08, 1), roughness=0.68),
        "coral_cool": material("V2_CoralCool", (0.05, 0.38, 0.38, 1), roughness=0.70),
    }
    build_environment(collections, mats)
    route_audit = build_circulation(collections, mats)
    build_glass_gallery(collections, mats)
    archive_audit = build_grand_archive(collections, mats)
    pavilion_audit = build_pavilions(collections, mats)
    build_garden(collections, mats)
    cameras = configure_scene(collections, mats)
    blend_path, glb_path, audit_path = write_outputs(
        repo,
        cameras,
        route_audit,
        archive_audit,
        pavilion_audit,
        skip_renders=skip_renders,
    )
    print(f"V2_BLEND={blend_path}")
    print(f"V2_GLB={glb_path}")
    print(f"V2_AUDIT={audit_path}")


if __name__ == "__main__":
    arguments = cli_args()
    build(Path(arguments.repo).expanduser().resolve(), skip_renders=arguments.skip_renders)
