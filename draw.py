#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT

oldargv = sys.argv[:]
sys.argv = [ '-b-' ]
sys.argv = oldargv

from ROOT import TH1F
from ROOT import std

vstring = std.vector(std.string)

class colors:
    GREEN = "\033[1;32m"
    RED = "\033[1;31m"
    CYAN = "\033[1;34m"
    DEFAULT = "\033[0;10m"

###---message logger--------------------------------------------------
def printMessage(msg, msg_type):
    "Print colored information message"

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
    "Process single lines of C++ source code. Useful for on-the-fly style settings"
    
    for line in lines:
        ROOT.gROOT.ProcessLine(line)

###---build efficiency histogram--------------------------------------
def makeEfficiencyHisto(cfg, histos, histo_file, histo_key):
    "Exploit TGraphAsymErrors to generate a efficiency histogram with the right errors"

    ###SBAGLIATO!
    if cfg.OptExist(histo_key+".src", 2):
        num = histo_file.Get(cfg.GetOpt(std.string)(histo_key+".src", 1))
        den = histo_file.Get(cfg.GetOpt(std.string)(histo_key+".src", 2))
    else:
        histo_obj = histo_file.Get(cfg.GetOpt(std.string)(histo_key+".src", 1))                    
        if histo_obj.ClassName() != "TTree":
            printMessage(histo_obj+" is not of type TTree", -1)
            exit(0)
            
        bins = cfg.GetOpt(vstring)(histo_key+".bins")
        num = ROOT.TH1F("num", histo_key, int(bins[0]), float(bins[1]), float(bins[2]))
        den = ROOT.TH1F("den", histo_key, int(bins[0]), float(bins[1]), float(bins[2]))
        if "Xaxis" not in histos.keys():
            histos["Xaxis"] = ROOT.TH1F("Xaxis", cfg.GetOpt(histo_key+".title"), int(bins[0]), float(bins[1]), float(bins[2]))
            ROOT.gDirectory.Append(histos["Xaxis"])
            setStyle(cfg, histo_key, histos["Xaxis"])
            
        var = cfg.GetOpt(std.string)(histo_key+".var")
        cut = cfg.GetOpt(std.string)(histo_key+".cut")
        sel = cfg.GetOpt(std.string)(histo_key+".selection")

        printMessage("efficiency of: "+sel+" && ["+cut+"]", 0)
        histo_obj.Project("num", var, sel+" && "+cut)
        histo_obj.Project("den", var, cut)

        # add eff histo to histograms list
        histos[histo_key] = ROOT.TGraphAsymmErrors(num, den)
        histos[histo_key].SetName(histo_key.replace(".", "_"))
        ROOT.gDirectory.Append(histos[histo_key])

        # apply graphical options
        setStyle(cfg, histo_key, histos[histo_key])

        # fixed range for efficiency plots
        histos[histo_key].SetMinimum(0)
        histos[histo_key].SetMaximum(1.05)        

        num.Delete()
        den.Delete()
        
###---build efficiency histogram--------------------------------------
def makeSlicesHisto(cfg, histos, histo_file, histo_key, name, axis):
    "Exploit TGraphAsymErrors to generate a efficiency histogram with the right errors"
    
    histo_obj = histo_file.Get(cfg.GetOpt(std.string)(histo_key+".src", 1))                    
    if histo_obj.ClassName() != "TTree":
        printMessage(histo_obj+" is not of type TTree", -1)
        exit(0)

    bins = cfg.GetOpt(vstring)(histo_key+".bins")
    if len(bins) < 6:
        printMessage("bins should contains 6 elements: nbinsx, xmin, xmax, nbinsy, ymin, ymax", -1)
        exit(0)
        
    h2D = ROOT.TH2D(name, histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                    int(bins[3]), float(bins[4]), float(bins[5]))

    # draw 2D histo
    var = cfg.GetOpt(std.string)(histo_key+".var")+">>"+name
    cut = cfg.GetOpt(std.string)(histo_key+".cut")
    histo_obj.Draw(var, cut)

    if axis == "X":
        h2D.FitSlicesX()
        param = cfg.GetOpt(std.string)(histo_key+".fitParam")        
        histos[histo_key] = ROOT.TH1D(ROOT.gDirectory.Get(name+"_"+param))        
    elif axis == "Y":
        h2D.FitSlicesY()
        param = cfg.GetOpt(std.string)(histo_key+".fitParam")
        histos[histo_key] = ROOT.TH1D(ROOT.gDirectory.Get(name+"_"+param))

    # apply graphical options
    setStyle(cfg, histo_key, histos[histo_key])
                        
    h2D.Delete()
        
