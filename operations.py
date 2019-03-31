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

def Add(args, srcs):
    """
    Add histograms together:

    - works with any ROOT histogram type that implements the ``Suwm2()`` and ``Add(Class&)``

    - usage in FP cfg file: ``operations 'Add(h1, h2, [h3, ...])'``
    
    :param args: list of histograms to be added together (two or more).
    :type args: list
    :param srcs: plot sources provided by the FPPlot class.
    :type srcs: dict    
    :returns: result histogram containing the bin by bin sum of the specified sources.
    """

    name = "add_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.Sumw2()
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Add(srcs[arg])
    return tmp

def Sub(args, srcs):
    """
    Subtract histograms from the first one:

    - works with any ROOT histogram type that implements the ``Suwm2()`` and ``Add(Class&)``

    - usage in FP cfg file: ``operations 'Sub(h1, h2, [h3, ...])'``
    
    :param args: list of histograms to be combined together (two or more): the first one is the minuend the following ones are all subtrahend.
    :type args: list
    :param srcs: plot sources provided by the FPPlot class.
    :type srcs: dict    
    :returns: result histogram containing the bin by bin subtraction ``res = h1 - h2 - [h3 - ...]``.
    """

    name = "sub_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.Sumw2()
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Add(srcs[arg], -1)
    return tmp
    
def Mul(args, srcs):
    """
    Multiply histograms together:

    - works with any ROOT histogram type that implements the ``Suwm2()`` and ``Multiply(Class&)``

    - usage in FP cfg file: ``operations 'Mul(h1, h2, [h3, ...])'``
    
    :param args: list of histograms to be multiplied together (two or more).
    :type args: list
    :param srcs: plot sources provided by the FPPlot class.
    :type srcs: dict    
    :returns: result histogram containing the bin by bin multiplication of the specified sources.
    """

    name = "mul_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.Sumw2()
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Multiply(srcs[arg])
    return tmp
    
def Div(args, srcs):
    """
    Divide the first histogram by the others:

    - works with any ROOT histogram type that implements the ``Suwm2()`` and ``Divide(Class&)``

    - usage in FP cfg file: ``operations 'Div(h1, h2, [h3, ...])'``
    
    :param args: list of histograms (two or more): the first one is the dividend, the following are all divisors.
    :type args: list
    :param srcs: plot sources provided by the FPPlot class.
    :type srcs: dict    
    :returns: result histogram containing the bin by bin division: ``res = h1 / h2 [/h3 / ...]``
    """

    name = "div_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.Sumw2()
    tmp.UseCurrentStyle()
    args.pop(0)
    for arg in args:
        tmp.Divide(srcs[arg])
    return tmp

def Pow(srcs, name=None, power=2):
    """
    Compute power of bin contents for ``TH1`` and ``TH2`` histogram.
    
    - usage in FP cfg file: ``operations 'Pow(name=h1, power=2)'``    

    :param name: source histogram name.
    :type name: str
    :param power: exponent value.
    :type power: int
    """
    
    name = "pow_"+"_".join(args)
    tmp = srcs[args[0]].Clone(name)
    tmp.Sumw2()
    tmp.UseCurrentStyle()
    power = float(args[1])
    if '2' in tmp.ClassName():
        for xbin in range(1, tmp.GetNbinsX()+1):
            for ybin in range(1, tmp.GetNbinsY()+1):
                if tmp.GetBinContent(xbin, ybin) != 0:
                    error = tmp.GetBinError(xbin, ybin)*power*pow(tmp.GetBinContent(xbin, ybin), power-1)
                    tmp.SetBinContent(xbin, ybin, pow(tmp.GetBinContent(xbin, ybin), power))
                    tmp.SetBinError(xbin, ybin, error)
    else:
        for xbin in range(1, tmp.GetNbinsX()+1):
            if tmp.GetBinContent(xbin) != 0:
                error = tmp.GetBinError(xbin)*power*pow(tmp.GetBinContent(xbin), power-1)
                tmp.SetBinContent(xbin, pow(tmp.GetBinContent(xbin), power))
                tmp.SetBinError(xbin, error)

    return tmp

