

class PskImportOptions(object):
    def __init__(self):
        self.name = ''
        self.scale_down_mesh = True
        self.should_import_mesh = True
        self.should_import_vertex_colors = True
        self.vertex_color_space = 'sRGB'
        self.should_import_vertex_normals = True
        self.should_import_extra_uvs = True


def rgb_to_srgb(c):
    if c > 0.0031308:
        return 1.055 * (pow(c, (1.0 / 2.4))) - 0.055
    else:
        return 12.92 * c