###---get histogram from tree-------------------------------------------
def drawHistoFromTTree(cfg, histos, histo_obj, histo_key, name):
    "Draw histograms from TTree, histogram type is guessed from specified binning"
    
    bins = cfg.GetOpt(vstring)(histo_key+".bins")
    if len(bins) == 3:
        histos[histo_key] = ROOT.TH1F(name, histo_key, int(bins[0]), float(bins[1]), float(bins[2]))
    elif len(bins) == 5:
        histos[histo_key] = ROOT.TProfile(name, histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                          float(bins[3]), float(bins[4]))
    elif len(bins) == 6:
        histos[histo_key] = ROOT.TH2F(name, histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                      int(bins[3]), float(bins[4]), float(bins[5]))
    elif len(bins) == 8:
        histos[histo_key] = ROOT.TProfile2D(name, histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                            int(bins[3]), float(bins[4]), float(bins[5]),
                                            float(bins[6]), float(bins[7]))

    # draw histo
    var = cfg.GetOpt(std.string)(histo_key+".var")+">>"+name
    cut = cfg.GetOpt(std.string)(histo_key+".cut") if cfg.OptExist(histo_key+".cut") else ""
    histo_obj.Draw(var, cut)

    # apply graphical options
    setStyle(cfg, histo_key, histos[histo_key])

    # detach from original TFile
    histos[histo_key].SetDirectory(0)

        
###---set histogram style---------------------------------------------
def setStyle(cfg, key, histo):
    "Set style attribute of histograms"
    
    if cfg.OptExist(key+".graphicalOptions"):
        for gopt in cfg.GetOpt(vstring)(key+".graphicalOptions"):
            ROOT.gROOT.ProcessLine(histo.GetName()+"->"+gopt)

###---legend----------------------------------------------------------
def buildLegend(cfg, plot, histos, key_max):
    "Build legend for current plot. Entry order is fixed by cfg file"

    if cfg.OptExist(plot+".legendXY"):
        pos = cfg.GetOpt(vstring)(plot+".legendXY")
    elif histos[key_max].ClassName() == "TH1F":
        left_edge = histos[key_max].GetXaxis().GetXmin()
        right_edge = histos[key_max].GetXaxis().GetXmax()
        max_pos = histos[key_max].GetBinCenter(histos[key_max].GetMaximumBin())
        if abs(max_pos-left_edge) < abs(right_edge-max_pos):
            max_pos = (max_pos-left_edge)/(right_edge-left_edge)+ROOT.gStyle.GetPadLeftMargin()
            pos = [max_pos+0.05, 0.6, 0.9, 0.9]
        else:
            max_pos = (max_pos-left_edge)/(right_edge-left_edge)+ROOT.gStyle.GetPadLeftMargin()
            pos = [0.05+ROOT.gStyle.GetPadLeftMargin(), 0.6, max_pos-0.2, 0.9]
    else:
        pos = [0.6, 0.6, 0.9, 0.9]

    head = cfg.GetOpt(plot+".legendHeader") if cfg.OptExist(plot+".legendHeader") else ""
    lg = ROOT.TLegend(float(pos[0]), float(pos[1]), float(pos[2]), float(pos[3]), head)
    lg.SetFillStyle(0)

    entries = cfg.GetOpt(vstring)(plot+".legendEntries") if cfg.OptExist(plot+".legendEntries") else cfg.GetOpt(vstring)(plot+".histos")
    for entry in entries:
        histo_key = plot+"."+entry
        if cfg.OptExist(histo_key+".legendEntry", 0):
            label = cfg.GetOpt(std.string)(histo_key+".legendEntry", 0)
            opt = cfg.GetOpt(std.string)(histo_key+".legendEntry", 1) if cfg.OptExist(histo_key+".legendEntry", 1) else "lpf"
            lg.AddEntry(histos[histo_key].GetName(), label, opt)

    return lg
    