def Eff(srcs, num="", den=""):
    """
    Generate efficiency histogram exploiting ``TGraphAsymmErrors``. Errors are computed using ``TEfficiency``.

    - usage in FP cfg file: ``operations 'Eff(num=h1, den=h2)'``    

    :param num: efficiency numerator.
    :type num: str
    :param den: efficiency denominator.
    :type den: str
    """
                            
    tmp = ROOT.TGraphAsymmErrors(srcs[args[0]], srcs[args[1]])
    fake = ROOT.TCanvas()
    fake.cd()
    tmp.Draw("A")

    #---default range for efficiency plots
    tmp.SetMinimum(0)
    tmp.SetMaximum(1.05)

    return tmp

def TH2toTH1(srcs, name="", bins=[]):
    """
    Make 1D histogram of ``TH2`` bin contents. 

    - usage in FP cfg file: ``operations TH2toTH1(name=h1, bins=[nbins, min, max])``
    - if ``bins`` is not specified the range on the ``TH1D`` histogram will be set automatically
    
    :param name: ``TH2`` histogram name.
    :type name: str
    :param bins: 1D histogram bins.
    :type bins: list
    :returns: TH1D histogram filled with the bin content values of the input instogram.
    """

    origin = srcs[name]
    if len(bins) == 3:
        tmp = ROOT.TH1D("tmp", "", int(bins[1]), float(bins[2]), float(bins[3]))
    else:
        tmp = ROOT.TH1D("tmp", "", 100, 0, 0)

    for xbin in range(1, origin.GetNbinsX()+1):
        for ybin in range(1, origin.GetNbinsY()+1):
            if origin.GetBinContent(xbin, ybin) != 0:
                tmp.Fill(origin.GetBinContent(xbin, ybin))
    
    return tmp

def Project(srcs, name="", axis="X", min=None, max=None):
    """
    Interface to TH2::ProjectionX and TH2::ProjectionY. By default include all bins except underflow and overflow bins.
    
    - usage in FP cfg file: ``operations Project(name=h1, axis="X", min=bMin, max=bMax)``

    - args[0] = input TH2
    - args[1] = project NOT-specified axis onto specified one
    - args[2], args[3] (optional) = project including only bins between args[2] and args[3]
    """

    th2 = srcs[name]

    ### check inputs
    if "TH2" not in th2.ClassName():
        printMessage("ERROR: Project operation requires a TH2 histogram as first parameter, got"+th2.ClassName()+" instead", -1)
        return
    if axis not in ["X", "Y"]:
        printMessage("ERROR: Project operation, unsupported axis name: "+axis, -1)
        return

    ### set projected axis range
    if not min:
        min = 1
    if not max:
        max = th2.GetNbinsY() if axis == "X" else th2.GetNbinsX()
        
    ### project
    if axis == "X":
        tmp = th2.ProjectionX("_px", min, max, "eo")
    elif axis == "Y":
        tmp = th2.ProjectionY("_py", min, max, "eo")
        
    return tmp

def FitSlices(srcs, name="", axis="X", func=0, parameter="_0", min=None, max=None):
    """
    Interface to the FitSlicesX and FitSlicesY methods of ``TH2``. Returns the requested post-fit histogram.

    
    """

    ### check inputs
    if "TH2" not in th2.ClassName():
        printMessage("ERROR: FitSlices operation requires a TH2 histogram as first parameter, got"+th2.ClassName()+" instead", -1)
        return
    if axis not in ["X", "Y"]:
        printMessage("ERROR: FitSlices operation, unsupported axis name: "+axis, -1)
        return
    
    th2 = srcs[name]
    if func in srcs.keys():
        fit_func = srcs[func]
    else:
        if not min:
            min = th2.GetYaxis().GetBinLowEdge(0) if axis == "X" else th2.GetXaxis().GetBinLowEdge(0)
        if not max:
            max = th2.GetYaxis().GetBinUpEdge(th2.GetYaxis().GetLast()) if axis == "X" else th2.GetXaxis().GetBinUpEdge(th2.GetXaxis().GetLast())
            
        fit_func = ROOT.TF1("fit_slices_x_func", func.replace('"', ''), min, max)
                            
    if axis == "X":
        th2.FitSlicesX(fit_func)
    else:
        th2.FitSlicesY(fit_func)
        
    return ROOT.gDirectory.Get(th2.GetName()+parameter)

