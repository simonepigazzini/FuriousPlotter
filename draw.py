#!/usr/bin/env python3

import sys
import re
import time
import argparse
import os
import copy
import subprocess
import importlib
import ROOT
import cfgmanager

from fp_utils import *
from plot_manager import *
from tree_manager import *

ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.ShutDown = False

def draw(cmd_opts=None):
    """
    FuriousPlotter main loop    
    """

    cfg = cfgmanager.CfgManager()
    if cmd_opts.preset != "":
        for preset in cmd_opts.preset.split(','):
            print(preset)
            cfg.ParseConfigString(preset)        
    if cmd_opts.cfg != "":
        cfg.ParseConfigFile(cmd_opts.cfg)
    if cmd_opts.mod != "":
        for config in cmd_opts.mod.split(','):
            print(config)
            cfg.ParseConfigString(config)

    if cmd_opts.debug:
        cfg.Print()    
        
    #---Load py/C++ plugins, proccess all lines before
    sys.path.insert(1, os.getcwd())
    plugin_funcs = {}
    plugins = {"py" : ['operations'], "C" : [], "so" : [], "line" : []}    
    if cfg.OptExist("draw.plugins"):        
        for plugin in cfg.GetVOpt("draw.plugins"):
            plugin = str(plugin)
            if ".py" == plugin[-3:]:
                plugins["py"].append(plugin[:-3])
            elif ".C" == plugin[-2:] or ".C+" == plugin[-3:]:
                plugins["C"].append(plugin)
            elif ".so" == plugin[-3:]:
                plugins["so"].append(plugin)
            else:
                plugins["line"].append(plugin)
    processLines(plugins["line"])
    for plugin in plugins["py"]:
        plugin_module = importlib.import_module(plugin)
        for func_name in getattr(plugin_module, 'FPOperations'):
            plugin_funcs[func_name] = getattr(plugin_module, func_name)
    for macro in plugins["C"]:
        ROOT.gROOT.LoadMacro(macro) 
    for lib in plugins["so"]:
        ROOT.gSystem.Load(lib) 

    #---Create trees with FPTreeCreator
    if cmd_opts.make_trees and cfg.OptExist("draw.trees"):
        for tree_name in cfg.GetVOpt("draw.trees"):
            printMessage("Creating <"+colors.CYAN+tree_name+colors.DEFAULT+"> TTree", 1)        
            FPTreeCreator(cfg, tree_name, plugin_funcs)

    #---Make plots with FPPlots
    #---keep track of write process running in parallel
    write_procs = []
    #---create line object for drawing custom lines
    ROOT.gROOT.ProcessLine("TLine line;")
    ROOT.gROOT.ProcessLine("TLatex latex;")
    if cfg.OptExist("draw.plots"):
        for plot_name in cfg.GetVOpt("draw.plots"):
            printMessage("Drawing <"+colors.CYAN+plot_name+colors.DEFAULT+">", 1)        
            plot = FPPlot(plot_name, cfg, plugin_funcs, cmd_opts.force_update)
            output = copy.deepcopy(plot.getOutput())
            #---write output in parallel
            writeOutput(output, write_procs)
    #---close write parallel processes
    for proc in write_procs:
        proc.join()
        
    #---Post-proc
    if cfg.OptExist("draw.postProcCommands"):
        for command in cfg.GetVOpt("draw.postProcCommands"):
            os.system(command)

    
### MAIN ###
if __name__ == "__main__":
    parser = argparse.ArgumentParser (description = 'Draw plots from ROOT files')
    parser.add_argument('-p', '--preset', type=str, default='', help='preset option passed to the config parser')
    parser.add_argument('-m', '--mod', type=str, default='', help='config file modifiers')
    parser.add_argument('-c', '--cfg', default='', help='cfg file')
    parser.add_argument('-f', '--force-update', action='store_true', default=False, help='force plots update')
    parser.add_argument('--make-trees', action='store_true', help='recreate every TTree defined in draw.trees')
    parser.add_argument('--debug', action='store_true', help='print debug information')
    
    cmd_opts = parser.parse_args()

    draw(cmd_opts=cmd_opts)
