import ctypes

import os
import sys
from math import inf
from typing import Optional, List

import bmesh
import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import Operator, PropertyGroup, VertexGroup
from bpy_extras.io_utils import ImportHelper
from mathutils import Quaternion, Vector, Matrix
from .utils import PskImportOptions, rgb_to_srgb

from .psk import *


def _read_types(fp, data_class, section: Section, data):
    buffer_length = section.data_size * section.data_count
    buffer = fp.read(buffer_length)
    offset = 0
    for _ in range(section.data_count):
        data.append(data_class.from_buffer_copy(buffer, offset))
        offset += section.data_size

# unpredictable behavior (idk why). sometimes it works, sometimes it doesn't
# def _read_types(fp, data_class, section, data):
#     buffer_length = section.data_size * section.data_count
#     buffer = fp.read(buffer_length)
#     a = ctypes.cast(buffer, ctypes.POINTER(data_class * section.data_count))
#     data.extend(a.contents)
#     assert len(data) == section.data_count


def read_psk(path: str) -> Psk:
    psk = Psk()
    with open(path, 'rb') as fp:
        while fp.read(1):
            fp.seek(-1, 1)
            section = Section.from_buffer_copy(fp.read(ctypes.sizeof(Section)))
            if section.name == b'ACTRHEAD':
                pass
            elif section.name == b'PNTS0000':
                _read_types(fp, Vector3, section, psk.points)
            elif section.name == b'VTXW0000':
                if section.data_size == ctypes.sizeof(Psk.Wedge16):
                    _read_types(fp, Psk.Wedge16, section, psk.wedges)
                elif section.data_size == ctypes.sizeof(Psk.Wedge32):
                    _read_types(fp, Psk.Wedge32, section, psk.wedges)
                else:
                    raise RuntimeError('Unrecognized wedge format')
            elif section.name == b'FACE0000':
                _read_types(fp, Psk.Face, section, psk.faces)
            elif section.name == b'MATT0000':
                _read_types(fp, Psk.Material, section, psk.materials)
            elif section.name == b'REFSKELT':
                _read_types(fp, Psk.Bone, section, psk.bones)
            elif section.name == b'RAWWEIGHTS':
                _read_types(fp, Psk.Weight, section, psk.weights)
            elif section.name == b'FACE3200':
                _read_types(fp, Psk.Face32, section, psk.faces)
            elif section.name == b'VERTEXCOLOR':
                _read_types(fp, Color, section, psk.vertex_colors)
            elif section.name.startswith(b'EXTRAUVS'):
                psk.extra_uvs.append([])
                _read_types(fp, Vector2, section, psk.extra_uvs[-1])
            elif section.name == b'VTXNORMS':
                _read_types(fp, Vector3, section, psk.vertex_normals)
            else:
                raise RuntimeError(f'Unrecognized section "{section.name} at position {15:fp.tell()}"')
    return psk

