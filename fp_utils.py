#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT

from ROOT import std
vstring = std.vector(std.string)

class colors:
    GREEN = "\033[1;32m"
    RED = "\033[1;31m"
    CYAN = "\033[1;34m"
    DEFAULT = "\033[0;10m"

###---message logger--------------------------------------------------
def printMessage(msg, msg_type):
    """Print colored information message"""

    # info message
    if msg_type == 0:
        print("> FuriousPlotter: "+msg)
    # error
    elif msg_type == -1:
        print(colors.RED+"> FuriousPlotter: ERROR! "+colors.DEFAULT+msg)
    # success
    elif msg_type == 1:
        print(colors.GREEN+"> FuriousPlotter: "+colors.DEFAULT+msg)

###---process C++ lines-----------------------------------------------
def processLines(lines):
    """Process single lines of C++ source code. Useful for on-the-fly style settings"""
    
    for line in lines:
        ROOT.gROOT.ProcessLine(line)