def FitSlicesX(srcs, name="", func=0, parameter="_0", min=None, max=None):
    """
    Call the fit slices method of TH2 and returns the requested post-fit histogram
    """

    FitSlices(srcs, name=name, axis="X", func=func, parameter=parameter, min=min, max=max)

def FitSlicesY(srcs, name="", func=0, parameter="_0", min=None, max=None):
    """
    Call the fit slices method of TH2 and returns the requested post-fit histogram
    """

    FitSlices(srcs, name=name, axis="Y", func=func, parameter=parameter, min=min, max=max)
    
def QuantileBinning(srcs, name, nqx=0, nqy=0):
    """
    Define ``TH2`` axis binning using quantile of projected distribution(s).
    
    """    

    h_orig = srcs[name]

    ###---compute de quantiles ranges
    hx_tmp = h_orig.ProjectionX(h_orig.GetName()+"_px", 1, h_orig.GetNbinsY())
    hy_tmp = h_orig.ProjectionY(h_orig.GetName()+"_py", 1, h_orig.GetNbinsX())
    if nqx > 0:
        nqx = nqx+1
        probs_x = array('d', [x/(nqx-1) for x in range(0, nqx)])
        quantiles_x = array('d', [0 for x in range(0, nqx)])
        hx_tmp.GetQuantiles(nqx, quantiles_x, probs_x)
        printMessage("x-axis quantile binning: ", 0)
        print(quantiles_x)
    if nqy > 0:
        nqy = nqy+1
        probs_y = array('d', [y/(nqy-1) for y in range(0, nqy)])
        quantiles_y = array('d', [0 for y in range(0, nqy)])    
        hy_tmp.GetQuantiles(nqy, quantiles_y, probs_y)
        printMessage("y-ayis quantile binning: ", 0)
        print(quantiles_y)

    ###---build new histogram
    if "TH1" in h_orig.ClassName() and nqx > 0:
        h_tmp = ROOT.TH1D("tmp", "", nqx-1, quantiles_x)
        for ibin in range(1, h_orig.GetNbinsX()+1):
            h_tmp.Fill(h_orig.GetBinCenter(ibin), h_orig.GetBinContent(ibin)) 
    elif "TH2" in h_orig.ClassName():
        if nqx > 0 and nqy > 0:
            h_tmp = ROOT.TH2D("tmp", "", nqx-1, quantiles_x, nqy-1, quantiles_y)
        elif nqx > 0:
            h_tmp = ROOT.TH2D("tmp", "",
                              nqx-1, quantiles_x,
                              h_orig.GetNbinsY(), hy_tmp.GetBinLowEdge(1), hy_tmp.GetBinLowEdge(h_orig.GetNbinsY())+1)
        elif nqy > 0:
            h_tmp = ROOT.TH2D("tmp", "",
                              h_orig.GetNbinsX(), hx_tmp.GetBinLowEdge(1), hx_tmp.GetBinLowEdge(h_orig.GetNbinsX()+1),
                              nqy-1, quantiles_y)
        for xbin in range(1, h_orig.GetNbinsX()+1):
            for ybin in range(1, h_orig.GetNbinsY()+1):
                h_tmp.Fill(hx_tmp.GetBinCenter(xbin), hy_tmp.GetBinCenter(ybin), h_orig.GetBinContent(xbin, ybin))        
    else:
        h_tmp = h_orig.Clone("tmp")

    return h_tmp

