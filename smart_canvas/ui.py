from pyrr import matrix44
import numpy as np

from pathlib import Path

from moderngl_window.text.bitmapped import TextWriter2D
from moderngl_window import resources
from moderngl_window.meta import (
    ProgramDescription,
    TextureDescription,
)
import moderngl_window
import moderngl

resources.register_dir(Path(__file__).parent.resolve())


class TextWriterTest(TextWriter2D):
    """
    Class for creating text in OpenGL context. Extended from TextWriter2D
    """
    def __init__(self, position, size=24.0):
        super().__init__()
        # load custom glsl
        self._program = resources.programs.load(
            ProgramDescription(path="text.glsl")
        )
        self.pos = position
        self.size = size
        self.visible = False

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        self._text = value
        # String buffer is in_char_id at glsl
        self._string_buffer.orphan(size=len(value) * 4)

        self._string_buffer.clear(chunk=b'\32')
        self._write(value)

    def _write(self, text: str):
        # put ISO -- letter positions in opengl buffer. These are used to find correct textures for letters in map
        self._string_buffer.clear(chunk=b'\32')

        self._string_buffer.write(
            np.fromiter(
                self._translate_string(text),
                dtype=np.uint32,
            )
        )

    def draw(self, length=-1):
        # Calculate ortho projection based on viewport
        vp = self.ctx.fbo.viewport
        w, h = vp[2] - vp[0], vp[3] - vp[1]
        # projection matrix to viewport so we can use pixel coordinates
        # right low corner is 0,0 as expected
        projection = matrix44.create_orthogonal_projection_matrix(
            0,  # left
            w,  # right
            0,  # bottom
            h,  # top
            1,  # near
            -1.0,  # far
            dtype=np.float32,
        )

        self._texture.use(location=0)
        self._program["m_proj"].write(projection)
        self._program["text_pos"].value = self.pos

        self._program["font_texture"].value = 0
        self._program["char_size"].value = self._meta.char_aspect_wh * self.size, self.size

        self._vao.render(self._program, instances=len(self._text))

class Image2D():
    """
    Draw images with opengl! Currently not working.
    """
    def __init__(self, pos: tuple, size: tuple, path: str):
        # get context for this class
        self.ctx = moderngl_window.ContextRefs.CONTEXT
        self._program = resources.programs.load(
            ProgramDescription(path="image.glsl")
        )
        pos = self.ctx.buffer(
            array('f',
                  [
                      -1,  1, 0, 1,  # upper left
                      -1, -1, 0, 0,  # lower left
                      1,  1, 1, 1,  # upper right
                      1, -1, 1, 0,  # lower right
                  ])
        )
        #pos = self.ctx.buffer(data=bytes([0] * 4 * 2))
       # print(bytes([0] * 4 * 3))
        projection = matrix44.create_orthogonal_projection_matrix(
            0,  # left
            1280,  # right
            0,  # bottom
            720,  # top
            1.0,  # near
            -1.0,  # far
            dtype=np.float32,
        )

        #self.scale = self._program['scale']
        self.pos = self._program['in_vert']

        #self.vbo = self.ctx.buffer()
        #self.scale.value = (0.5, 0.5)

        self._program['m_proj'].write(projection)

        self.vao = self.ctx.vertex_array(
            self._program,
            [
                (pos, '2f 2f',  'in_vert', 'in_uv'),
            ]
        )

        self.visible = True

        self._image = resources.textures.load(TextureDescription(
            path, midmap=False,))

    def draw(self):
        # Calculate ortho projection based on viewport
        vp = self.ctx.fbo.viewport
        w, h = vp[2] - vp[0], vp[3] - vp[1]
        # projection matrix to viewport so we can use pixel coordinates
        # right low corner is 0,0 as expected
        projection = matrix44.create_orthogonal_projection_matrix(
            0,  # left
            w,  # right
            0,  # bottom
            h,  # top
            1,  # near
            -1.0,  # far
            dtype=np.float32,
        )
        #self.pos = (1.0, 1.0)
        self._image.use(location=0)
        self.vao.render(moderngl.TRIANGLE_STRIP)

class Progressbar():
    """
    Create a progress bar badly with quads. Simply scale the vertex translation matrix
    to create an illusion of progress bar
    """
    def __init__(self):

        self.ctx = moderngl_window.ContextRefs.CONTEXT
        self._program = resources.programs.load(
            ProgramDescription(path="progressbar.glsl")
        )

        vertices = np.array([
                      0.4,  -0.7, 0, -0.7,  
                      0.4, -0.8, 0, -0.8,  
        ]
        )
        self.vbo = self.ctx.buffer(vertices.astype('f4').tobytes())
        self.visible = True
        self._scale = 0.0

        self.vao = self.ctx.vertex_array(
            self._program,
            [
                (self.vbo, '2f', 'in_vert'),
            ]
        )

    @property
    def scale(self):
        return self.scale

    @scale.setter
    def scale(self,value):
        if value < 0.0:
            self._scale = 0.0
        else:
            self._scale = value

    def draw(self):
        self._program["scale"] = self._scale 
        self.vao.render(mode=moderngl.TRIANGLE_STRIP)

class UI:
    """
    Class for managing UI elements
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UI, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if(self._initialized): return
        self._initialized = True

        super(UI, self).__setattr__('elements', dict())
        self.texts = dict()
        self.images = dict()

    # add new element
    def create_text(self, name: str, pos: tuple, size: float):
        self.elements[name] = TextWriterTest(pos,size)

    def create_image(self, path: str, pos: tuple, size: tuple):
        self.images[path] = Image2D(pos, size, path)

    def create_progressbar(self, name: str):
        self.elements[name] = Progressbar()

    def set_text(self, name: str, text: str):
        if name not in self.elements:
            raise KeyError
        self.texts[name] = text

    def set_prog(self, name: str, value: float):
        if name not in self.elements:
            raise KeyError
        
        self.elements[name].scale = value

    def show(self, *names: str):
        for name in names:
            if name in self.elements:
                self.elements[name].visible = True
            else:
                raise KeyError

    def hide(self, *names: str):
        for name in names:
            if name in self.elements:
                self.elements[name].visible = False
            else:
                raise KeyError

    def draw(self):
        #TODO: use same dict for both images and texts
        #copy new texts to buffer
        for k,v in self.texts.items():
            if self.elements[k].text is not v:
                self.elements[k].text = v 
        #render all
        {v.draw() for k,v in self.elements.items() if v.visible }