###---Finalize canvas-------------------------------------------------
def finalizeCanvas(cnv, cfg, plot):
    "Finalize canvas: macro executed within this function must take a TPad* as first argument"

    for post_proc in cfg.GetOpt(vstring)(plot+".postProc"):
        load = cfg.GetOpt(post_proc+".load") if cfg.OptExist(post_proc+".load") else cfg.GetOpt(post_proc+".macro")+".C"
        macro = cfg.GetOpt(post_proc+".macro")
        line = macro+"("+cnv.GetName()
        for arg in cfg.GetOpt(vstring)(post_proc+".arguments"):
            line += ","+arg
        line += ")"

        printMessage(line, 0)
        ROOT.gROOT.LoadMacro(load)
        ROOT.gROOT.ProcessLine(line)

###---Print canvas----------------------------------------------------
def saveCanvasAs(cnv, cfg, name):
    "Print canvas to specified file format"

    outDir = cfg.GetOpt("draw.outDir") if cfg.OptExist("draw.outDir") else "plots"
    
    subprocess.getoutput("mkdir -p "+outDir)
    for ext in cfg.GetOpt(vstring)("draw.saveAs"):
        cnv.Print(outDir+"/"+name+"."+ext, ext)
        
###---main function---------------------------------------------------
def main():
    
    ROOT.gROOT.SetBatch(True)
    ROOT.gSystem.Load("CfgManagerDict.so")
    
    parser = argparse.ArgumentParser (description = 'Draw plots from ROOT files')
    parser.add_argument('-m', '--mod', type=str, default='', help='config file modifiers')
    parser.add_argument('-c', '--cfg', default='', help='cfg file')
    
    args = parser.parse_args()

    cfg = ROOT.CfgManager()
    if args.cfg != "":
        cfg.ParseConfigFile(args.cfg)
    if args.mod != "":
        for config in args.mod.split(','):
            print(config)
            cfg.ParseConfigString(config)

    cfg.Print()

    # LOAD PLUGINS (for preproc, style and postproc)
    if cfg.OptExist("draw.pluginMacros"):
        processLines(cfg.GetOpt(vstring)("draw.pluginMacros"))

    # GET THE HISTOGRAMS
    cfg.GetOpt("draw.plots")
    cfg.GetOpt(std.string)("draw.plots")
    cfg.GetOpt(float)("draw.plots")
    for plot in cfg.GetOpt(vstring)("draw.plots"):
        printMessage("Drawing <"+colors.CYAN+plot+colors.DEFAULT+">", 1)
        if cfg.OptExist(plot+".preProc"):
            processLines(cfg.GetOpt(vstring)(plot+".preProc"))
        c1 = ROOT.TCanvas("cnv_"+plot)
        plot_type = cfg.GetOpt(vstring)(plot+".type") if cfg.OptExist(plot+".type") else ""
        histos={}
        histo_files={}
        key_max=""
        key_min=""
        for histo in cfg.GetOpt(vstring)(plot+".histos"):
            histo_key = plot+"."+histo
            if ROOT.gDirectory.GetName()=="Rint" or ROOT.gDirectory.GetName() != cfg.GetOpt(std.string)(histo_key+".src"):
                histo_files[histo_key] = ROOT.TFile.Open(cfg.GetOpt(std.string)(histo_key+".src"))
                histo_file = histo_files[histo_key]
            if not histo_file:
                printMessage("file "+colors.CYAN+cfg.GetOpt(std.string)(histo_key+".src")+colors.DEFAULT+" not found.", -1)

            # efficiency plot
            if "eff" in plot_type:
                printMessage("Efficiency histogram", 1)

                makeEfficiencyHisto(cfg, histos, histo_file, histo_key)

                key_max = "Xaxis"

            # slices plots
            if "x-slices" in plot_type:
                printMessage("Fit slices histogram", 1)

                makeSlicesHisto(cfg, histos, histo_file, histo_key, plot+"_"+histo, "X")

            if "y-slices" in plot_type:
                printMessage("Fit slices histogram", 1)

                makeSlicesHisto(cfg, histos, histo_file, histo_key, plot+"_"+histo, "Y")

            # multiple graphs
            if "graphs" in plot_type:
                if not histos["mg"]:
                    histos["mg"] = ROOT.TMultigraph("mg", "")

                # add graph
                ROOT.gDirectory.Append(histo_obj)
                setStyle(cfg, histo_key, histo_obj)
                histos["mg"].Add(histo_obj)
                histo_key = "mg"                
                
            # plain plot
            if len(plot_type) == 0:
                histo_obj = histo_file.Get(cfg.GetOpt(std.string)(histo_key+".src", 1))
                # Draw from TTree
                if histo_obj.ClassName() == "TTree":
                    drawHistoFromTTree(cfg, histos, histo_obj, histo_key, plot+"_"+histo)
                # get has it is from source file
                elif "TGraph" in histo_obj.ClassName():
                    ROOT.gDirectory.Append(histo_obj)
                    setStyle(cfg, histo_key, histo_obj)
                    histos[histo_key] = histo_obj.Clone()
                    histos[histo_key].SetName(plot+"_"+histo)
                else:
                    histos[histo_key] = histo_obj                    
                    # apply graphical options
                    setStyle(cfg, histo_key, histos[histo_key])
                    # detach from original file
                    histos[histo_key].SetDirectory(0)

            # save histograms with the max/min values
            if key_max == "" or ("eff" not in plot_type and "Graph" not in histo_obj.ClassName()
                                 and histos[histo_key].ClassName() == histos[key_max].ClassName()
                                 and histos[histo_key].GetMaximum() > histos[key_max].GetMaximum()):
                key_max = histo_key
            if key_min == "" or ("eff" not in plot_type and "Graph" not in histo_obj.ClassName()
                                 and histos[histo_key].ClassName() == histos[key_min].ClassName()
                                 and histos[histo_key].GetMinimum() < histos[key_min].GetMinimum()):
                key_min = histo_key

            # set histo title
            histos[histo_key].SetTitle(cfg.GetOpt(std.string)(histo_key+".title") if cfg.OptExist(histo_key+".title") else "")
            
        # DRAW CANVAS
        c1.cd()
        draw_opt = cfg.GetOpt(std.string)(key_max+".drawOptions") if cfg.OptExist(key_max+".drawOptions") else ""            
        if "eff" in plot_type:
            print(histos[key_max], key_max)
            histos[key_max].SetLineColor(0)
            histos[key_max].SetLineStyle(0)
            histos[key_max].Draw()
            # set X axis range
            bins = cfg.GetOpt(vstring)(histo_key+".bins")
            histos[key_max].GetXaxis().SetRangeUser(float(bins[1]), float(bins[2]))
            # add reference line
            line = ROOT.TLine(float(bins[1]), 1, float(bins[2]), 1)
            line.SetLineColor(ROOT.kGray)
            line.SetLineWidth(2)
            line.SetLineStyle(7)
            line.Draw("same")
            draw_opt += "same"

        min_val = histos[key_min].GetMinimum()
        min_val = min_val*cfg.GetOpt(float)(plot+".extraSpaceBelow") if cfg.OptExist(plot+".extraSpaceBelow") else min_val
        max_val = histos[key_max].GetMaximum()
        max_val = max_val*cfg.GetOpt(float)(plot+".extraSpaceAbove") if cfg.OptExist(plot+".extraSpaceAbove") else max_val
        for histo in cfg.GetOpt(vstring)(plot+".histos"):
            histo_key = plot+"."+histo
            if "eff" in plot_type and histo_key == key_max:
                continue
            if "eff" not in plot_type:
                axis = "Y" if histos[histo_key].ClassName() in ["TH1F", "TProfile"] else "Z"
                # set default min/max
                if "TGraph" not in histos[histo_key].ClassName():
                    histos[histo_key].SetAxisRange(min_val, max_val*1.2, axis)                
            if cfg.OptExist(histo_key+".drawOptions"):
                draw_opt += cfg.GetOpt(std.string)(histo_key+".drawOptions")
            if cfg.OptExist(histo_key+".norm"):
                norm = cfg.GetOpt(float)(histo_key+".norm")
                histos[histo_key].DrawNormalized(draw_opt, norm)
            else:
                histos[histo_key].Draw(draw_opt)
            draw_opt = "same"

        # LEGEND
        lg = ROOT.TLegend(buildLegend(cfg, plot, histos, key_max))

        lg.Draw("same")
            
        # POST PROC (on the canvas)
        if cfg.OptExist(plot+".postProc"):
            finalizeCanvas(c1, cfg, plot)
        saveCanvasAs(c1, cfg, plot)

        # cleanup
        for key in histos:
            histos[key].Delete()

### MAIN ###
if __name__ == "__main__":
    main()
    

