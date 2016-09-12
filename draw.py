#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT
from fp_utils import *

oldargv = sys.argv[:]
sys.argv = [ '-b-' ]
sys.argv = oldargv

from collections import OrderedDict as odict
from ROOT import TH1F

###---plot container class--------------------------------------------
class FPPlot:
    """Main class: contains all the objects belonging to a plot instance"""

    ###---init function-----------------------------------------------
    def __init__(self, plot_name, cfg, plugin_funcs):
        self.name       = plot_name
        self.cfg        = cfg
        self.files      = {}
        self.histos     = odict()
        self.pads       = odict()
        self.basedir    = ""
        self.functions  = plugin_funcs
    
    ###---define pads-----------------------------------------------------
    def processPads(self):
        """Manage pads
        + create global canvas and user defined pads
        + create and draw histograms 
        """

        self.basedir = ROOT.gDirectory.CurrentDirectory()

        #---if no pad is specified, only the default global canvas is created
        #   histos defined under plot scope are attached to it
        pads_names = self.cfg.GetOpt(vstring)(self.name+".pads") if self.cfg.OptExist(self.name+".pads") else []

        self.createPad(self.name)
        for pad_name in pads_names:
            self.createPad(self.name+"."+pad_name)

        for pad_key, pad in self.pads.items():
            if not pad:
                self.createPad(pad_key)
                pad = self.pads[pad_key]
            draw_opt = "same"
            first_histo = 0
            for histo in self.cfg.GetOpt(vstring)(pad_key+".histos") if self.cfg.OptExist(pad_key+".histos") else []:
                histo_key = pad_key+"."+histo
                if histo_key not in self.histos.keys():
                    self.processHistogram(histo_key)
                self.setStyle(histo_key, self.histos[histo_key])
                draw_opt += cfg.GetOpt(std.string)(histo_key+".drawOptions") if cfg.OptExist(histo_key+".drawOptions") else ""
                pad.cd()                
                self.histos[histo_key].Draw(draw_opt)
                if not first_histo:
                    first_histo = histo_key
                extra_min = cfg.GetOpt(float)(self.name+".extraSpaceBelow") if cfg.OptExist(self.name+".extraSpaceBelow") else 1.
                extra_max = cfg.GetOpt(float)(self.name+".extraSpaceAbove") if cfg.OptExist(self.name+".extraSpaceAbove") else 1.
                if "TH1" in self.histos[histo_key].ClassName() and "TH1" in self.histos[first_histo].ClassName() and self.histos[histo_key].GetMaximum() >= self.histos[first_histo].GetMaximum():
                    self.histos[first_histo].SetAxisRange(self.histos[first_histo].GetMinimum(),
                                                          self.histos[histo_key].GetMaximum()*1.1*extra_max, "Y")
                if "TH1" in self.histos[histo_key].ClassName() and "TH1" in self.histos[first_histo].ClassName() and self.histos[histo_key].GetMinimum() <= self.histos[first_histo].GetMinimum():
                    self.histos[first_histo].SetAxisRange(self.histos[histo_key].GetMinimum()*1.1*extra_min,
                                                          self.histos[first_histo].GetMaximum(), "Y")
            #---apply style to pad
            lg = self.buildLegend()
            lg.Draw("same")
            ROOT.gPad.Update()
            self.setStyle(pad_key, pad)
                
        ###---if option 'saveAs' is specified override global option
        save_opt = self.cfg.GetOpt(vstring)(self.name+".saveAs") if self.cfg.OptExist(self.name+".saveAs") else self.cfg.GetOpt(vstring)("draw.saveAs")
        ###---save canvas if not disabled
        if "goff" not in save_opt:
            self.savePlotAs(save_opt)

    ###---create pad------------------------------------------------------
    def createPad(self, pad_name):
        """Create pad and histos"""

        self.basedir.cd()
        
        # get constructor size parameters        
        size = self.cfg.GetOpt(vstring)(pad_name+".size") if self.cfg.OptExist(pad_name+".size") else []
        if pad_name == self.name:
            if len(size) == 0:                        
                self.pads[pad_name] = ROOT.TCanvas(pad_name.replace(".", "_"))
            elif len(size) == 2:
                self.pads[pad_name] = ROOT.TCanvas(pad_name.replace(".", "_"), "", int(size[0]), int(size[1]))
            else:
                printMessage("Global canvas creation: option <size> must contain 0 or 2 values", -1)
            ROOT.gDirectory.Append(self.pads[self.name])
        elif len(size) == 4:
            self.pads[pad_name] = ROOT.TPad(pad_name.replace(".", "_"), "", float(size[0]), float(size[1]), float(size[2]), float(size[3]))
            self.pads[pad_name].Draw()
        else:
            printMessage("TPad size parameters not specified: "+pad_name, -1)
            exit(0)

    ###---legend----------------------------------------------------------
    def buildLegend(self):
        "Build legend for current plot. Entry order is fixed by cfg file"

        if cfg.OptExist(self.name+".legendXY"):
            pos = cfg.GetOpt(vstring)(self.name+".legendXY")
        else:
            pos = [0.6, 0.6, 0.9, 0.9]

        head = cfg.GetOpt(self.name+".legendHeader") if cfg.OptExist(self.name+".legendHeader") else ""
        lg = ROOT.TLegend(float(pos[0]), float(pos[1]), float(pos[2]), float(pos[3]), head)
        lg.SetFillStyle(0)

        entries = cfg.GetOpt(vstring)(self.name+".legendEntries") if cfg.OptExist(self.name+".legendEntries") else cfg.GetOpt(vstring)(self.name+".histos")
        for entry in entries:
            histo_key = self.name+"."+entry
            if cfg.OptExist(histo_key+".legendEntry", 0):
                label = cfg.GetOpt(std.string)(histo_key+".legendEntry", 0)
                opt = cfg.GetOpt(std.string)(histo_key+".legendEntry", 1) if cfg.OptExist(histo_key+".legendEntry", 1) else "lpf"
                lg.AddEntry(self.histos[histo_key].GetName(), label, opt)
                        
        return lg

    ###---Print canvas----------------------------------------------------
    def savePlotAs(self, exts):
        "Print canvas to specified file format"

        outDir = self.cfg.GetOpt("draw.outDir") if self.cfg.OptExist("draw.outDir") else "plots"
    
        subprocess.getoutput("mkdir -p "+outDir)
        for ext in exts:
            self.pads[self.name].Print(outDir+"/"+self.name+"."+ext, ext)
            
    ###---process histos--------------------------------------------------
    def processHistogram(self, histo_key):
        """Process all the histograms defined in the canvas, steering the histogram creation and drawing"""

        srcs = self.sourceParser(histo_key)
        for key in srcs:
            if srcs[key].ClassName() == "TTree":
                srcs[key] = self.makeHistogramFromTTree(srcs[key], histo_key)
            if "Graph" not in srcs[key].ClassName() and not srcs[key].GetSumw2():
                srcs[key].Sumw2()
            if not self.cfg.OptExist(histo_key+".operation"):
                if histo_key not in self.histos.keys():
                    self.histos[histo_key] = srcs[key].Clone(histo_key.replace(".", "_"))
                    if "Graph" in self.histos[histo_key].ClassName():
                        ROOT.gDirectory.Append(self.histos[histo_key])
                else:
                    self.histos[histo_key].Add(srcs[key])

        if self.cfg.OptExist(histo_key+".operation"):
            #---build line to be processed, replacing aliases        
            operation = self.cfg.GetOpt(std.string)(histo_key+".operation")
            operation = operation.replace(" ", "")
            self.histos[histo_key] = self.parseOperation(operation, srcs)
            self.histos[histo_key].SetName(histo_key.replace(".", "_"))

    ###---operations-----------------------------------------------------
    def parseOperation(self, operation, srcs):
        """
        Read operation string recursively:
        + process basic operation +-/*
        + call function for custom operations (efficiency, fit slices, ...)
        """        
                
        #---recursive
        func = operation[:operation.index("(")]
        if func in self.functions:            
            tokens = re.split("(.*),(.*)", operation[operation.index("(")+1:operation.rfind(")")])
            args = []
            for token in tokens:
                if "(" in token:
                    ret = self.parseOperation(token, srcs)
                    args.append(ret.GetName())
                    srcs[ret.GetName()] = ret
                elif token != "":
                    args.append(token)
            return self.functions[func](args, srcs) 
        
    ###---get sources----------------------------------------------------
    def sourceParser(self, histo_key):
        """
        Get histogram source(s):
        1) check if src is from file (and if has already been opened)
        2) check if src match a cfg option
        3) if so check if already loaded, otherwise process the source
        """

        srcs = {}
        histo_file = 0
        src_vect = self.cfg.GetOpt(vstring)(histo_key+".src")
        while len(src_vect) > 0:
            if ":" in src_vect[0]:
                alias = src_vect[0][0:src_vect[0].find(":")]                
                src_vect[0] = src_vect[0].replace(alias+":", "")
            else:
                alias = src_vect[0]
            ### try to build the file path
            #   1) skip grid files
            #   2) then replace ~ with home dir path (if needed)
            #   3) if root / is not the starting point and current dir to relative path
            abs_path = src_vect[0]
            if ":" not in abs_path:
                if src_vect[0][0] == "~":
                    abs_path = os.path.expanduser(src_vect[0])
                elif "/" in src_vect[0] and src_vect[0][0] != "/":
                    abs_path = os.path.abspath(src_vect[0])
            if os.path.isfile(abs_path):
                if histo_key not in self.files.keys():
                    self.files[histo_key] = ROOT.TFile.Open(src_vect[0])
                histo_file = self.files[histo_key]                
            # not a file: try to get it from current open file
            elif histo_file and histo_file.Get(src_vect[0]):
                srcs[alias] = histo_file.Get(src_vect[0])
                srcs[alias].SetDirectory(self.basedir)
            # try to get object from session workspace
            elif self.basedir.Get(src_vect[0]):
                srcs[alias] = self.basedir.Get(src_vect[0])
            # not a object in the current file: try to get it from loaded objects
            elif self.cfg.OptExist(src_vect[0]+".src"):
                if src_vect[0] not in self.histos.keys():
                    self.processHistogram(src_vect[0])
                srcs[alias] = self.histos[src_vect[0]]
            else:
                printMessage("source "+colors.CYAN+src_vect[0]+colors.DEFAULT+" not found.", -1)
                exit(0)
            src_vect.erase(src_vect.begin())

        self.basedir.cd()
        return srcs

    ###---get histogram from tree-------------------------------------------
    def makeHistogramFromTTree(self, histo_obj, histo_key):
        "Draw histograms from TTree, histogram type is guessed from specified binning"

        bins = cfg.GetOpt(vstring)(histo_key+".bins")
        if len(bins) == 1 and self.cfg.OptExist(bins[0]):
            vbins = self.cfg.GetOpt(std.vector(float))(bins[0])
            nbins = vbins.size()-1
            tmp_histo = ROOT.TH1F("h_"+histo_obj.GetName(), histo_key, nbins, vbins.data())
        if len(bins) == 3:
            tmp_histo = ROOT.TH1F("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]))
        elif len(bins) == 5:
            tmp_histo = ROOT.TProfile("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                      float(bins[3]), float(bins[4]), "S")
        elif len(bins) == 6:
            tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                  int(bins[3]), float(bins[4]), float(bins[5]))
        elif len(bins) == 8:
            tmp_histo = ROOT.TProfile2D("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                        int(bins[3]), float(bins[4]), float(bins[5]),
                                        float(bins[6]), float(bins[7]), "S")
            
        # draw histo
        var = cfg.GetOpt(std.string)(histo_key+".var")+">>"+tmp_histo.GetName()
        cut = cfg.GetOpt(std.string)(histo_key+".cut") if cfg.OptExist(histo_key+".cut") else ""
        histo_obj.Draw(var, cut, "goff")

        return tmp_histo

    ###---set histogram style---------------------------------------------
    def setStyle(self, key, obj):
        "Set style attribute of histograms"
    
        if self.cfg.OptExist(key+".graphicalOptions"):
            for gopt in self.cfg.GetOpt(vstring)(key+".graphicalOptions"):
                if gopt[:6] != "macro:":
                    gopt = "this->"+gopt if gopt[:4] != "this" else gopt
                else:
                    gopt = gopt[6:]
                gopt = gopt.replace("this", obj.GetName())
                ROOT.gROOT.ProcessLine(gopt)
    
### MAIN ###
if __name__ == "__main__":

    ROOT.gROOT.SetBatch(True)
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
    
    #---Make plots with FPPlots
    #---create line object for drawing custom lines
    ROOT.gROOT.ProcessLine("TLine line;")
    ROOT.gROOT.ProcessLine("TLatex latex;")
    for plot_name in cfg.GetOpt(vstring)("draw.plots"):
        printMessage("Drawing <"+colors.CYAN+plot_name+colors.DEFAULT+">", 1)        
        plot = FPPlot(plot_name, cfg, plugin_funcs)
        plot.processPads()

    #---Post-proc
    if cfg.OptExist("draw.postProcCommands"):
        for command in cfg.GetOpt(vstring)("draw.postProcCommands"):
            os.system(command)
            
