#!/bin/python

import sys
import re
import time
import argparse
import os
import subprocess
import ROOT
import draw

def add(args, srcs):
    name = "add_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    args.pop(0)
    for arg in args:
        tmp.Add(srcs[arg])
    return tmp

def sub(args, srcs):
    name = "sub_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    args.pop(0)
    for arg in args:
        tmp.Add(srcs[arg], -1)
    return tmp
    
def mul(args, srcs):
    name = "mul_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    args.pop(0)
    for arg in args:
        tmp.Multiply(srcs[arg])
    return tmp
    
def div(args, srcs):
    name = "div_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
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
                               

dictionary = dict(Add=add, Sub=sub, Mul=mul, Div=div, Eff=eff, FitSlicesX=fit_slices_x, FitSlicesY=fit_slices_y)

