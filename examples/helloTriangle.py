#!/bin/env python
import os
import time
import sys
import numpy as np
import json
import sdl2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import vulkanese as ve
import vulkanese.shapes
import vulkanese.stock_pipeline.simple_graphics as simple_graphics
import vulkan as vk
from sinode import Sinode

htHere = os.path.dirname(os.path.abspath(__file__))


class PyramidExample(simple_graphics.SimpleGraphicsPipeline):
    def __init__(self, device, surface, constantsDict):
        simple_graphics.SimpleGraphicsPipeline.__init__(self, device=device, surface=surface, constantsDict=constantsDict)
        
        # create the pyramid
        self.pyramid = vulkanese.shapes.Pyramid()
        self.indexBuffer.set(np.array(self.pyramid.mesh.triangles, dtype = np.uint32).flatten())
        self.vertexStage.gpuBuffers.position.set(
            np.array(self.pyramid.mesh.vertices).flatten()
        )
        self.vertexStage.gpuBuffers.color.set(
            self.pyramid.verticesColorBGR
        )
        
        print(self.indexBuffer.getAsNumpyArray())
        print(self.vertexStage.gpuBuffers.position.getAsNumpyArray())
        print(self.vertexStage.gpuBuffers.color.getAsNumpyArray())
        
        self.running = True
        
    def run(self):
        # rotate and redraw the pyramid
        self.pyramid.rotate(self.fps_last)
        self.vertexStage.gpuBuffers.position.set(
            np.array(self.pyramid.mesh.vertices).flatten()
        )

        # get quit, mouse, keypress etc
        for event in self.surface.getEvents():
            if event.type == sdl2.SDL_QUIT:
                self.running = False
                vk.vkDeviceWaitIdle(self.device.vkDevice)
                break

        # draw the frame!
        self.draw_frame()


if __name__ == "__main__":

    # constants declared here will be visible in this class as an attribute,
    # and in the shader as a #define
    
    # we need 12 verts for a pyramid
    constantsDict = {
        "VERTEX_COUNT": 12,  # there are redundant verts
        "TRIANGLE_COUNT": 4,
        "VERTS_PER_TRIANGLE": 3,
        "SPATIAL_DIMENSIONS": 3,
        "COLOR_DIMENSIONS": 3,
    }

    width, height = 700, 700
    # device selection and instantiation
    instance = ve.instance.Instance(verbose=True)
    print("naively choosing device 0")
    device = instance.getDevice(0)
    surface = ve.surface.Surface(
        instance=instance,
        device=device,
        width=width,
        height=height,
    )
        
    ht = PyramidExample(device=device, surface=surface, constantsDict=constantsDict)
    
    # print the object hierarchy
    print("Object tree:")
    print(json.dumps(instance.asDict(), indent=4))

    while(ht.running):
        ht.run()

    # elegantly free all memory
    instance.release()
