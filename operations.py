#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT

from fp_utils import *
from array import array

def add(args, srcs):
    name = "add_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Add(srcs[arg])
    return tmp

def sub(args, srcs):
    name = "sub_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Add(srcs[arg], -1)
    return tmp
    
def mul(args, srcs):
    name = "mul_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Multiply(srcs[arg])
    return tmp
    
def div(args, srcs):
    name = "div_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Divide(srcs[arg])
    return tmp

def eff(args, srcs):
    """Exploit TGraphAsymErrors to generate a efficiency histogram with the right errors"""
                            
    tmp = ROOT.TGraphAsymmErrors(srcs[args[0]], srcs[args[1]])
    fake = ROOT.TCanvas()
    fake.cd()
    tmp.Draw("A")

    #---default range for efficiency plots
    tmp.SetMinimum(0)
    tmp.SetMaximum(1.05)

    return tmp

def fit_slices_x(args, srcs):
    """Call the fit slices method of TH2 and returns the requested post-fit histogram"""

    parameter = "_0" if len(args)<2 else "_"+args[1]
    fit_func = 0 if len(args)<3 else srcs[args[2]]
    srcs[args[0]].FitSlicesX(fit_func)

    return ROOT.gDirectory.Get(srcs[args[0]].GetName()+parameter)

def fit_slices_y(args, srcs):
    """Call the fit slices method of TH2 and returns the requested post-fit histogram"""

    parameter = "_0" if len(args)<2 else "_"+args[1]
    fit_func = 0 if len(args)<3 else srcs[args[2]]
    srcs[args[0]].FitSlicesY(fit_func)

    return ROOT.gDirectory.Get(srcs[args[0]].GetName()+parameter)
                               
def quantile_binning(args, srcs):
    """Define axis binning using quantile of projected distribution(s)"""    

    ###---get quantiles and axis options from agrs
    if len(args) == 2:
        nqx = nqy = int(args[1])
    elif len(args) == 3:
        if args[2] == 'X':
            nqx = int(args[1])
            nqy = 0
        elif args[2] == 'Y':
            nqx = 0
            nqy = int(args[1])
        else:
            printMessage("WARNING: unsupported axis specified ("+args[1]+")", -1)
    elif len(args) == 5:
        if args[2] == 'X' and args[4] == 'Y':
            nqx = int(args[1])
            nqy = int(args[3])
        elif args[2] == 'Y' and args[4] == 'X':
            nqx = int(args[3])
            nqy = int(args[1])
        else:
            printMessage("WARNING: unsupported axis specified ("+args[2]+"/"+args[4]+")", -1)

    ###---compute de quantiles ranges
    hx_tmp = srcs[args[0]].ProjectionX(srcs[args[0]].GetName()+"_px", 1, srcs[args[0]].GetNbinsY())
    hy_tmp = srcs[args[0]].ProjectionY(srcs[args[0]].GetName()+"_py", 1, srcs[args[0]].GetNbinsX())
    if nqx != 0:
        nqx = nqx+1
        probs_x = array('d', [x/(nqx-1) for x in range(0, nqx)])
        quantiles_x = array('d', [0 for x in range(0, nqx)])
        hx_tmp.GetQuantiles(nqx, quantiles_x, probs_x)
        printMessage("x-axis quantile binning: ", 0)
        print(quantiles_x)
    if nqy != 0:
        nqy = nqy+1
        probs_y = array('d', [y/(nqy-1) for y in range(0, nqy)])
        quantiles_y = array('d', [0 for y in range(0, nqy)])    
        hy_tmp.GetQuantiles(nqy, quantiles_y, probs_y)
        printMessage("y-ayis quantile binning: ", 0)
        print(quantiles_y)

    ###---build new histogram
    if "TH1" in srcs[args[0]].ClassName() and nqx != 0:
        h_tmp = ROOT.TH1D("tmp", "", nqx-1, quantiles_x)
        for ibin in range(1, srcs[args[0]].GetNbinsX()+1):
            h_tmp.Fill(srcs[args[0]].GetBinCenter(ibin), srcs[args[0]].GetBinContent(ibin)) 
    elif "TH2" in srcs[args[0]].ClassName():
        if nqx != 0 and nqy != 0:
            h_tmp = ROOT.TH2D("tmp", "", nqx-1, quantiles_x, nqy-1, quantiles_y)
        elif nqx != 0:
            h_tmp = ROOT.TH2D("tmp", "",
                             nqx-1, quantiles_x,
                              srcs[args[0]].GetNbinsY(), hy_tmp.GetBinLowEdge(1), hy_tmp.GetBinLowEdge(srcs[args[0]].GetNbinsY())+1)
        elif nqy != 0:
            h_tmp = ROOT.TH2D("tmp", "",
                             srcs[args[0]].GetNbinsX(), hx_tmp.GetBinLowEdge(1), hx_tmp.GetBinLowEdge(srcs[args[0]].GetNbinsX()+1),
                             nqy-1, quantiles_y)
        for xbin in range(1, srcs[args[0]].GetNbinsX()+1):
            for ybin in range(1, srcs[args[0]].GetNbinsY()+1):
                h_tmp.Fill(hx_tmp.GetBinCenter(xbin), hy_tmp.GetBinCenter(ybin), srcs[args[0]].GetBinContent(xbin, ybin))        
    else:
        h_tmp = srcs[args[0]].Clone("tmp")

    return h_tmp
                
dictionary = dict(Add=add, Sub=sub, Mul=mul, Div=div, Eff=eff, FitSlicesX=fit_slices_x, FitSlicesY=fit_slices_y,
                  QuantileBinning=quantile_binning)

