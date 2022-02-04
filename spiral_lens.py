#!/bin/env python

# coding: utf-8

# flake8: noqa
import ctypes
import os
import time
import sys
from vulkan import *
from vulkan_lib import *

instance_inst = Instance()



# Main loop
running = True
if sys.version_info >= (3, 3):
    clock = time.perf_counter
else:
    clock = time.clock

last_time = clock() * 1000
fps = 0
while instance_inst.device.surface.running:
    fps += 1
    if clock() * 1000 - last_time >= 1000:
        last_time = clock() * 1000
        print("FPS: %s" % fps)
        fps = 0

    instance_inst.device.surface.processEvents()
    instance_inst.draw_frame()

instance_inst.release()
