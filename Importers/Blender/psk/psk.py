from ctypes import *
from typing import List, Tuple


class Color(Structure):
    _fields_ = [
        ('r', c_ubyte),
        ('g', c_ubyte),
        ('b', c_ubyte),
        ('a', c_ubyte),
    ]

    def __iter__(self):
        yield self.r
        yield self.g
        yield self.b
        yield self.a

    def __eq__(self, other):
        return all(map(lambda x: x[0] == x[1], zip(self, other)))

    def __repr__(self):
        return repr(tuple(self))

    def normalized(self) -> Tuple:
        return tuple(map(lambda x: x / 255.0, iter(self)))


class Vector2(Structure):
    _fields_ = [
        ('x', c_float),
        ('y', c_float),
    ]

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self):
        return repr(tuple(self))


class Vector3(Structure):
    _fields_ = [
        ('x', c_float),
        ('y', c_float),
        ('z', c_float),
    ]

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __repr__(self):
        return repr(tuple(self))

    @classmethod
    def zero(cls):
        return Vector3(0, 0, 0)


class Quaternion(Structure):
    _fields_ = [
        ('x', c_float),
        ('y', c_float),
        ('z', c_float),
        ('w', c_float),
    ]

    def __iter__(self):
        yield self.w
        yield self.x
        yield self.y
        yield self.z

    def __repr__(self):
        return repr(tuple(self))

    @classmethod
    def identity(cls):
        return Quaternion(0, 0, 0, 1)



class Section(Structure):
    _fields_ = [
        ('name', c_char * 20),
        ('type_flags', c_int32),
        ('data_size', c_int32),
        ('data_count', c_int32)
    ]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.type_flags = 1999801

class Psk(object):
    class Wedge(object):
        def __init__(self):
            self.point_index: int = 0
            self.u: float = 0.0
            self.v: float = 0.0
            self.material_index: int = 0

        def __hash__(self):
            return hash(f'{self.point_index}-{self.u}-{self.v}-{self.material_index}')

    class Wedge16(Structure):
        _fields_ = [
            ('point_index', c_uint16),
            ('padding1', c_int16),
            ('u', c_float),
            ('v', c_float),
            ('material_index', c_uint8),
            ('reserved', c_int8),
            ('padding2', c_int16)
        ]

    class Wedge32(Structure):
        _fields_ = [
            ('point_index', c_uint32),
            ('u', c_float),
            ('v', c_float),
            ('material_index', c_uint32)
        ]

    class Face(Structure):
        _fields_ = [
            ('wedge_indices', c_uint16 * 3),
            ('material_index', c_uint8),
            ('aux_material_index', c_uint8),
            ('smoothing_groups', c_int32)
        ]

    class Face32(Structure):
        _pack_ = 1
        _fields_ = [
            ('wedge_indices', c_uint32 * 3),
            ('material_index', c_uint8),
            ('aux_material_index', c_uint8),
            ('smoothing_groups', c_int32)
        ]

    class Material(Structure):
        _fields_ = [
            ('name', c_char * 64),
            ('texture_index', c_int32),
            ('poly_flags', c_int32),
            ('aux_material', c_int32),
            ('aux_flags', c_int32),
            ('lod_bias', c_int32),
            ('lod_style', c_int32)
        ]

    class Bone(Structure):
        _fields_ = [
            ('name', c_char * 64),
            ('flags', c_int32),
            ('children_count', c_int32),
            ('parent_index', c_int32),
            ('rotation', Quaternion),
            ('location', Vector3),
            ('length', c_float),
            ('size', Vector3)
        ]

    class Weight(Structure):
        _fields_ = [
            ('weight', c_float),
            ('point_index', c_int32),
            ('bone_index', c_int32),
        ]

    @property
    def has_extra_uvs(self):
        return len(self.extra_uvs) > 0

    @property
    def has_vertex_colors(self):
        return len(self.vertex_colors) > 0

    @property
    def has_vertex_normals(self):
        return len(self.vertex_normals) > 0

    def __init__(self):
        self.points: Tuple[Vector3] = ()
        self.wedges: Tuple[Psk.Wedge] = ()
        self.faces: Tuple[Psk.Face] = ()
        self.materials: Tuple[Psk.Material] = ()
        self.weights: Tuple[Psk.Weight] = ()
        self.bones: Tuple[Psk.Bone] = ()
        self.extra_uvs: List[Tuple[Vector2]] = ()
        self.vertex_colors: Tuple[Color] = ()
        self.vertex_normals: Tuple[Vector3] = ()

