#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT
import draw

###---TTree manager class---------------------------------------------
class TreeCreator:
    """This class is an interface to a generic TTree: it automaticcaly handles the Branch I/O"""

    def __init__(self, cfg, name):
        self.dyn_trees = {}
        self.name      = name
        self.cfg       = cfg

        ROOT.gSystem.Load("DynamicTTreeDict.so")

        #for tree in cfg.GetOpt
        
    def createDynTree(self, key):
        """Reads existing tree and creates a DynamicTree for each one"""

        tname = cfg.GetOpt(std.string)(key+".treeName")
        tfile = ROOT.TFile.Open(cfg.GetOpt(std.string)(key+".inputFile"), 'READ')
        ttree = tfile.Get(tname)

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
                data_table += ' \ \n DATA('+b_type+", "+branch.GetName()+")"
            elif b_len > 1:
                data_vect_table += ' \ \n DATA('+b_type+", "+branch.GetName()+", "+b_len+")"
            else:
                data_class_table += ' \ \n DATA('+b_type+", "+branch.GetName()+")"
                
        ###---Create the DynamicTTree interface
        ROOT.gROOT.ProcessLine('#include "DynamicTTreeBase.h"')
        ROOT.gROOT.ProcessLine('#define DYNAMIC_TREE_NAME '+tname)
        ROOT.gROOT.ProcessLine(data_table)
        ROOT.gROOT.ProcessLine(data_vect_table)
        ROOT.gROOT.ProcessLine(data_class_table)
        ROOT.gROOT.ProcessLine('#include \"DynamicTTreeInterface.h\"')
        ROOT.gROOT.ProcessLine('#pragma link C++ class '+tname+';')

