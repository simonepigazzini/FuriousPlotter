#!/bin/python

import sys
import re
import time
import random
import os
import copy
import ctypes
import ROOT

from plugins.yoda_reader import *
from fp_utils import *
from array import array
from collections import OrderedDict as odict
from ROOT import TH1F

###---plot container class--------------------------------------------
class FPPlot:
    """Main class: contains all the objects belonging to a plot instance"""

    ###---init function-----------------------------------------------
    def __init__(self, plot_name, cfg, plugin_funcs, force_update=False):
        self.basedir     = ROOT.gDirectory.CurrentDirectory()
        self.name        = plot_name
        self.cfg         = cfg
        self.output      = {}
        self.files       = {}        
        self.histos      = odict()
        self.updated     = {}
        self.pads        = odict()        
        self.functions   = plugin_funcs
        self.forceUpdate = force_update
        self.outDir      = self.cfg.GetOpt("draw.outDir") if self.cfg.OptExist("draw.outDir") else "plots"
        if not os.path.isdir(self.outDir):
            os.makedirs(self.outDir)
        
        ###---main loop
        self.processPads()
        
    ###---define pads-----------------------------------------------------
    def processPads(self):
        """Manage pads
        + create global canvas and user defined pads
        + create and draw histograms 
        """

        self.basedir.cd()

        #---if no pad is specified, only the default global canvas is created
        #   histos defined under plot scope are attached to it
        pads_names = self.cfg.GetOpt[stdvstring](self.name+".pads") if self.cfg.OptExist(self.name+".pads") else []

        self.createPad(self.name)
        for pad_name in pads_names:
            self.createPad(self.name+"."+pad_name)

        for pad_key, pad in self.pads.items():
            if not pad:
                self.createPad(pad_key)
                pad = self.pads[pad_key]
            ### cumpute pad rescaling if sub-frame
            pad_size = self.cfg.GetOpt[stdvstring](pad_key+".size") if self.cfg.OptExist(pad_key+".size") else []
            if len(pad_size) == 4:
                pad_x_scale = float(pad_size[2])-float(pad_size[0])
                pad_y_scale = float(pad_size[3])-float(pad_size[1])
            first_histo = 0
            for histo in self.cfg.GetOpt[stdvstring](pad_key+".histos") if self.cfg.OptExist(pad_key+".histos") else []:
                draw_opt = "same" if pad.GetListOfPrimitives().GetSize() > 0 else ""
                histo_key = pad_key+"."+histo
                if histo_key not in self.histos.keys():
                    self.processHistogram(histo_key)
                self.customize(histo_key, self.histos[histo_key])
                draw_opt += self.cfg.GetOpt(std.string)(histo_key+".drawOptions") if self.cfg.OptExist(histo_key+".drawOptions") else ""
                if 'NORM' in draw_opt or 'norm' in draw_opt:
                    if "TH1" in self.histos[histo_key].ClassName():
                        self.histos[histo_key].Scale(1./self.histos[histo_key].GetEntries())
                        draw_opt = draw_opt.replace('NORM', '')
                        draw_opt = draw_opt.replace('norm', '')
                    else:
                        draw_opt = draw_opt.replace('NORM', '')
                        draw_opt = draw_opt.replace('norm', '')

                ### rescale labels and titles if pad is a sub-frame
                pad.cd()
                if 'goff' not in draw_opt:
                    if len(pad_size) == 4:
                        self.autoRescale(self.histos[histo_key], self.updated[histo_key], x_scale=pad_x_scale, y_scale=pad_y_scale)
                    self.histos[histo_key].Draw(draw_opt)
                    ### adjust maximum and minimum
                    if not first_histo:
                        first_histo = histo_key
                    if not self.updated[histo_key]:
                        extra_min = self.cfg.GetOpt(float)(self.name+".extraSpaceBelow") if self.cfg.OptExist(self.name+".extraSpaceBelow") else 1.
                        extra_max = self.cfg.GetOpt(float)(self.name+".extraSpaceAbove") if self.cfg.OptExist(self.name+".extraSpaceAbove") else 1.
                        if "TH1" in self.histos[histo_key].ClassName() and "TH1" in self.histos[first_histo].ClassName() and self.histos[histo_key].GetMaximum() >= self.histos[first_histo].GetMaximum():
                            extra = 1.1*extra_max if self.histos[histo_key].GetMaximum()>=0 else 0.9*extra_max
                            self.histos[first_histo].SetAxisRange(self.histos[first_histo].GetMinimum(),
                                                                  self.histos[histo_key].GetMaximum()*extra, "Y")
                        if "TH1" in self.histos[histo_key].ClassName() and "TH1" in self.histos[first_histo].ClassName() and self.histos[histo_key].GetMinimum() <= self.histos[first_histo].GetMinimum():
                            extra = 1.1*extra_min if self.histos[histo_key].GetMinimum()<=0 else 0.9*extra_min
                            self.histos[first_histo].SetAxisRange(self.histos[histo_key].GetMinimum()*extra,
                                                                  self.histos[first_histo].GetMaximum(), "Y")
                        
            #---apply style to pad
            lg = self.buildLegend(pad_key)
            lg.SetName("lg")
            self.basedir.Append(lg)
            lg.Draw()
            ROOT.gPad.Update()
            self.customize(pad_key, pad)
            if len(pad_size) == 4:
                self.autoRescale(pad, False, x_scale=pad_x_scale, y_scale=pad_y_scale)                
                
        ###---if option 'saveAs' is specified override global option
        save_opt = self.cfg.GetOpt[stdvstring](self.name+".saveAs") if self.cfg.OptExist(self.name+".saveAs") else self.cfg.GetOpt[stdvstring]("draw.saveAs")
        ###---save canvas if not disabled
        if "goff" not in save_opt:
            self.savePlotAs(save_opt)

    ###---create pad------------------------------------------------------
    def createPad(self, pad_name):
        """Create pad and histos"""

        self.basedir.cd()
        
        # get constructor size parameters        
        size = self.cfg.GetOpt[stdvstring](pad_name+".size") if self.cfg.OptExist(pad_name+".size") else []
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
    def buildLegend(self, pad_key):
        "Build legend for current plot. Entry order is fixed by cfg file"

        if self.cfg.OptExist(pad_key+".legendXY"):
            pos = self.cfg.GetOpt[stdvstring](pad_key+".legendXY")
        else:
            pos = [0.6, 0.6, 0.9, 0.9]
        header = self.cfg.GetOpt(pad_key+".legendHeader") if self.cfg.OptExist(pad_key+".legendHeader") else ""
        header = self.computeValues(header)

        ###---Create legend using the buildin BuildLegend TPad method:
        ###   this is a workaround in order to be able to draw legends in different pads (probably a ROOT bug)        
        lg = self.pads[pad_key].BuildLegend(float(pos[0]), float(pos[1]), float(pos[2]), float(pos[3]))        
        lg.Clear()
        lg.SetNColumns(self.cfg.GetOpt(int)(pad_key+".legendColumns") if self.cfg.OptExist(pad_key+".legendColumns") else 1)
        lg.SetHeader(header)
        lg.SetFillStyle(self.cfg.GetOpt(int)(pad_key+".legendStyle") if self.cfg.OptExist(pad_key+".legendStyle") else 0)

        entries = self.cfg.GetOpt[stdvstring](pad_key+".legendEntries") if self.cfg.OptExist(pad_key+".legendEntries") else vstring()
        for histo in self.cfg.GetOpt[stdvstring](pad_key+".histos") if self.cfg.OptExist(pad_key+".histos") else []:
            entries.push_back(pad_key+"."+histo)
        ###---loop over entries and create an entry in the TLegend object
        for entry in entries:
            if self.cfg.OptExist(entry+".legendEntry"):
                label = self.cfg.GetOpt(std.string)(entry+".legendEntry", 0)
                label = self.computeValues(label)                                
                opt = self.cfg.GetOpt(std.string)(entry+".legendEntry", 1) if self.cfg.OptExist(entry+".legendEntry", 1) else "lpf"
                entry = self.cfg.GetOpt(std.string)(entry+".objName") if self.cfg.OptExist(entry+".objName") else entry
                lg.AddEntry(self.histos[entry], label, opt)

        return lg

    ###---Parse string and replace function calls-------------------------
    def computeValues(self, string):
        """
        Parse string and replace funtion calls with the value returned by the call.
        Returns the modified string
        """

        for key, histo in self.histos.items():            
            while True:
                calls = re.findall(r'[\%|\s+]'+key+'->\w+[\([\w|\"|\,|\-|\_]+\)|\(\)]', string)
                if not calls:
                    break
                call = calls[-1].replace('%', '')
                call.strip()
                method = call[call.find('->')+2:call.find('(')]
                args_str = call[call.find('(')+1:call.rfind(')')]
                args = args_str.split(',')
                ### try to convert values into either int or float, remove empty arguments from list
                for i,arg in enumerate(args):
                    if arg == '':
                        args.pop(i)
                    else:
                        arg = self.computeValues(arg)
                        try:
                            args[i] = int(arg) if arg.isdigit() else float(arg)
                        except ValueError:
                            continue
                value = str(getattr(histo, method)(*args))
                match = re.search("\%\.[0-9]+[Ef]\%$", string[:string.find(call)])
                if match != None:
                    value = (match.group(0)[:-1] % float(value))
                    value = re.sub('E(.*)', r'#scale[0.75]{#times}10^{\1}', value).replace('+','')
                    value = re.sub('{0+(.*)}', r'{\1}', value)
                    string = re.sub('\%\.[0-9]+[Ef]\%'+key+'->'+method+'[\([\w|\"|\,|\-|\_]+\)|\(\)]', value, string, 1)
                else:
                    string = re.sub('[\%|\s+]'+key+'->'+method+'[\([\w|\"|\,|\-|\_]+\)|\(\)]', value, string, 1)

        return string
    
    ###---Print canvas----------------------------------------------------
    def savePlotAs(self, exts):
        """
        - Print canvas to specified file format.
        - If description is specified, analyze the text searching for expressions to be evaluated.
        """

        ###---parse description string
        description = []
        for line in self.cfg.GetOpt[stdvstring](self.name+".description") if self.cfg.OptExist(self.name+".description") else []:
            description.append(self.computeValues(line))

        self.output = {'canvas'      : self.pads[self.name],
                       'basename'    : self.outDir+"/"+self.name,
                       'description' : description,
                       'exts'        : exts,
                       'cfg'         : self.cfg.GetSubCfg(self.name)
                       }

        ###---cleanup
        for path, ofile in self.files.items():
            if ofile.ClassName() == "TFile":
                ofile.Close()

    ###---retrive canvas and save directive-------------------------------
    def getOutput(self):
        """
        Returns self.output a dictionary with the canvans and output filenames.
        """

        return self.output

    ###---check if output already exist and if source is unchanged--------
    def getPreviousResult(self, histo_key):
        """
        Check if output file exist (.root) and if source has not been updated since 
        output creation.
        Return value:
        - False, None -> previous result is not current.
        - True, srcs  -> previous result is current, old histogram returned in srcs
        """

        ### previous result does not exist
        oldresult_path = expand_path(self.outDir+"/"+self.name+".root")
        if not os.path.isfile(oldresult_path):
            return False
        else:
            oldresult_time = os.path.getmtime(oldresult_path)
            ### check if configuration is different
            if oldresult_path not in self.files.keys():
                oldfile = ROOT.TFile.Open(oldresult_path)
            else:
                oldfile = self.files[oldresult_path]
            oldcfg = oldfile.Get("CfgManager")
            for critical_opt in [".src", ".var", ".cut", ".bins", ".operation"]:
                if not oldcfg.CompareOption(self.cfg, histo_key+critical_opt):
                    return False
            ### check if sources are more recent than results
            for src in self.cfg.GetOpt[stdvstring](histo_key+".src"):
                path = expand_path(src)
                if os.path.isfile(path) and os.path.getmtime(path) > oldresult_time:
                    return False
                elif path[path.find(":")+1:] in self.updated.keys() and self.updated[path[path.find(":")+1:]]:
                    return False
                
            ### old result exists and is current
            self.files[oldresult_path] = oldfile
            fields = histo_key.split(".")
            primitives = ['_'.join(fields[0:i]) for i in range(1, len(fields)+1)]            
            pad = oldfile.Get(primitives[0])
            for primitive in primitives[1:-1]:
                pad = pad.GetPrimitive(primitive)
            obj = pad.GetPrimitive(primitives[-1])
            self.histos[histo_key] = copy.deepcopy(getattr(ROOT, obj.ClassName())(obj))
            self.basedir.Append(self.histos[histo_key])
            if "TGraph" not in self.histos[histo_key].ClassName():
                self.histos[histo_key].SetDirectory(self.basedir)
            
            return True
        
    ###---process histos--------------------------------------------------
    def processHistogram(self, histo_key):
        """
        Process all the histograms defined in the canvas, steering the histogram creation and drawing
        If the plot already exist and only style changes are requested (through <customize> and <legendEntry>
        and <drawOptions> options in the cfg) load previous histogram instead of reprocessing the sources.
        """

        ### check if previous result is current
        self.updated[histo_key] = None if self.forceUpdate else self.getPreviousResult(histo_key)
        self.basedir.cd()
        if not self.updated[histo_key]:
            ### process sources
            srcs = self.sourceParser(histo_key)
            print(srcs)
            for key in srcs:
                if srcs[key].ClassName() == "TTree" and self.cfg.OptExist(histo_key+".var"):
                    srcs[key] = self.makeHistogramFromTTree(srcs[key], histo_key)                    
                if not any(rtype in srcs[key].ClassName() for rtype in ('TTree', 'Graph', 'TF1')) and not srcs[key].GetSumw2():
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
                self.histos[histo_key] = self.operationParser(operation, srcs)
                self.histos[histo_key].SetName(histo_key.replace(".", "_"))
                if "Graph" in self.histos[histo_key].ClassName():
                    ROOT.gDirectory.Append(self.histos[histo_key])

    ###---operations-----------------------------------------------------
    def operationParser(self, operation, srcs):
        """
        Read operation string recursively:
        + call function for builtin/custom operations (efficiency, fit slices, ...)
        """        
                
        #---recursive
        func = operation[:operation.index("(")]
        if func in self.functions:            
            if '=' not in operation[operation.index("(")+1:operation.rfind(")")]:
                tokens = re.findall('\"[^,]+\"|.*\(.*\)|[\m-\w\.]+', operation[operation.index("(")+1:operation.rfind(")")])
                args = []
                for token in tokens:
                    if "(" in token:
                        ret = self.operationParser(token, srcs)
                        args.append(ret.GetName())
                        srcs[ret.GetName()] = ret
                    elif token != "":
                        args.append(token)
                return self.functions[func](args, srcs)
            else:
                args = operation[operation.index("(")+1:operation.rfind(")")]
                kwargs = {}
                while len(args) > 0:
                    pnts = [m.start()+1 for m in re.finditer('[^=]=[^=]', args)]
                    if len(pnts) > 1:
                        pnts = [pnts[0], args.rfind(',', pnts[0], pnts[1])]
                    else:
                        pnts.append(len(args))
                    key = args[:pnts[0]]
                    value = args[pnts[0]+1:pnts[1]]
                    kwargs[key] = value
                    if value[0] == '(' and value[-1] == ')':
                        ret = self.operationParser(value, srcs)
                        kwargs[key] = ret.GetName()
                        srcs[ret.GetName()] = ret
                    args = args[pnts[1]+1:] if pnts[1] != len(args) else ''
                return self.functions[func](srcs, **kwargs)
        
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
        src_vect = self.cfg.GetOpt[stdvstring](histo_key+".src")
        while len(src_vect) > 0:
            if ":" in src_vect[0]:
                alias = src_vect[0][0:src_vect[0].find(":")]                
                src_vect[0] = src_vect[0].replace(alias+":", "")
            else:
                alias = src_vect[0]
            ### check if source is a file
            abs_path = expand_path(src_vect[0])
            if os.path.isfile(abs_path) or "/eos/user" in src_vect[0]:
                if abs_path not in self.files.keys():
                    ### file is a ROOT file
                    if ".root" in abs_path:
                        self.files[abs_path] = ROOT.TFile.Open(abs_path)
                        ### get primitives objects from all the canvas stored in the file
                        for fkey in self.files[abs_path].GetListOfKeys():
                            fobj = self.files[abs_path].Get(fkey.GetName())                        
                            if "TCanvas" in fobj.ClassName():
                                for primitive in fobj.GetListOfPrimitives():
                                    c_name = primitive.GetName()
                                    if any(rtype in c_name for rtype in ('TFrame', 'TPave')):
                                        continue
                                    replica_cnt = 1
                                    while self.basedir.Get(primitive.GetName()+"_"+str(replica_cnt)):
                                        replica_cnt = replica_cnt + 1
                                    primitive.SetName(primitive.GetName()+"_"+str(replica_cnt))
                                    self.basedir.Append(fobj.GetPrimitive(primitive.GetName()))
                    ### yoda file
                    elif ".yoda" in abs_path:
                        if ":" in src_vect[1]:
                            alias = src_vect[1][0:src_vect[1].find(":")]                
                            src_vect[1] = src_vect[1].replace(alias+":", "")
                        else:
                            alias = src_vect[1]
                        srcs[alias] = readYODA(abs_path, src_vect[1])
                        src_vect.erase(src_vect.begin()+1)
                    ### txt file (load data with TTree::ReadFile). TTree is stored both in self.files and srcs
                    else:
                        self.files[abs_path] = ROOT.TTree()
                        ### check if next src is a branch descriptor
                        branch_desc = ''
                        #delimiter = ' '
                        if len(src_vect)>1 and src_vect[1].count(":")>1:
                            branch_desc = src_vect[1]
                        self.files[abs_path].ReadFile(abs_path, branch_desc)
                        srcs[alias] = self.files[abs_path]
                        src_vect.erase(src_vect.begin()+1)
                if abs_path in self.files and  "File" in self.files[abs_path].ClassName():
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
            # last attempt
            else:
                # function (TF1) definition
                func = ROOT.TF1(alias, src_vect[0])
                if func.IsValid():
                    frange = self.cfg.GetOpt(std.vector(float))(histo_key+".bins") if self.cfg.OptExist(histo_key+".bins") else []
                    if len(frange) > 1:
                        func.SetRange(frange[0], frange[1])
                    func.SetLineWidth(2)
                    func.SetTitle()
                    srcs[alias] = func                    
                else:
                    # bad source
                    printMessage("WARNING: source "+colors.CYAN+src_vect[0]+colors.DEFAULT+" not found.", 0)
                    
            src_vect.erase(src_vect.begin())

        self.basedir.cd()

        ###---No source found -> ERROR -> exit
        if not len(srcs):
            printMessage("No source found.", -1)
            exit(0)
            
        return srcs

    ###---get histogram from tree-------------------------------------------
    def makeHistogramFromTTree(self, histo_obj, histo_key):
        "Draw histograms from TTree, histogram type is guessed from specified binning"

        ###---build histograms with fixed size bins 
        if self.cfg.OptExist(histo_key+".bins"):
            bins = self.cfg.GetOpt[stdvstring](histo_key+".bins")
            if len(bins) == 3:
                tmp_histo = ROOT.TH1F("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]))
            elif len(bins) == 5:
                tmp_histo = ROOT.TProfile("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                              eval_f(bins[3]), eval_f(bins[4]))
            elif len(bins) == 6:
                try:
                    tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                          eval_i(bins[3]), eval_f(bins[4]), eval_f(bins[5]))
                except ValueError:
                    tmp_histo = ROOT.TProfile("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                              eval_f(bins[3]), eval_f(bins[4]), bins[5])                    
            elif len(bins) == 8:
                tmp = ROOT.TProfile2D("ht_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                      eval_i(bins[3]), eval_f(bins[4]), eval_f(bins[5]),
                                      eval_f(bins[6]), eval_f(bins[7]))
                tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                      eval_i(bins[3]), eval_f(bins[4]), eval_f(bins[5]))
            elif len(bins) == 9:
                try:
                    tmp_histo = ROOT.TH3F("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                      eval_i(bins[3]), eval_f(bins[4]), eval_f(bins[5]), eval_i(bins[6]), eval_f(bins[7]), eval_f(bins[8]))
                except ValueError:
                    tmp = ROOT.TProfile2D("ht_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                          eval_i(bins[3]), eval_f(bins[4]), eval_f(bins[5]),
                                          eval_f(bins[6]), eval_f(bins[7]), bins[8])
                    tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, eval_i(bins[0]), eval_f(bins[1]), eval_f(bins[2]),
                                          eval_i(bins[3]), eval_f(bins[4]), eval_f(bins[5]))
                
        ###---build histograms with variable size bins
        elif self.cfg.OptExist(histo_key+".dbins"):
            dbins = self.cfg.GetOpt[stdvstring](histo_key+".dbins")
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
                vxbins = array('d')
                for value in vbins: 
                    vxbins.append(value)
                nbins = vbins.size()-1
                tmp_histo = ROOT.TProfile("h_"+histo_obj.GetName(), histo_key, nbins, vxbins, eval_f(dbins[1]), eval_f(dbins[2]))
            elif len(dbins) == 4:
                if self.cfg.OptExist(dbins[0]):
                    values = self.cfg.GetOpt(std.vector(float))(dbins[0])
                    vxbins = array('d')
                    for value in values: 
                        vxbins.append(value)
                    nxbins = values.size()-1
                    tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, nxbins, vxbins,
                                          eval_i(dbins[1]), eval_f(dbins[2]), eval_f(dbins[3]))
                elif self.cfg.OptExist(dbins[3]):
                    values = self.cfg.GetOpt(std.vector(float))(dbins[0])
                    vybins = array('d')
                    for value in values: 
                        vybins.append(value)
                    nybins = values.size()-1
                    tmp_histo = ROOT.TH2F("h_"+histo_obj.GetName(), histo_key, eval_i(dbins[0]), eval_f(dbins[1]), eval_f(dbins[2]),
                                          nybins, vybins)
                    
        ###---no binning specified
        else:
            name = "h_"+histo_obj.GetName()
                    
        # draw histo
        if 'name' not in locals():
            name = tmp.GetName() if 'tmp' in locals() else tmp_histo.GetName()
        var = self.cfg.GetOpt(std.string)(histo_key+".var")+">>"+name
        cut = ""
        if self.cfg.OptExist(histo_key+".cut"):
            for next_cut in self.cfg.GetOpt[stdvstring](histo_key+".cut"):                
                cut += next_cut
        histo_obj.Draw(var, cut, "goff")

        # get histogram if binning was not specified
        if 'tmp_histo' not in locals():
            tmp_histo = ROOT.gDirectory.Get(name)
        
        # convert TProfile2D in plain TH2F
        if 'tmp' in locals():
            for xbin in range(1, tmp.GetNbinsX()+1):                
                for ybin in range(1, tmp.GetNbinsY()+1):
                    tmp_histo.SetBinContent(xbin, ybin, tmp.GetBinContent(xbin, ybin))
                    tmp_histo.SetBinError(xbin, ybin, tmp.GetBinError(xbin, ybin))

            tmp.Delete()

        return tmp_histo

    ###---set object style---------------------------------------------
    def customize(self, key, obj):
        """
        Set style attribute of histograms
        """

        obj_definition_lines = []
        if self.cfg.OptExist(key+".customize"):
            for line in self.cfg.GetOpt[stdvstring](key+".customize"):
                line = self.computeValues(line)
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
                if obj.ClassName() == "TPad":
                    obj.Draw()
                
        for line in obj_definition_lines:
            self.getNewObject(line)

    ###---rescale obj in sub-frame-----------------------------------
    def autoRescale(self, obj, is_updated, x_scale=1, y_scale=1):
        """
        Rescale object labels and titles if object is in sub-frame
        """

        x_scale = x_scale if x_scale!=0 else 1
        y_scale = y_scale if y_scale!=0 else 1        
        if "TPad" not in obj.ClassName() and not is_updated:
            xaxis = obj.GetXaxis()
            xaxis.SetLabelSize(xaxis.GetLabelSize()/(x_scale*y_scale))
            xaxis.SetTitleSize(xaxis.GetTitleSize()/(x_scale*y_scale))
            yaxis = obj.GetYaxis()
            yaxis.SetLabelSize(yaxis.GetLabelSize()/(x_scale*y_scale))
            yaxis.SetTitleSize(yaxis.GetTitleSize()/(x_scale*y_scale))
            yaxis.SetTitleOffset(yaxis.GetTitleOffset()*x_scale*y_scale)
            if 'TH2' in obj.ClassName():
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
        obj_def = "" if '"' in line[:line.index("=")] else obj_def
        if obj_def != "":
            var_name = line[:line.index("=")-1].split()[-1]
            tokens = re.findall("\w+", obj_def)
            if tokens[0] == "new" and ROOT.gROOT.ProcessLine("gDirectory->Append("+var_name+")")==0:
                obj_name = tokens[2]
            elif ROOT.gROOT.ProcessLine("gDirectory->Append(&"+var_name+")")==0:
                obj_name = tokens[1]
            if "obj_name" in locals() and ROOT.gDirectory.Get(obj_name):
                self.histos[obj_name] = ROOT.gDirectory.Get(obj_name)
                self.histos[var_name] = self.histos[obj_name]
