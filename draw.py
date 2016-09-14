#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT

from fp_utils import *
from plot_manager import *
from tree_manager import *

oldargv = sys.argv[:]
sys.argv = [ '-b-' ]
sys.argv = oldargv

### MAIN ###
if __name__ == "__main__":

    ROOT.gROOT.SetBatch(True)
    if ROOT.gSystem.Load("CfgManagerDict.so") == -1:
        ROOT.gSystem.Load("CfgManager/lib/CfgManagerDict.so")
    
    parser = argparse.ArgumentParser (description = 'Draw plots from ROOT files')
    parser.add_argument('-m', '--mod', type=str, default='', help='config file modifiers')
    parser.add_argument('-c', '--cfg', default='', help='cfg file')
    parser.add_argument('--make-trees', action='store_true', help='recreate every TTree defined in draw.trees')
    parser.add_argument('--debug', action='store_true', help='print debug information')
    
    cmd_opts = parser.parse_args()

    cfg = ROOT.CfgManager()
    if cmd_opts.cfg != "":
        cfg.ParseConfigFile(cmd_opts.cfg)
    if cmd_opts.mod != "":
        for config in cmd_opts.mod.split(','):
            print(config)
            cfg.ParseConfigString(config)

    if cmd_opts.debug:
        cfg.Print()    
        
    #---Load py/C++ plugins(for preproc, style and postproc)
    sys.path.insert(1, os.getcwd())
    plugin_funcs = {}
    plugins = {"py" : ['operations'], "C" : [], "so" : [], "line" : []}    
    if cfg.OptExist("draw.plugins"):        
        for plugin in cfg.GetOpt(vstring)("draw.plugins"):
            if ".py" == plugin[-3:]:
                plugins["py"].append(plugin[:-3])
            elif ".C" == plugin[-2:]:
                plugins["C"].append(plugin)
            elif ".so" == plugin[-3:]:
                plugins["so"].append(plugin)
            else:
                plugins["line"].append(plugin)
    for plugin in plugins["py"]:
        plugin_module = __import__(plugin)        
        for key, func in getattr(plugin_module, 'dictionary').items():
            plugin_funcs[key] = func
    for macro in plugins["C"]:
        ROOT.gROOT.LoadMacro(macro) 
    for lib in plugins["so"]:
        ROOT.gSystem.Load(lib) 
    processLines(plugins["line"])

    #---Create trees with FPTreeCreator
    if cmd_opts.make_trees and cfg.OptExist("draw.trees"):
        for tree_name in cfg.GetOpt(vstring)("draw.trees"):
            printMessage("Creating <"+colors.CYAN+tree_name+colors.DEFAULT+" TTree>", 1)        
            FPTreeCreator(cfg, tree_name, plugin_funcs)

    #---Make plots with FPPlots
    #---create line object for drawing custom lines
    ROOT.gROOT.ProcessLine("TLine line;")
    ROOT.gROOT.ProcessLine("TLatex latex;")
    for plot_name in cfg.GetOpt(vstring)("draw.plots"):
        printMessage("Drawing <"+colors.CYAN+plot_name+colors.DEFAULT+">", 1)        
        plot = FPPlot(plot_name, cfg, plugin_funcs)
        
    #---Post-proc
    if cfg.OptExist("draw.postProcCommands"):
        for command in cfg.GetOpt(vstring)("draw.postProcCommands"):
            os.system(command)
            
