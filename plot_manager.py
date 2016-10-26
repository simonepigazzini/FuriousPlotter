#!/bin/python

import sys
import re
import time
import random
import os
import subprocess
import ROOT

from fp_utils import *
from array import array
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

        self.processPads()
        
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
            ### cumpute pad rescaling if sub-frame
            pad_size = self.cfg.GetOpt(vstring)(pad_key+".size") if self.cfg.OptExist(pad_key+".size") else []
            if len(pad_size) == 4:
                pad_x_scale = float(pad_size[2])-float(pad_size[0])
                pad_y_scale = float(pad_size[3])-float(pad_size[1])
            first_histo = 0
            for histo in self.cfg.GetOpt(vstring)(pad_key+".histos") if self.cfg.OptExist(pad_key+".histos") else []:
                draw_opt = "same"
                histo_key = pad_key+"."+histo
                if histo_key not in self.histos.keys():
                    self.processHistogram(histo_key)
                self.customize(histo_key, self.histos[histo_key])
                draw_opt += self.cfg.GetOpt(std.string)(histo_key+".drawOptions") if self.cfg.OptExist(histo_key+".drawOptions") else ""
                ### rescale labels and titles if pad is a sub-frame
                pad.cd()
                if len(pad_size) == 4:
                    self.autoRescale(self.histos[histo_key], x_scale=pad_x_scale, y_scale=pad_y_scale)
                self.histos[histo_key].Draw(draw_opt)

                ### adjust maximum and minimum
                if not first_histo:
                    first_histo = histo_key
                extra_min = self.cfg.GetOpt(float)(self.name+".extraSpaceBelow") if self.cfg.OptExist(self.name+".extraSpaceBelow") else 1.
                extra_max = self.cfg.GetOpt(float)(self.name+".extraSpaceAbove") if self.cfg.OptExist(self.name+".extraSpaceAbove") else 1.
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
            self.customize(pad_key, pad)
            if len(pad_size) == 4:
                self.autoRescale(pad, x_scale=pad_x_scale, y_scale=pad_y_scale)
                
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

        if self.cfg.OptExist(self.name+".legendXY"):
            pos = self.cfg.GetOpt(vstring)(self.name+".legendXY")
        else:
            pos = [0.6, 0.6, 0.9, 0.9]

        head = self.cfg.GetOpt(self.name+".legendHeader") if self.cfg.OptExist(self.name+".legendHeader") else ""
        lg = ROOT.TLegend(float(pos[0]), float(pos[1]), float(pos[2]), float(pos[3]), head)
        lg.SetFillStyle(0)

        entries = self.cfg.GetOpt(vstring)(self.name+".legendEntries") if self.cfg.OptExist(self.name+".legendEntries") else vstring()
        for pad_key, pad in self.pads.items():
            for histo in self.cfg.GetOpt(vstring)(pad_key+".histos") if self.cfg.OptExist(pad_key+".histos") else []:
                entries.push_back(pad_key+"."+histo)
        ###---loop over entries and create an entry in the TLegend object
        for entry in entries:
            if self.cfg.OptExist(entry+".legendEntry"):
                ###---get label from cfg then parse it and process c++ calls:
                ###   - create a new namespace
                ###   - convert result of c++ call to string
                ###   - replace call with result in label
                label = self.cfg.GetOpt(std.string)(entry+".legendEntry", 0)
                for key, histo in self.histos.items():
                    for call in re.findall(r'[\%|\s+]'+key+'->\w+\([\w|\"|\,|\-|\_]+\)', label):
                        call = call.replace('%', '')
                        call.strip()
                        nspc = 'n'+''.join(random.choice('abcdefghjkilmnopqrstuvwyz0123456789') for i in range(5))
                        ROOT.gROOT.ProcessLine("namespace "+nspc+"{::TString str_value;}")
                        ROOT.gROOT.ProcessLine("namespace "+nspc+"{auto value = ::"+call+";}")
                        ROOT.gROOT.ProcessLine(nspc+"::str_value += "+nspc+"::value;")
                        ROOT.gROOT.ProcessLine("namespace "+nspc+"{struct get_value{::TString value = str_value;};}")
                        value = getattr(ROOT, nspc).get_value().value
                        match = re.search("\%\.[0-9]+[Ef]\%$", label[:label.find(call)])
                        if match != None:
                            # if '.' in value:
                            #     value = value[:value.find('.')+int(match.group(0)[2:])+1]
                            value = (match.group(0)[:-1] % float(value))
                            value = re.sub('E(.*)', r'#scale[0.75]{#times}10^{\1}', value).replace('+','')
                            value = re.sub('{0+(.*)}', r'{\1}', value)
                            label = re.sub("\%\.[0-9]+[Ef]\%"+key+"->\w+\([\w|\"|\,|\-|\_]+\)", value, label, 1)
                        else:
                            label = re.sub(key+"->\w+\([\w|\"|\,|\-|\_]+\)", value, label, 1)
                                                
                opt = self.cfg.GetOpt(std.string)(entry+".legendEntry", 1) if self.cfg.OptExist(entry+".legendEntry", 1) else "lpf"
                entry = self.cfg.GetOpt(std.string)(entry+".objName") if self.cfg.OptExist(entry+".objName") else entry
                lg.AddEntry(self.histos[entry], label, opt)
                        
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
        + call function for builtin/custom operations (efficiency, fit slices, ...)
        """        
                
        #---recursive
        func = operation[:operation.index("(")]
        if func in self.functions:            
            tokens = re.findall(".*\(.*\)|\w+", operation[operation.index("(")+1:operation.rfind(")")])
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
                if abs_path not in self.files.keys():
                    self.files[abs_path] = ROOT.TFile.Open(src_vect[0])
                histo_file = self.files[abs_path]
            # not a file: try to get it from current open file
            elif histo_file and histo_file.Get(src_vect[0]):
                srcs[alias] = histo_file.Get(src_vect[0])
                if "TTree" not in srcs[alias].ClassName() and "TGraph" not in srcs[alias].ClassName():
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

        ###---build histograms with fixed size bins 
        if self.cfg.OptExist(histo_key+".bins"):
            bins = self.cfg.GetOpt(vstring)(histo_key+".bins")
            if len(bins) == 3:
                tmp_histo = ROOT.TH1F("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]))
            elif len(bins) == 5:
                tmp_histo = ROOT.TProfile("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                              float(bins[3]), float(bins[4]), "S")
            elif len(bins) == 6:
                tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                          int(bins[3]), float(bins[4]), float(bins[5]))
            elif len(bins) == 8:
                tmp = ROOT.TProfile2D("ht_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                      int(bins[3]), float(bins[4]), float(bins[5]),
                                      float(bins[6]), float(bins[7]), "S")
                tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, int(bins[0]), float(bins[1]), float(bins[2]),
                                      int(bins[3]), float(bins[4]), float(bins[5]))
                
        ###---build histograms with variable size bins
        elif self.cfg.OptExist(histo_key+".dbins"):
            dbins = self.cfg.GetOpt(vstring)(histo_key+".dbins")
            if len(dbins) == 1 and self.cfg.OptExist(dbins[0]):
                vbins = self.cfg.GetOpt(std.vector(float))(dbins[0])
                nbins = vbins.size()-1
                tmp_histo = ROOT.TH1F("h_"+histo_obj.GetName(), histo_key, nbins, vbins.data())
            elif len(dbins) == 2 and self.cfg.OptExist(dbins[0]) and self.cfg.OptExist(dbins[1]):
                vxbins = self.cfg.GetOpt(std.vector(float))(dbins[0])
                nxbins = vxbins.size()-1
                vybins = self.cfg.GetOpt(std.vector(float))(dbins[1])
                nybins = vybins.size()-1
                tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, nxbins, vxbins.data(), nybins, vybins.data())
            elif len(dbins) == 3 and self.cfg.OptExist(dbins[0]):
                vbins = self.cfg.GetOpt(std.vector(float))(dbins[0])
                nbins = vbins.size()-1
                tmp_histo = ROOT.TProfile("h_"+histo_obj.GetName(), histo_key, nbins, vbins.data(), float(dbins[1]), float(dbins[2]))
            elif len(dbins) == 4:
                if self.cfg.OptExist(dbins[0]):
                    values = self.cfg.GetOpt(std.vector(float))(dbins[0])
                    vxbins = array('d')
                    for value in values: 
                        vxbins.append(value)
                    nxbins = values.size()-1
                    tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, int(nxbins), vxbins,
                                          int(dbins[1]), float(dbins[2]), float(dbins[3]))
                elif self.cfg.OptExist(dbins[3]):
                    values = self.cfg.GetOpt(std.vector(float))(dbins[0])
                    vybins = array('d')
                    for value in values: 
                        vybins.append(value)
                    nybins = values.size()-1
                    tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, int(dbins[0]), float(dbins[1]), float(dbins[2]),
                                          nybins, vybins)
                    
        # draw histo
        name = tmp.GetName() if 'tmp' in locals() else tmp_histo.GetName()
        var = self.cfg.GetOpt(std.string)(histo_key+".var")+">>"+name
        cut = self.cfg.GetOpt(std.string)(histo_key+".cut") if self.cfg.OptExist(histo_key+".cut") else ""
        histo_obj.Draw(var, cut, "goff")

        # convert TProfile2D in plain TH2F
        if 'tmp' in locals():
            for xbin in range(1, tmp.GetNbinsX()+1):                
                for ybin in range(1, tmp.GetNbinsY()+1):
                    tmp_histo.SetBinContent(xbin, ybin, tmp.GetBinContent(xbin, ybin))

            tmp.Delete()
                                            
        return tmp_histo

    ###---set object style---------------------------------------------
    def customize(self, key, obj):
        """
        Set style attribute of histograms
        """

        obj_definition_lines = []
        if self.cfg.OptExist(key+".customize"):
            for line in self.cfg.GetOpt(vstring)(key+".customize"):
                if line[:6] != "macro:":
                    line = "this->"+line if line[:4] != "this" else line
                else:
                    line = line[6:]                    
                for key, histo in self.histos.items():
                    if '=' in line:
                        line = line[:line.find('=')]+line[line.find('='):].replace(key, histo.GetName())
                    else:
                        line = line.replace(key, histo.GetName())
                line = line.replace("this", obj.GetName())
                line += ';'
                if '=' in line:
                    obj_definition_lines.append(line)

                ROOT.gROOT.ProcessLine(line)

        for line in obj_definition_lines:
            self.getNewObject(line)

    ###---rescale obj in sub-frame-----------------------------------
    def autoRescale(self, obj, x_scale=1, y_scale=1):
        """
        Rescale object labels and titles if object is in sub-frame
        """

        if "TPad" not in obj.ClassName():
            xaxis = obj.GetXaxis()
            xaxis.SetLabelSize(xaxis.GetLabelSize()/(x_scale*y_scale))
            xaxis.SetTitleSize(xaxis.GetTitleSize()/(x_scale*y_scale))
            yaxis = obj.GetYaxis()
            yaxis.SetLabelSize(yaxis.GetLabelSize()/(x_scale*y_scale))
            yaxis.SetTitleSize(yaxis.GetTitleSize()/(x_scale*y_scale))
            yaxis.SetTitleOffset(yaxis.GetTitleOffset()*x_scale*y_scale)
            zaxis = obj.GetZaxis()
            zaxis.SetLabelSize(zaxis.GetLabelSize()/(x_scale*y_scale))
            zaxis.SetTitleSize(zaxis.GetTitleSize()/(x_scale*y_scale))
            zaxis.SetTitleOffset(zaxis.GetTitleOffset()*x_scale*y_scale)

    ###---capture object defined in line passed as argument
    def getNewObject(self, line):
        """
        Parse line and retrive new objects appending them to:
        - current directory
        - self.histos container
        """
        
        obj_def = line[line.index("=")+1:line.rfind(")")] if ")" in line else ""
        if obj_def != "":
            var_name = line[:line.index("=")-1].split()[-1]
            tokens = re.findall("\w+", obj_def)                    
            if tokens[0] == "new":
                ROOT.gROOT.ProcessLine("gDirectory->Append("+var_name+")")
                obj_name = tokens[2]
            else:
                ROOT.gROOT.ProcessLine("gDirectory->Append(&"+var_name+")")
                obj_name = tokens[1]
            if ROOT.gDirectory.Get(obj_name):
                self.histos[obj_name] = ROOT.gDirectory.Get(obj_name)
                self.histos[var_name] = self.histos[obj_name]
