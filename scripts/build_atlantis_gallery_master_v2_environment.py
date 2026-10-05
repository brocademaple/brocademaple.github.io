#!/usr/bin/env python3
"""Build the local-only Atlantis Gallery Master V2.2 environment pass.

The script develops the approved lightweight graybox into a reproducible
architectural review model:

- asymmetric crescent campus instead of the V1 axial palace;
- one continuous 3.2 m visitor loop plus accessible rising routes;
- a large three-level Grand Tide Archive;
- one detailed glass-vault gallery and three distinct terraced pavilions;
- rendered seabed, layered reefs, caustics, water haze and light shafts;
- reef-integrated retaining walls, colonnades, lanterns, kelp and warm rooms;
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
RNG = random.Random(20260821)


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


def procedural_ground_material(name: str, *, reef: bool = False) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 7.5 if reef else 4.2
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    stops = (
        ((0.018, 0.07, 0.09, 1), 0.18),
        ((0.035, 0.18, 0.20, 1), 0.45),
        ((0.08, 0.32, 0.34, 1), 0.70),
        ((0.20, 0.45, 0.42, 1), 0.90),
    ) if reef else (
        ((0.018, 0.10, 0.14, 1), 0.10),
        ((0.045, 0.23, 0.27, 1), 0.42),
        ((0.18, 0.43, 0.43, 1), 0.68),
        ((0.42, 0.62, 0.55, 1), 0.90),
    )
    for index, (color, position) in enumerate(stops):
        element = ramp.color_ramp.elements[0] if index == 0 else ramp.color_ramp.elements.new(position)
        element.position = position
        element.color = color
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.48 if reef else 0.24
    bump.inputs["Distance"].default_value = 0.32
    bsdf.inputs["Roughness"].default_value = 0.86 if reef else 0.78
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def caustic_material(name: str, color: tuple[float, float, float, float], strength: float) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    mix = nodes.new("ShaderNodeMixShader")
    texcoord = nodes.new("ShaderNodeTexCoord")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.feature = "DISTANCE_TO_EDGE"
    voronoi.distance = "EUCLIDEAN"
    voronoi.inputs["Scale"].default_value = 5.8
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.028
    # Keep the network faint enough to read as reflected water light, not as
    # a second graphic layer pasted across the ground.
    ramp.color_ramp.elements[0].color = (0.18, 0.18, 0.18, 1)
    ramp.color_ramp.elements[1].position = 0.105
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    links.new(texcoord.outputs["Generated"], voronoi.inputs["Vector"])
    links.new(voronoi.outputs["Distance"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
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


def add_cone(
    name: str,
    radius_bottom: float,
    radius_top: float,
    depth: float,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    vertices: int = 24,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius_bottom,
        radius2=radius_top,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
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


def add_classical_column(
    name: str,
    location: tuple[float, float, float],
    height: float,
    shaft_radius: float,
    shaft_mat: bpy.types.Material,
    trim_mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    x, y, base_z = location
    add_cylinder(f"{name}_Base", shaft_radius * 1.55, 0.28, (x, y, base_z + 0.14), trim_mat, collection, vertices=20)
    add_cylinder(f"{name}_Foot", shaft_radius * 1.25, 0.26, (x, y, base_z + 0.38), shaft_mat, collection, vertices=20)
    add_cylinder(f"{name}_Shaft", shaft_radius, height - 0.78, (x, y, base_z + 0.39 + (height - 0.78) / 2), shaft_mat, collection, vertices=20)
    add_cylinder(f"{name}_Capital", shaft_radius * 1.45, 0.34, (x, y, base_z + height - 0.22), trim_mat, collection, vertices=20)
    add_box(f"{name}_Abacus", (shaft_radius * 3.35, shaft_radius * 3.35, 0.22), (x, y, base_z + height - 0.02), trim_mat, collection, bevel=0.05)


def add_arch_frame_y(
    name: str,
    center_x: float,
    y: float,
    base_z: float,
    half_width: float,
    spring_z: float,
    radius: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    add_box(f"{name}_L", (radius * 2.0, radius * 2.0, spring_z - base_z), (center_x - half_width, y, (base_z + spring_z) / 2), mat, collection, bevel=radius * 0.45)
    add_box(f"{name}_R", (radius * 2.0, radius * 2.0, spring_z - base_z), (center_x + half_width, y, (base_z + spring_z) / 2), mat, collection, bevel=radius * 0.45)
    points = []
    for index in range(17):
        angle = math.pi - math.pi * index / 16
        points.append((center_x + math.cos(angle) * half_width, y, spring_z + math.sin(angle) * half_width))
    add_tube(f"{name}_Arch", points, radius, mat, collection)


def add_lantern(
    name: str,
    location: tuple[float, float, float],
    height: float,
    mats: dict[str, bpy.types.Material],
    collection: bpy.types.Collection,
) -> None:
    x, y, base_z = location
    add_cylinder(f"{name}_Post", 0.10, height, (x, y, base_z + height / 2), mats["bronze"], collection, vertices=12)
    add_cylinder(f"{name}_Crown", 0.22, 0.18, (x, y, base_z + height + 0.05), mats["bronze"], collection, vertices=16)
    add_ico(f"{name}_Glow", (x, y, base_z + height + 0.33), (0.22, 0.22, 0.34), mats["window"], collection, subdivisions=2)
    add_cone(f"{name}_Cap", 0.24, 0.02, 0.24, (x, y, base_z + height + 0.67), mats["bronze"], collection, vertices=16)


def add_plane(
    name: str,
    size: tuple[float, float],
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    *,
    rotation_z: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location, rotation=(0, 0, rotation_z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size[0] / 2, size[1] / 2, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return move_to(obj, collection)


def add_sea_fan(
    name: str,
    location: tuple[float, float, float],
    height: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    x, y, z = location
    for branch in range(-4, 5):
        spread = branch / 4
        points = []
        for step in range(6):
            t = step / 5
            points.append(
                (
                    x + spread * height * 0.50 * t + math.sin(t * math.pi) * spread * 0.18,
                    y + math.sin(t * math.pi) * 0.12,
                    z + height * t,
                )
            )
        add_tube(f"{name}_Branch_{branch:+d}", points, 0.035 + 0.018 * (1 - abs(spread)), mat, collection)
    for level in (0.34, 0.58, 0.78):
        half_width = height * 0.50 * level
        add_tube(
            f"{name}_Cross_{int(level * 100)}",
            [(x - half_width, y, z + height * level), (x, y + 0.08, z + height * (level + 0.06)), (x + half_width, y, z + height * level)],
            0.028,
            mat,
            collection,
        )


def add_fish_school(
    name: str,
    center: tuple[float, float, float],
    count: int,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    cx, cy, cz = center
    for index in range(count):
        x = cx + RNG.uniform(-5.5, 5.5)
        y = cy + RNG.uniform(-2.4, 2.4)
        z = cz + RNG.uniform(-1.2, 1.2)
        fish = add_ico(
            f"{name}_Fish_{index:02d}",
            (x, y, z),
            (RNG.uniform(0.26, 0.45), RNG.uniform(0.08, 0.13), RNG.uniform(0.11, 0.18)),
            mat,
            collection,
            subdivisions=1,
        )
        fish.rotation_euler.z = RNG.uniform(-0.28, 0.28)


def build_environment(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> None:
    env = collections["environment"]
    eco = collections["ecology"]
    add_box("V2_Seabed", (160, 124, 1.2), (0, 0, -1.1), mats["seabed"], env, bevel=0)
    add_cylinder("V2_CampusReefPlate", 46, 1.7, (0, 0, -0.2), mats["reef"], env, vertices=64, scale_xy=(1.0, 0.76))
    # Broad sediment shelves break the single dark ground plane and lead the
    # eye toward the museum rather than competing with it.
    sediment_specs = (
        ((-34, -26, -0.08), (24, 13, 0.34), 0.12),
        ((28, -25, -0.10), (30, 11, 0.30), -0.16),
        ((39, 15, 0.02), (18, 16, 0.38), 0.22),
        ((-37, 24, 0.02), (22, 13, 0.42), -0.14),
    )
    for index, (location, size, rotation) in enumerate(sediment_specs):
        add_box(
            f"V2_SedimentShelf_{index:02d}",
            size,
            location,
            mats["sand" if index % 2 == 0 else "silt"],
            env,
            rotation_z=rotation,
            bevel=1.1,
        )
    add_plane("V2_SeabedCausticsA", (96, 68), (0, 0, 0.48), mats["caustic_cool"], env, rotation_z=0.08)
    add_plane("V2_SeabedCausticsB", (78, 54), (5, 2, 0.50), mats["caustic_gold"], env, rotation_z=-0.18)
    add_plane("V2_GardenCaustics", (34, 24), (0, 0, 3.52), mats["caustic_cool"], env, rotation_z=0.31)
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
    # Reef terraces make the campus feel excavated from a site instead of laid
    # on a flat disk. The gaps remain wide enough to preserve the audited route.
    terrace_specs = (
        ((-36, 22), (20, 7, 2.6), -0.18),
        ((35, 25), (18, 8, 3.0), 0.15),
        ((38, -18), (16, 9, 2.4), -0.22),
        ((-8, -32), (28, 6, 1.8), 0.04),
    )
    for index, (location, size, rotation) in enumerate(terrace_specs):
        add_box(
            f"V2_ReefTerrace_{index:02d}",
            size,
            (location[0], location[1], size[2] / 2 - 0.15),
            mats["reef_mid"],
            env,
            rotation_z=rotation,
            bevel=0.7,
        )
    for index in range(26):
        angle = TAU * index / 26 + RNG.uniform(-0.1, 0.1)
        radius = RNG.uniform(28, 44)
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.73
        height = RNG.uniform(2.4, 6.2)
        add_cone(
            f"V2_KelpStem_{index:02d}",
            RNG.uniform(0.14, 0.28),
            RNG.uniform(0.03, 0.08),
            height,
            (x, y, 1.1 + height / 2),
            mats["kelp"],
            eco,
            vertices=10,
        )
        if index % 2 == 0:
            add_ico(
                f"V2_KelpLeaf_{index:02d}",
                (x + RNG.uniform(-0.4, 0.4), y + RNG.uniform(-0.4, 0.4), 1.0 + height * 0.75),
                (0.18, 0.65, 0.12),
                mats["kelp_light"],
                eco,
                subdivisions=1,
            )
    for index in range(12):
        angle = TAU * index / 12 + 0.22
        radius = 34 + (index % 3) * 3.5
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.72
        add_sea_fan(
            f"V2_SeaFan_{index:02d}",
            (x, y, 1.0),
            RNG.uniform(2.1, 4.6),
            mats["coral_gold" if index % 4 == 0 else "sea_fan"],
            eco,
        )
    coral_cluster_specs = (
        ((-41, -12), "coral_warm"),
        ((-27, 28), "coral_gold"),
        ((35, 26), "coral_warm"),
        ((43, -8), "coral_cool"),
        ((18, -31), "coral_gold"),
    )
    for cluster, ((cx, cy), mat_key) in enumerate(coral_cluster_specs):
        for branch in range(9):
            height = RNG.uniform(1.2, 3.8)
            add_cone(
                f"V2_OuterCoral_{cluster:02d}_{branch:02d}",
                0.18 + height * 0.05,
                0.025,
                height,
                (cx + RNG.uniform(-2.0, 2.0), cy + RNG.uniform(-1.5, 1.5), 0.9 + height / 2),
                mats[mat_key if branch % 3 else "coral_cool"],
                eco,
                vertices=9,
            )
    add_fish_school("V2_FishSchoolWest", (-24, -4, 13.5), 14, mats["fish"], eco)
    add_fish_school("V2_FishSchoolEast", (31, 15, 16.0), 18, mats["fish"], eco)
    add_fish_school("V2_FishSchoolDistant", (4, 34, 20.0), 12, mats["fish_gold"], eco)
    for index, (x, y, height) in enumerate(((-39, 7, 4.5), (42, 5, 5.2), (-6, -34, 3.8))):
        add_cylinder(f"V2_RuinColumnBase_{index}", 0.82, 0.4, (x, y, 1.1), mats["stone"], eco, vertices=20)
        column = add_cylinder(f"V2_RuinColumn_{index}", 0.55, height, (x, y, 1.3 + height / 2), mats["stone_dark"], eco, vertices=20)
        column.rotation_euler = (RNG.uniform(-0.12, 0.12), RNG.uniform(-0.18, 0.18), RNG.uniform(-0.2, 0.2))
    # Water atmosphere is carried by lighting and color. Visible cone meshes
    # were deliberately removed because their transparency dithered in Eevee.


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

    # A bronze rhythm ties the asymmetric campus together without making the
    # visitor loop feel fenced in: low outer rails, mosaic ticks and lanterns.
    outer_rail_points = []
    for index in range(65):
        angle = TAU * index / 64
        outer_rail_points.append((24.0 * math.cos(angle), 18.0 * math.sin(angle), 4.05))
    add_tube("V2_VisitorLoopOuterRail", outer_rail_points, 0.065, mats["bronze"], circulation)
    for index in range(24):
        angle = TAU * index / 24
        x = 24.0 * math.cos(angle)
        y = 18.0 * math.sin(angle)
        add_cylinder(f"V2_LoopBaluster_{index:02d}", 0.07, 0.88, (x, y, 3.62), mats["bronze"], circulation, vertices=10)
        if index % 4 == 0:
            add_lantern(f"V2_LoopLantern_{index:02d}", (x, y, 3.2), 1.1, mats, circulation)
    for index in range(36):
        angle = TAU * index / 36
        add_box(
            f"V2_LoopMosaicTick_{index:02d}",
            (0.18, 1.15, 0.06),
            (21.8 * math.cos(angle), 16.1 * math.sin(angle), 3.43),
            mats["mosaic"],
            circulation,
            rotation_z=angle,
            bevel=0.02,
        )
    for edge_sign in (-1, 1):
        bridge_edge = []
        for index, point in enumerate(bridge_points):
            previous = Vector(bridge_points[max(0, index - 1)])
            following = Vector(bridge_points[min(len(bridge_points) - 1, index + 1)])
            tangent = following - previous
            tangent.z = 0
            tangent.normalize()
            side = Vector((-tangent.y, tangent.x, 0)) * (1.23 * edge_sign)
            bridge_edge.append((point[0] + side.x, point[1] + side.y, point[2] + 0.82))
        add_tube(f"V2_ArchiveBridgeRail_{edge_sign:+d}", bridge_edge, 0.055, mats["bronze"], circulation)

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
        for bay in range(8):
            y = center[1] - length / 2 + 2.15 + bay * 4.25
            add_box(
                f"V2_GlassGalleryWarmBay_{side:+d}_{bay:02d}",
                (0.08, 3.15, 2.65),
                (x - side * 0.11, y, base_z + 2.8),
                mats["window"],
                gallery,
                bevel=0.03,
            )
        for bay in range(9):
            y = center[1] - length / 2 + bay * (length / 8)
            add_classical_column(
                f"V2_GlassGalleryPilaster_{side:+d}_{bay:02d}",
                (center[0] + side * (width / 2 + 0.22), y, base_z),
                4.85,
                0.18,
                mats["stone"],
                mats["bronze"],
                gallery,
            )
    add_vault_surface("V2_GlassGalleryVault", center, base_z + 4.65, width, length, 3.3, mats["glass"], gallery)
    for index, y in enumerate([center[1] - length / 2 + 1.0 + 2.65 * n for n in range(13)]):
        arch_points = []
        for step in range(17):
            angle = math.pi - math.pi * step / 16
            arch_points.append((center[0] + math.cos(angle) * width / 2, y, base_z + 4.65 + math.sin(angle) * 3.3))
        add_tube(f"V2_GlassVaultRib_{index:02d}", arch_points, 0.075, mats["bronze"], gallery)
    for rib, angle in enumerate((math.radians(28), math.radians(58), math.radians(90), math.radians(122), math.radians(152))):
        x = center[0] + math.cos(angle) * width / 2
        z = base_z + 4.65 + math.sin(angle) * 3.3
        add_tube(
            f"V2_GlassVaultSpine_{rib:02d}",
            [(x, center[1] - length / 2, z), (x, center[1] + length / 2, z)],
            0.06,
            mats["bronze"],
            gallery,
        )
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
    add_arch_frame_y("V2_GlassGalleryEntryArch", center[0], portal_y - 0.18, base_z + 0.05, 2.65, base_z + 3.15, 0.14, mats["gold_glow"], gallery)
    add_box("V2_GlassGalleryDoor", (5.0, 0.25, 4.4), (center[0], center[1] - length / 2 - 0.35, base_z + 2.3), mats["glass"], gallery, bevel=0.12)
    add_text("V2_GlassGallerySign", "GLASS GALLERY", (center[0], center[1] - length / 2 - 0.55, base_z + 5.45), (math.pi / 2, 0, 0), 0.55, mats["gold_glow"], gallery)
    for side in (-1, 1):
        add_cone(
            f"V2_GlassGalleryFinial_{side:+d}",
            0.32,
            0.02,
            1.35,
            (center[0] + side * 4.35, portal_y, base_z + 6.65),
            mats["bronze"],
            gallery,
            vertices=20,
        )


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
    add_ellipse_band("V2_ArchiveLowerCornice", center, (radius + 0.65, radius + 0.65), 1.15, ground_z + 0.35, 0.34, mats["bronze"], archive, segments=80)
    add_ellipse_band("V2_ArchiveCrownCornice", center, (radius + 0.72, radius + 0.72), 1.10, ground_z + 6.08, 0.42, mats["bronze"], archive, segments=80)
    for index in range(13):
        angle = math.radians(-12 + index * 18)
        x = center[0] + math.cos(angle) * (radius + 0.28)
        y = center[1] + math.sin(angle) * (radius + 0.28)
        add_classical_column(
            f"V2_ArchiveExteriorColumn_{index:02d}",
            (x, y, ground_z + 0.25),
            5.75,
            0.28,
            mats["stone"],
            mats["bronze"],
            archive,
        )
        if index < 12:
            pane_angle = math.radians(-3 + index * 18)
            px = center[0] + math.cos(pane_angle) * (radius + 0.12)
            py = center[1] + math.sin(pane_angle) * (radius + 0.12)
            add_box(
                f"V2_ArchiveWarmWindow_{index:02d}",
                (2.15, 0.13, 3.15),
                (px, py, ground_z + 3.15),
                mats["window"],
                archive,
                rotation_z=pane_angle + math.pi / 2,
                bevel=0.12,
            )
    add_dome("V2_ArchiveGlassDome", center, ground_z + 6.2, radius, 6.2, mats["glass"], archive, rings=9, segments=48)
    for rib in range(20):
        angle = TAU * rib / 20
        points = []
        for step in range(10):
            phi = (math.pi / 2) * step / 9
            points.append((center[0] + radius * math.sin(phi) * math.cos(angle), center[1] + radius * math.sin(phi) * math.sin(angle), ground_z + 6.2 + 6.2 * math.cos(phi)))
        add_tube(f"V2_ArchiveDomeRib_{rib:02d}", points, 0.07, mats["bronze"], archive)
    add_cylinder("V2_ArchiveDomeLantern", 2.25, 1.4, (center[0], center[1], ground_z + 12.95), mats["window"], archive, vertices=32)
    add_ellipse_band("V2_ArchiveLanternCrown", center, (2.65, 2.65), 0.48, ground_z + 13.72, 0.28, mats["bronze"], archive, segments=40)
    add_cone("V2_ArchiveFinial", 0.42, 0.03, 2.25, (center[0], center[1], ground_z + 15.0), mats["bronze"], archive, vertices=24)
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
    add_arch_frame_y("V2_ArchiveEntryArch", center[0], center[1] - radius - 0.32, ground_z + 0.05, 2.8, ground_z + 3.35, 0.15, mats["gold_glow"], archive)
    add_text("V2_ArchiveSign", "GRAND TIDE ARCHIVE", (center[0], center[1] - radius - 0.22, ground_z + 5.75), (math.pi / 2, 0, 0), 0.52, mats["gold_glow"], archive)
    add_steps(
        "V2_ArchiveForecourtStair",
        (center[0], center[1] - radius - 5.2, ground_z - 1.25),
        (center[0], center[1] - radius - 0.4, ground_z + 0.05),
        8.0,
        9,
        mats["stone"],
        archive,
    )
    for side in (-1, 1):
        add_lantern(
            f"V2_ArchiveEntryLantern_{side:+d}",
            (center[0] + side * 4.6, center[1] - radius - 1.0, ground_z),
            2.2,
            mats,
            archive,
        )
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
    style: str,
    collections: dict[str, bpy.types.Collection],
    mats: dict[str, bpy.types.Material],
) -> None:
    pavilions = collections["pavilions"]
    add_cylinder(f"V2_{label}Foundation", radius + 1.0, 0.9, (center[0], center[1], base_z - 0.45), mats["foundation"], pavilions, vertices=40)
    add_cylinder(f"V2_{label}Floor", radius, 0.35, (center[0], center[1], base_z), mats["floor"], pavilions, vertices=40)
    wall_height = 4.25 if style == "open_portico" else 4.6
    add_arc_wall(f"V2_{label}Drum", center, radius, 0.65, base_z, wall_height, math.radians(-50), math.radians(230), mats["stone"], pavilions, segments=40)
    add_ellipse_band(f"V2_{label}PlinthRing", center, (radius + 0.55, radius + 0.55), 0.75, base_z + 0.25, 0.28, mats["bronze"], pavilions, segments=52)
    add_ellipse_band(f"V2_{label}Cornice", center, (radius + 0.50, radius + 0.50), 0.70, base_z + wall_height - 0.10, 0.34, mats["bronze"], pavilions, segments=52)
    add_dome(f"V2_{label}Dome", center, base_z + 4.6, radius, 3.0, mats["glass"], pavilions, rings=6, segments=32)
    for index in range(10):
        angle = TAU * index / 10
        x = center[0] + math.cos(angle) * (radius - 0.3)
        y = center[1] + math.sin(angle) * (radius - 0.3)
        add_classical_column(f"V2_{label}Column_{index:02d}", (x, y, base_z + 0.1), 4.4, 0.19, mats["stone"], mats["bronze"], pavilions)
    for index, angle in enumerate((math.radians(70), math.radians(125), math.radians(235), math.radians(290))):
        x = center[0] + math.cos(angle) * (radius - 0.55)
        y = center[1] + math.sin(angle) * (radius - 0.55)
        add_box(f"V2_{label}Art_{index}", (2.0, 0.16, 2.3), (x, y, base_z + 2.3), mats["art"], pavilions, rotation_z=angle + math.pi / 2, bevel=0.03)
    portal_y = center[1] - radius + 0.25
    for side in (-1, 1):
        add_box(f"V2_{label}PortalPier_{side:+d}", (1.0, 0.8, 4.8), (center[0] + side * 1.8, portal_y, base_z + 2.4), mats["bronze"], pavilions, bevel=0.20)
    add_box(f"V2_{label}PortalLintel", (4.6, 0.8, 0.8), (center[0], portal_y, base_z + 4.4), mats["bronze"], pavilions, bevel=0.18)
    add_arch_frame_y(f"V2_{label}EntryArch", center[0], portal_y - 0.18, base_z + 0.08, 1.9, base_z + 2.65, 0.12, mats["gold_glow"], pavilions)
    add_text(f"V2_{label}Sign", label.upper().replace("_", " "), (center[0], center[1] - radius - 0.22, base_z + 4.35), (math.pi / 2, 0, 0), 0.36, mats["gold_glow"], pavilions)
    # Three related but visibly different buildings prevent the terrace from
    # reading like duplicated cylinders.
    if style == "open_portico":
        for side in (-1, 1):
            add_box(
                f"V2_{label}Wing_{side:+d}",
                (4.2, 5.2, 0.45),
                (center[0] + side * (radius + 1.6), center[1] + 0.8, base_z + 4.65),
                mats["stone"],
                pavilions,
                rotation_z=side * 0.18,
                bevel=0.16,
            )
            for row in range(2):
                add_classical_column(
                    f"V2_{label}WingColumn_{side:+d}_{row}",
                    (center[0] + side * (radius + 1.7), center[1] - 1.1 + row * 3.6, base_z),
                    4.65,
                    0.22,
                    mats["stone"],
                    mats["bronze"],
                    pavilions,
                )
    elif style == "belvedere":
        add_ellipse_band(f"V2_{label}Balcony", center, (radius + 1.3, radius + 1.3), 1.65, base_z + 4.45, 0.34, mats["floor"], pavilions, segments=56)
        rail_points = []
        for index in range(49):
            angle = TAU * index / 48
            rail_points.append((center[0] + (radius + 1.2) * math.cos(angle), center[1] + (radius + 1.2) * math.sin(angle), base_z + 5.35))
        add_tube(f"V2_{label}BalconyRail", rail_points, 0.055, mats["bronze"], pavilions)
    else:
        add_cylinder(f"V2_{label}UpperLantern", radius * 0.46, 2.1, (center[0], center[1], base_z + 7.25), mats["window"], pavilions, vertices=32)
        add_dome(f"V2_{label}UpperCap", center, base_z + 8.3, radius * 0.55, 1.35, mats["glass"], pavilions, rings=5, segments=28)
        add_cone(f"V2_{label}Finial", 0.32, 0.03, 1.65, (center[0], center[1], base_z + 10.2), mats["bronze"], pavilions, vertices=20)


def build_pavilions(collections: dict[str, bpy.types.Collection], mats: dict[str, bpy.types.Material]) -> list[dict]:
    specs = [
        ("RECOMPOSITION", (25.0, -10.0), 3.2, 5.7, "open_portico"),
        ("MATERIAL", (31.0, 5.0), 4.8, 6.2, "belvedere"),
        ("MOOD_OBJECT", (24.0, 21.0), 6.4, 6.8, "lantern_tower"),
    ]
    for label, center, base_z, radius, style in specs:
        build_pavilion(label, center, base_z, radius, style, collections, mats)
    return [
        {"id": label.lower(), "center": [center[0], center[1], base_z], "diameter_m": radius * 2, "style": style}
        for label, center, base_z, radius, style in specs
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
        if index % 2 == 0:
            for branch in (-1, 1):
                add_cone(
                    f"V2_CoralBranch_{index:02d}_{branch:+d}",
                    0.11,
                    0.025,
                    height * 0.72,
                    (x + branch * 0.28, y, 3.35 + height * 0.78),
                    mats["coral_gold" if index % 4 == 0 else "coral_cool"],
                    garden,
                    vertices=8,
                ).rotation_euler = (0, branch * 0.48, 0)
    for index, angle in enumerate((0.35, 2.05, 3.55, 5.15)):
        add_lantern(
            f"V2_GardenLantern_{index:02d}",
            (12.0 * math.cos(angle), 8.5 * math.sin(angle), 3.25),
            1.55,
            mats,
            garden,
        )


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
        scene.eevee.taa_render_samples = 20
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.use_nodes = True
    background = next(node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.008, 0.11, 0.17, 1.0)
    background.inputs["Strength"].default_value = 0.88

    lighting = collections["lighting"]
    add_light("V2_SurfaceSun", "AREA", (-22, -18, 34), (0.48, 0.86, 1.0), 3800, lighting, size=20, target=(0, 0, 3))
    add_light("V2_GardenFill", "AREA", (8, -8, 21), (0.24, 0.66, 0.82), 2200, lighting, size=16, target=(0, 0, 4))
    add_light("V2_ArchiveWarmKey", "AREA", (-12, 18, 20), (1.0, 0.62, 0.28), 1900, lighting, size=12, target=(-12, 23, 8))
    add_light("V2_GlassGalleryWarm", "AREA", (-31, 2, 15), (1.0, 0.68, 0.34), 1500, lighting, size=10, target=(-31, 2, 8))
    add_light("V2_SeabedFillWest", "AREA", (-38, -15, 14), (0.20, 0.66, 0.70), 1600, lighting, size=22, target=(-30, -8, 0))
    add_light("V2_SeabedFillEast", "AREA", (38, -5, 16), (0.14, 0.58, 0.72), 1750, lighting, size=24, target=(30, 4, 0))
    add_light("V2_BackReefRim", "AREA", (0, 37, 18), (0.16, 0.50, 0.60), 1350, lighting, size=26, target=(0, 25, 2))
    for index, location in enumerate(((25, -10, 10), (31, 5, 12), (24, 21, 14))):
        add_light(f"V2_PavilionWarm_{index}", "POINT", location, (1.0, 0.60, 0.30), 760, lighting)
    add_light("V2_LightShaftGlow", "POINT", (-12, 23, 9), (0.16, 0.82, 1.0), 850, lighting)

    cameras = collections["cameras"]
    specs = [
        (1, "V2_HERO", add_camera("V2_HeroCamera", (-57, -49, 28), (-1, 6, 7), 50, cameras)),
        (20, "V2_PLAN", add_camera("V2_PlanCamera", (0, -6, 130), (0, 1, 2.2), 32, cameras)),
        (40, "V2_LOOP", add_camera("V2_LoopCamera", (-21, -18, 8.2), (13, -1, 6.5), 44, cameras)),
        (60, "V2_ARCHIVE_CUTAWAY", add_camera("V2_ArchiveCutawayCamera", (12, -15, 20), (-12, 23, 9.0), 52, cameras)),
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
<title>Atlantis Gallery Local Review</title>
<style>
:root{color-scheme:dark;--deep:#031f35;--blue:#0a4f7a;--gold:#e8b54a;--cream:#fff5dc}*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:radial-gradient(circle at 70% 12%,#0a5676 0,#052f49 38%,#031c31 100%);color:var(--cream)}body{font-family:-apple-system,BlinkMacSystemFont,\"Noto Sans SC\",sans-serif}canvas{display:block}.topbar{position:fixed;z-index:3;left:28px;right:28px;top:24px;display:flex;align-items:flex-start;justify-content:space-between;gap:18px;pointer-events:none}.brand{min-width:0;text-shadow:0 2px 18px rgba(0,11,22,.9)}.brand strong{display:block;font:600 23px/1.1 \"Noto Serif SC\",Songti SC,Georgia,serif;letter-spacing:.02em;color:var(--cream)}.brand span{display:block;margin-top:7px;font-size:11px;letter-spacing:.18em;color:rgba(255,226,154,.76)}.views{display:flex;gap:8px;pointer-events:auto}.views button{appearance:none;border:1px solid rgba(255,226,154,.34);background:rgba(3,31,53,.62);backdrop-filter:blur(10px);color:rgba(255,245,220,.86);padding:9px 14px;border-radius:999px;font-weight:600;cursor:pointer;white-space:nowrap;transition:background .2s,color .2s,border-color .2s}.views button:hover,.views button.active{background:var(--gold);border-color:var(--gold);color:var(--deep)}.footer{position:fixed;z-index:3;left:28px;right:28px;bottom:22px;display:flex;justify-content:space-between;align-items:flex-end;gap:18px;pointer-events:none;font-size:11px;letter-spacing:.06em;color:rgba(255,245,220,.62);text-shadow:0 1px 10px #001522}.status{border-left:2px solid var(--gold);padding:4px 0 4px 10px}.help{text-align:right}@media(max-width:720px){.topbar{left:16px;right:16px;top:16px;display:block}.brand strong{font-size:19px}.views{margin-top:14px;overflow-x:auto}.views button{padding:8px 11px}.footer{left:16px;right:16px;bottom:14px}.help{display:none}}@media(prefers-reduced-motion:reduce){.views button{transition:none}}
</style></head><body><header class=\"topbar\"><div class=\"brand\"><strong>brocademaple · Atlantis Gallery</strong><span>水下建筑本地评审</span></div><nav class=\"views\" aria-label=\"Review views\"><button data-view=\"hero\" class=\"active\">园区</button><button data-view=\"plan\">总平面</button><button data-view=\"loop\">步行环路</button><button data-view=\"archive\">潮汐档案馆</button></nav></header><footer class=\"footer\"><div class=\"status\" id=\"status\">正在读取本地建筑模型</div><div class=\"help\">拖动旋转 · 滚轮缩放 · 右键平移</div></footer><script type=\"module\">
import * as THREE from 'https://esm.sh/three@0.160.0';
import {GLTFLoader} from 'https://esm.sh/three@0.160.0/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js';
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;document.body.append(renderer.domElement);
const scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x07364d,.0058);const camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.1,300);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=!matchMedia('(prefers-reduced-motion:reduce)').matches;controls.dampingFactor=.07;controls.maxDistance=175;controls.minDistance=7;
scene.add(new THREE.HemisphereLight(0x8fe6f4,0x02131e,2.35));const sun=new THREE.DirectionalLight(0xc5f3ff,3.4);sun.position.set(-28,48,35);scene.add(sun);const warm=new THREE.PointLight(0xffa75c,68,100,1.3);warm.position.set(-12,15,-23);scene.add(warm);
const views={hero:{p:[-57,28,49],t:[-1,7,-6]},plan:{p:[0,130,6],t:[0,2.2,-1]},loop:{p:[-21,8.2,18],t:[13,6.5,1]},archive:{p:[12,20,15],t:[-12,9,-23]}};
function view(id){const v=views[id];camera.position.set(...v.p);controls.target.set(...v.t);controls.update();document.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.view===id))}document.querySelectorAll('button').forEach(b=>b.onclick=()=>view(b.dataset.view));view('hero');
new GLTFLoader().load('./atlantis-gallery-master-v2-environment.glb',g=>{scene.add(g.scene);document.getElementById('status').textContent='V2.2 水下环境已加载 · 仅本地预览';},undefined,e=>{document.getElementById('status').textContent='模型加载失败，请从桌面启动器重新打开';console.error(e)});
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
    output_dir = repo / "output/gallery/master-v2-environment"
    working_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = working_dir / "atlantis-gallery-master-v2-environment.blend"
    glb_path = output_dir / "atlantis-gallery-master-v2-environment.glb"
    viewer_path = output_dir / "index.html"

    scene["gallery_version"] = "2.2-environment"
    scene["publication_state"] = "local-only"
    scene["source_of_truth"] = str(Path(__file__).resolve())
    scene["spatial_contract"] = "crescent campus + 3.2m loop + grand three-level archive"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    # Export a compact all-in-one local review GLB. A public V2 can later split
    # the campus into proximity-loaded modules after the architecture is signed off.
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
        "version": "2.2-environment",
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
            "environment_under_300k_triangles": triangle_count <= 300_000,
            "environment_glb_under_35mb": glb_path.stat().st_size <= 35_000_000,
        },
    }
    audit["passed"] = all(audit["gates"].values())
    audit_path = output_dir / "audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not audit["passed"]:
        failed = [name for name, passed in audit["gates"].items() if not passed]
        raise RuntimeError("V2.2 environment audit failed: " + ", ".join(failed))

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
        "stone": material("V2_PaleLimestone", (0.62, 0.76, 0.75, 1), roughness=0.66),
        "foundation": material("V2_DeepTealFoundation", (0.018, 0.105, 0.145, 1), roughness=0.80),
        "floor": material("V2_SiltMosaicFloor", (0.31, 0.53, 0.55, 1), roughness=0.62),
        "mosaic": material("V2_GoldMosaicInlay", (0.72, 0.45, 0.12, 1), metallic=0.52, roughness=0.34, emission=(0.48, 0.22, 0.04, 1), emission_strength=0.18),
        "bronze": material("V2_OxidizedBronze", (0.40, 0.27, 0.085, 1), metallic=0.84, roughness=0.29),
        "glass": material("V2_ProtectedGlass", (0.055, 0.48, 0.64, 0.26), roughness=0.10, transmission=0.76),
        "window": material("V2_WarmWindow", (0.90, 0.48, 0.16, 0.76), roughness=0.22, transmission=0.22, emission=(0.92, 0.34, 0.06, 1), emission_strength=1.55),
        "light_glass": material("V2_WaterLightGlass", (0.05, 0.72, 0.88, 0.40), roughness=0.18, transmission=0.48, emission=(0.04, 0.72, 0.94, 1), emission_strength=1.7),
        "water": material("V2_WaterCeiling", (0.03, 0.42, 0.58, 0.22), roughness=0.18, transmission=0.58),
        "shaft": material("V2_SunShaft", (0.13, 0.72, 0.92, 0.045), roughness=0.14, transmission=0.78, emission=(0.05, 0.55, 0.78, 1), emission_strength=0.12),
        "seabed": procedural_ground_material("V2_SeabedRendered"),
        "reef": procedural_ground_material("V2_ReefRockRendered", reef=True),
        "reef_mid": procedural_ground_material("V2_ReefTerraceRendered", reef=True),
        "rock": material("V2_GardenRock", (0.08, 0.25, 0.25, 1), roughness=0.86),
        "sand": material("V2_TurquoiseSand", (0.23, 0.50, 0.48, 1), roughness=0.91),
        "silt": material("V2_BlueSilt", (0.08, 0.32, 0.36, 1), roughness=0.92),
        "stone_dark": material("V2_RuinStone", (0.18, 0.38, 0.38, 1), roughness=0.82),
        "caustic_cool": caustic_material("V2_CoolCausticProjection", (0.28, 0.88, 1.0, 1), 0.10),
        "caustic_gold": caustic_material("V2_GoldCausticProjection", (1.0, 0.70, 0.30, 1), 0.05),
        "kelp": material("V2_DeepKelp", (0.018, 0.22, 0.17, 1), roughness=0.72),
        "kelp_light": material("V2_KelpLeaf", (0.05, 0.42, 0.30, 1), roughness=0.70),
        "warm": material("V2_ArchiveWorkbench", (0.34, 0.21, 0.12, 1), roughness=0.55),
        "art": material("V2_ArtworkPlaceholder", (0.58, 0.30, 0.20, 1), roughness=0.42, emission=(0.50, 0.19, 0.08, 1), emission_strength=0.25),
        "gold_glow": material("V2_GoldWayfinding", (0.82, 0.54, 0.13, 1), metallic=0.48, roughness=0.28, emission=(0.95, 0.55, 0.12, 1), emission_strength=1.4),
        "coral_warm": material("V2_CoralWarm", (0.55, 0.13, 0.08, 1), roughness=0.68),
        "coral_cool": material("V2_CoralCool", (0.05, 0.38, 0.38, 1), roughness=0.70),
        "coral_gold": material("V2_CoralGold", (0.76, 0.42, 0.10, 1), roughness=0.62),
        "sea_fan": material("V2_SeaFan", (0.10, 0.52, 0.42, 1), roughness=0.66),
        "fish": material("V2_FishSilhouette", (0.025, 0.13, 0.16, 1), metallic=0.18, roughness=0.54),
        "fish_gold": material("V2_FishGold", (0.62, 0.42, 0.14, 1), metallic=0.35, roughness=0.42),
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
