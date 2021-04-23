#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import multiprocessing as mp
import ROOT

from ROOT import std
stdvstring = "std::vector<std::string>"
stdstring = "std::string"

class colors:
    GREEN = "\033[1;32m"
    RED = "\033[1;31m"
    CYAN = "\033[1;34m"
    DEFAULT = "\033[0;10m"

###---message logger--------------------------------------------------
def printMessage(msg, msg_type):
    """
    Print colored information message
    """

    # info message
    if msg_type == 0:
        print('> FuriousPlotter: '+msg)
    # error
    elif msg_type == -1:
        print(colors.RED+'> FuriousPlotter: ERROR! '+colors.DEFAULT+msg)
    # success
    elif msg_type == 1:
        print(colors.GREEN+'> FuriousPlotter: '+colors.DEFAULT+msg)

###---process C++ lines-----------------------------------------------
def processLines(lines):
    """
    Process single lines of C++ source code. Useful for on-the-fly style settings
    """
    
    for line in lines:
        ROOT.gROOT.ProcessLine(line)

###---write subprocess manager----------------------------------------
def writeOutput(output, write_procs):
    """
    Spawn a process to write each output file
    """

    #---check for terminated processes and cleanup
    for idx, proc in enumerate(write_procs):
        if not proc.is_alive():
            proc.join()
            write_procs.pop(idx)

    #---spawn new processes
    for ext in output['exts']:
        proc = mp.Process(target=writeFile, args=(output['canvas'], output['basename']+'.'+ext, ext, output['cfg']))
        proc.start()
        write_procs.append(proc)
    if len(output['description']) > 0:
        proc = mp.Process(target=writeDescription, args=(output['description'], output['basename']+'.txt'))
        proc.start()
        write_procs.append(proc)
        
###---write single output file----------------------------------------
def writeFile(canvas, name, ext, cfg):
    """
    Write single output file. This function is called by the parallel manager
    """

    if ext == "root":
        rfile = ROOT.TFile.Open(name, "RECREATE")
        canvas.Write()
        cfg.Write()
        rfile.Close()
    else:
        canvas.Print(name, ext)

###---write single output file----------------------------------------
def writeDescription(text, name):
    """
    Write single output file. This function is called by the parallel manager
    """

    with open(name, 'w') as desc_file:
        for line in text:
            endline = '' if line[-2:] == '\n' else '\n'
            desc_file.write(line+endline)
    
###---evaluate string as int------------------------------------------
###---Note this isn't the safest way but the fastest
def eval_i(expr):
    """
    Evaluate expression an cast result as int
    """

    return int(eval(expr))

###---evaluate string as float----------------------------------------
###---Note this isn't the safest way but the fastest
def eval_f(expr):
    """
    Evaluate expression an cast result as float
    """

    return float(eval(expr))

###---expand source path
def expand_path(path):
    """
    Expand relative and EOS path
    """

    if ":" not in path:
        if path[0] == "~":
            path = os.path.expanduser(path)
        elif "/" in path and path[0] != "/":
            path = os.path.abspath(path)
        elif "/eos/user" in path:
            path = 'root://eosuser-internal.cern.ch/'+path

    return path