def QuantileProf(srcs, name="", qvalues=None):
    """
    Use quatiles so set asymmetric errors to standard profiles of 2D histograms. 
    Options:
    1) when only one value is specified the function calculates two quatiles: 0.5-opt/2, 0.5+opt/2
    2) the first argument must a TH2.
    """

    ### check input arguments
    if not qvalues:
        printMessage("QuintileProf: no qvalues specified", -1)
        exit(-1)
    h_orig = srcs[name]
    nbins = srcs[name].GetNbinsX()

    ### define quantiles
    if len(qvalues) == 2:
        probs = array('d', [0.5-float(qvalues)/2., 0.5, 0.5+float(qvalues)/2.])
    else:
        probs = array('d', [float(qvalues[0]), 0.5, float(qvalues[1])])
    quantiles = array('d', [0, 0, 0])

    ### create output histogram
    h_tmp = ROOT.TGraphAsymmErrors()
    
    ### compute errors for each x bin
    h_projx = h_orig.ProjectionX()
    for xbin in range(1, nbins+1):
        h_proj = h_orig.ProjectionY("_py", xbin, xbin, "o")
        if h_proj.GetEntries() > 0:
            h_proj.GetQuantiles(3, quantiles, probs)
            h_tmp.SetPoint(h_tmp.GetN(), h_projx.GetBinCenter(xbin), quantiles[1])
            h_tmp.SetPointError(h_tmp.GetN()-1, 0, 0, quantiles[1]-quantiles[0], quantiles[2]-quantiles[1])
            quantiles = array('d', [0, 0, 0])

    return h_tmp

def TH1ToGraph(srcs, name=""):
    """
    Convert TH1 histogram into TGraph
    """

    th1 = srcs[name]
    tmp = ROOT.TGraphErrors()

    if "TH1" not in th1.ClassName():
        printMessage("ERROR: TH1ToGraph, "+name+" is not a TH1 histogram: "+th1.ClassName(), -1)
        return 
    
    for ibin in range(1, th1.GetNbinsX()+1):
        tmp.SetPoint(ibin-1, th1.GetBinCenter(ibin), th1.GetBinContent(ibin))
        tmp.SetPointError(ibin-1, th1.GetBinWidth(ibin)/2., th1.GetBinError(ibin))

    return tmp

def SpectrumAwareGraph(srcs, name="", spectrum=""):
    """
    Set x position of args[0] (graph) points accordingly to args[1] (TH1) average in the same bin  
    """

    orig_gr = srcs[name]
    spectrum = srcs[spectrum]  

    if "TH1" in orig_gr.ClassName():
        orig_gr = th1_to_graph(srcs, name=name)

    px = orig_gr.GetX()
    py = orig_gr.GetY()
    ex = orig_gr.GetEX()
    ey = orig_gr.GetEY()
        
    tmp = ROOT.TGraphAsymmErrors()
    for ib in range(0, orig_gr.GetN()):
        spectrum.GetXaxis().SetRangeUser(px[ib]-ex[ib], px[ib]+ex[ib])
        mean = spectrum.GetMean()
        tmp.SetPoint(ib, mean, py[ib])
        tmp.SetPointError(ib, mean-px[ib]+ex[ib], px[ib]-mean+ex[ib], ey[ib], ey[ib])

    return tmp

def MakeHistoErrors(srcs, values="", errors=""):
    """Combine two histograms: the first one set the point value, the second the point error"""

    h_tmp = ROOT.TGraphErrors()
    for xbin in range(1, srcs[values].GetNbinsX()+1):
        h_tmp.SetPoint(xbin-1, srcs[values].GetBinCenter(xbin), srcs[values].GetBinContent(xbin))
        h_tmp.SetPointError(xbin-1, 0, srcs[errors].GetBinContent(xbin))

    return h_tmp
                          
FPOperations = [
    'Add', 'Sub', 'Mul', 'Div', 'Pow', 'Eff',
    'TH2toTH1', 'Project',
    'FitSlicesX', 'FitSlicesY',
    'QuantileBinning', 'QuantileProf',
    'SpectrumAwareGraph',
    'MakeHistoErrors'
]