def import_psk(psk: Psk, context, options: PskImportOptions) -> Tuple[List[str], bpy.types.Object]:
    warnings = []

    # MESH
    mesh_data = bpy.data.meshes.new(options.name+".md")
    mesh_object = bpy.data.objects.new(options.name+".mo", mesh_data)

    # MATERIALS
    for material in psk.materials:
        # TODO: re-use of materials should be an option
        bpy_material = bpy.data.materials.new(material.name.decode('utf-8'))
        mesh_data.materials.append(bpy_material)

    bm = bmesh.new()

    # VERTICES
    # scale down 1/100
    if options.scale_down_mesh:
        for point in psk.points:
            point.x /= 100
            point.y /= 100
            point.z /= 100
    for point in psk.points:
        bm.verts.new(tuple(point))

    bm.verts.ensure_lookup_table()

    degenerate_face_indices = set()
    for face_index, face in enumerate(psk.faces):
        point_indices = [bm.verts[psk.wedges[i].point_index] for i in reversed(face.wedge_indices)]
        try:
            bm_face = bm.faces.new(point_indices)
            bm_face.material_index = face.material_index
        except ValueError:
            degenerate_face_indices.add(face_index)

    if len(degenerate_face_indices) > 0:
        warnings.append(f'Discarded {len(degenerate_face_indices)} degenerate face(s).')

    bm.to_mesh(mesh_data)

    # TEXTURE COORDINATES
    data_index = 0
    uv_layer = mesh_data.uv_layers.new(name='VTXW0000')
    for face_index, face in enumerate(psk.faces):
        if face_index in degenerate_face_indices:
            continue
        face_wedges = [psk.wedges[i] for i in reversed(face.wedge_indices)]
        for wedge in face_wedges:
            uv_layer.data[data_index].uv = wedge.u, 1.0 - wedge.v
            data_index += 1

    # EXTRA UVS
    if psk.has_extra_uvs and options.should_import_extra_uvs:
        extra_uv_channel_count = int(len(psk.extra_uvs) / len(psk.wedges))
        wedge_index_offset = 0
        for extra_uv_index in range(extra_uv_channel_count):
            data_index = 0
            uv_layer = mesh_data.uv_layers.new(name=f'EXTRAUV{extra_uv_index}')
            for face_index, face in enumerate(psk.faces):
                if face_index in degenerate_face_indices:
                    continue
                for wedge_index in reversed(face.wedge_indices):
                    u, v = psk.extra_uvs[extra_uv_index][wedge_index_offset + wedge_index]
                    uv_layer.data[data_index].uv = u, 1.0 - v
                    data_index += 1
            wedge_index_offset += len(psk.wedges)

    # VERTEX COLORS
    if psk.has_vertex_colors and options.should_import_vertex_colors:
        size = (len(psk.points), 4)
        vertex_colors = np.full(size, inf)
        vertex_color_data = mesh_data.vertex_colors.new(name='VERTEXCOLOR')
        ambiguous_vertex_color_point_indices = []

        for wedge_index, wedge in enumerate(psk.wedges):
            point_index = wedge.point_index
            psk_vertex_color = psk.vertex_colors[wedge_index].normalized()
            if vertex_colors[point_index, 0] != inf and tuple(vertex_colors[point_index]) != psk_vertex_color:
                ambiguous_vertex_color_point_indices.append(point_index)
            else:
                vertex_colors[point_index] = psk_vertex_color

        if options.vertex_color_space == 'SRGBA':
            for i in range(vertex_colors.shape[0]):
                vertex_colors[i, :3] = tuple(map(lambda x: rgb_to_srgb(x), vertex_colors[i, :3]))

        for loop_index, loop in enumerate(mesh_data.loops):
            vertex_color = vertex_colors[loop.vertex_index]
            if vertex_color is not None:
                vertex_color_data.data[loop_index].color = vertex_color
            else:
                vertex_color_data.data[loop_index].color = 1.0, 1.0, 1.0, 1.0

        if len(ambiguous_vertex_color_point_indices) > 0:
            warnings.append(
                f'{len(ambiguous_vertex_color_point_indices)} vertex(es) with ambiguous vertex colors.')

    # VERTEX NORMALS
    if psk.has_vertex_normals and options.should_import_vertex_normals:
        mesh_data.polygons.foreach_set("use_smooth", [True] * len(mesh_data.polygons))
        normals = []
        for vertex_normal in psk.vertex_normals:
            normals.append(tuple(vertex_normal))
        mesh_data.normals_split_custom_set_from_vertices(normals)
        mesh_data.use_auto_smooth = True

    bm.normal_update()
    bm.free()

    # Get a list of all bones that have weights associated with them.
    vertex_group_bone_indices = set(map(lambda weight: weight.bone_index, psk.weights))
    vertex_groups: List[Optional[VertexGroup]] = [None] * len(psk.bones)
    for bone_index, psk_bone in map(lambda x: (x, psk.bones[x]), vertex_group_bone_indices):
        vertex_groups[bone_index] = mesh_object.vertex_groups.new(name=psk_bone.name.decode('windows-1252'))

    for weight in psk.weights:
        vertex_groups[weight.bone_index].add((weight.point_index,), weight.weight, 'ADD')

    context.collection.objects.link(mesh_object)

    actionString = 'DESELECT'
    if bpy.ops.object.select_all.poll(): bpy.ops.object.select_all(action = actionString)
    if bpy.ops.mesh.select_all.poll(): bpy.ops.mesh.select_all(action = actionString)
    if bpy.ops.pose.select_all.poll(): bpy.ops.pose.select_all(action = actionString)

    mesh_object.select_set(True)
    context.view_layer.objects.active = mesh_object
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass

    return warnings, mesh_object

default_import_options = PskImportOptions()

def do_psk_import(path: str, context: bpy.types.Context) -> Optional[bpy.types.Object]:
    # try:
    psk = read_psk(path)
    # except Exception as e:
    #     print(f"[PSK] Failed to import {path} due to an exception: {e}")
    #     return None

    default_import_options.name = os.path.splitext(os.path.basename(path))[0]
    warnings, obj = import_psk(psk, context, default_import_options)

    print(f"[PSK] Successfully imported {path}, with {len(warnings)} warning(s).")
    for warning in warnings:
        print("\t", warning)
    return obj
