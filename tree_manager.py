#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT
from  fp_utils import *

###---TTree manager class---------------------------------------------
class FPTreeCreator:
    """This class is an interface to a generic TTree: it automaticcaly handles the Branch I/O"""

    def __init__(self, cfg, key, plugin_funcs):    
        self.key       = key
        self.cfg       = cfg
        self.variables = {}
        self.classes   = []
        self.basetypes = ['float', 'double', 'int', 'unsigned', 'short', 'bool', 'long']
        self.basedir = ROOT.gDirectory.CurrentDirectory()        
        
        ROOT.gSystem.Load("DynamicTTreeDict.so")

        for tkey in (cfg.GetOpt(vstring)(key+".inputs") if cfg.OptExist(key+".inputs") else []):
            self.loadTree(tkey)

        self.basedir.cd()
        self.createOutTree()
                
    def createOutTree(self):
        """Create the new TTree"""

        cname = cfg.GetOpt(std.string)(self.key+".class") if cfg.OptExist(self.key+".class") else 'fp_'+self.key.replace(".", "_")
        name = cfg.GetOpt(std.string)(self.key+".treeName") if cfg.OptExist(self.key+".treeName") else 't_'+self.key.replace(".", "_")

        ###---Load list of variables
        data_table = '#define DATA_TABLE '
        data_vect_table = '#define DATA_VECT_TABLE '
        data_class_table = '#define DATA_CLASS_TABLE '
        for line in cfg.GetOpt(vstring)(self.key+".variables") if cfg.OptExist(self.key+".variables") else []:
            v_name = self.readVariable(line)
            v_type = self.variables[v_name]['type']
            v_len = self.variables[v_name]['size']
            if ("_t" == v_type[-2:] or (ctype in v_type for ctype in self.basetypes)) and v_len == 1:
                data_table += ' \\\n DATA('+v_type+", "+v_name+")"
            elif v_len > 1:
                data_vect_table += ' \\\n DATA('+v_type+", "+v_name+", "+str(v_len)+")"
            else:
                data_class_table += ' \\\n DATA('+v_type+", "+v_name+")"            

        self.makeDynTTree(self.key, cname, name, data_table, data_vect_table, data_class_table)
        
        ###---Fill new tree:
        ###   1) automatically with values specified in the variables declaration
        ###   2) processing a user defined scope
        if not self.cfg.OptExist(self.key+".process"):
            print("TODO")
        else:
            proc_lines = self.cfg.GetOpt(vstring)(self.key+".process")
            proc = '\n'.join(proc_lines)            
            ROOT.gROOT.ProcessLine(proc)

        new_tree = self.basedir.Get(name)
        tfile = ROOT.TFile.Open(cfg.GetOpt(std.string)(self.key+".file"), 'RECREATE')
        new_tree.SetDirectory(tfile)
        new_tree.Write()
        tfile.Close()

    def readVariable(self, line):
        """Parse declaration of a single variable during the creation of a new tree"""

        ###---1) split variable declaration into type, name and value
        ###   2) check if declaration defines an array
        declaration = line.split('=')
        vtype = declaration[0].split()[0].strip()
        vname = declaration[0].split()[1].strip()
        value = declaration[1].strip() if len(declaration) > 1 else '0'
        if vname[-1:] == ']':
            vsize = vname[vname.find('[')+1:-1]
            vname = vname[:vname.find('[')]
        else:
            vsize = 1

        self.variables[vname] = {'type' : vtype, 'size' : int(vsize), 'value' : value}

        return vname
            
    def loadTree(self, key):
        """Reads existing tree and creates a DynamicTree for each one"""

        cname = cfg.GetOpt(std.string)(key+".class") if cfg.OptExist(key+".class") else 'fp_'+key.replace(".", "_")
        tname = cfg.GetOpt(std.string)(key+".treeName")
        tfile = ROOT.TFile.Open(cfg.GetOpt(std.string)(key+".file"), 'READ')
        ttree = tfile.Get(tname)
        ttree.SetDirectory(self.basedir)
        ttree.SetName('t_'+key.replace(".", "_"))
        tfile.Close()

        ###---Get list of branches to be loaded from cfg, otherwise get whole list of branches
        branches = []
        if cfg.OptExist(key+".branches"):
            branches_names = cfg.GetOpt(vstring)(key+".branches")
            for branch in branches_names:
                branches.append(ttree.GetBranch(branch))
        else:
            branches = ttree.GetListOfBranches()
        ###---Setup the data table for the call to DynamicTTree
        data_table = '#define DATA_TABLE '
        data_vect_table = '#define DATA_VECT_TABLE '
        data_class_table = '#define DATA_CLASS_TABLE '
        for branch in branches:
            b_leaf = branch.GetLeaf(branch.GetName())
            b_type = b_leaf.GetTypeName()
            b_len  = b_leaf.GetLen()
            if "_t" == b_type[-2:] and b_len == 1:
                data_table += ' \\\n DATA('+b_type+", "+branch.GetName()+")"
            elif b_len > 1:
                data_vect_table += ' \\\n DATA('+b_type+", "+branch.GetName()+", "+str(b_len)+")"
            else:
                data_class_table += ' \\\n DATA('+b_type+", "+branch.GetName()+")"

        self.makeDynTTree(key, cname, ttree.GetName(), data_table, data_vect_table, data_class_table)

    def makeDynTTree(self, key, cname, tname, data_table, data_vect_table, data_class_table):
        """Create the DynamicTTree interface"""

        self.basedir.cd()
        
        ###---Create class and dictionary if needed
        if cname not in self.classes:
            self.classes.append(cname)
            ROOT.gROOT.ProcessLine('#include "DynamicTTreeBase.h"')
            ROOT.gROOT.ProcessLine('#define DYNAMIC_TREE_NAME '+cname)
            ROOT.gROOT.ProcessLine(data_table)
            ROOT.gROOT.ProcessLine(data_vect_table)
            ROOT.gROOT.ProcessLine(data_class_table)
            ROOT.gROOT.ProcessLine('#include \"DynamicTTreeInterface.h\"')
            ROOT.gROOT.ProcessLine('#pragma link C++ class '+cname+'+;')
            ROOT.gROOT.ProcessLine('#undef DYNAMIC_TREE_NAME')
            ROOT.gROOT.ProcessLine('#undef DATA_TABLE')
            ROOT.gROOT.ProcessLine('#undef DATA_VECT_TABLE')
            ROOT.gROOT.ProcessLine('#undef DATA_CLASS_TABLE')

        ###---Create DynamicTTree instance
        if self.basedir.Get(tname):
            ROOT.gROOT.ProcessLine(cname+'* '+key.replace(".", "_")+' = new '+cname+'('+tname+');')
        else:
            ROOT.gROOT.ProcessLine(cname+'* '+key.replace(".", "_")+' = new '+cname+'("'+tname+'","'+tname+'");')
### MAIN ###
if __name__ == "__main__":

    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.Reset()
    if ROOT.gSystem.Load("CfgManagerDict.so") == -1:
        ROOT.gSystem.Load("CfgManager/lib/CfgManagerDict.so")
    
    parser = argparse.ArgumentParser (description = 'Draw plots from ROOT files')
    parser.add_argument('-m', '--mod', type=str, default='', help='config file modifiers')
    parser.add_argument('-c', '--cfg', default='', help='cfg file')
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
    
    #---Make plots with FPPlots
    for plot_name in cfg.GetOpt(vstring)("draw.trees"):
        FPTreeCreator(cfg, plot_name, plugin_funcs)
