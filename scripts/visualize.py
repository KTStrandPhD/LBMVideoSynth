import subprocess
import numpy as np
import cv2

WIDTH, HEIGHT = 128, 128

# Optional: You can update main.cpp to continuously print raw binary density floats to stdout,
# or we can write a tiny C++ exporter loop. 
# For an immediate test, let's look at how a Python script can wrap the simulation:
