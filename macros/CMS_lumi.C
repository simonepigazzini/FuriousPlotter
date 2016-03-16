#include "TPad.h"
#include "TLatex.h"
#include "TLine.h"
#include "TBox.h"
#include "TASImage.h"
#include <iostream>

void CMS_lumi(TPad* pad, std::string period, int iPosX, TString extraText="",
              bool outOfFrame=false, bool is2DCOLZ=false)
{
    //
    // Global variables
    //

    TString cmsText     = "CMS";
    float cmsTextFont   = 62;  // default is helvetic-bold

    float extraTextFont = 52;  // default is helvetica-italics

    // text sizes and text offsets with respect to the top frame
    // in unit of the top margin size
    float lumiTextSize     = 0.6;
    float lumiTextOffset   = 0.2;
    float cmsTextSize      = 0.75;
    float cmsTextOffset    = 0.1;  // only used in outOfFrame version

    float relPosX    = 0.045;
    float relPosY    = 0.035;
    float relExtraDX = 1.1;
    float relExtraDY = 1.2;

    // ratio of "CMS" and extra text size
    float extraOverCmsTextSize  = 0.76;

    std::map<std::string, TString> lumi_map;

    bool drawLogo      = false;

    lumi_map["13TeV"] = "3.3 fb^{-1} (13 TeV)";
    lumi_map["13TeV_4T"] = "2.7 fb^{-1} (13 TeV)";
    lumi_map["13TeV_0T"] = "0.6 fb^{-1} (13 TeV, 0T)";
    lumi_map["8TeV"] = "19.7 fb^{-1} (8 TeV)" ;
    lumi_map["7TeV"] = "5.1 fb^{-1} (7 TeV)";
    lumi_map["Comb_7_8"] = lumi_map["7TeV"]+" + "+lumi_map["8TeV"];
    lumi_map["Comb_7_8_13"] = "#scale[0.85]{"+lumi_map["7TeV"]+" + "+lumi_map["8TeV"]+" + "+lumi_map["13TeV"]+"}";

    pad->SetBottomMargin(0.13);
    pad->SetLeftMargin(0.18);
    if(is2DCOLZ)
    {
        TGaxis::SetMaxDigits(4);
        pad->SetTopMargin(0.07);
        pad->SetRightMargin(0.15);
    }
    else
    {
        pad->SetTopMargin(0.08);
        pad->SetRightMargin(0.05);
    }
    
    int alignY_=3;
    int alignX_=2;
    if( iPosX/10==0 ) alignX_=1;
    if( iPosX==0    ) alignX_=1;
    if( iPosX==0    ) alignY_=1;
    if( iPosX/10==1 ) alignX_=1;
    if( iPosX/10==2 ) alignX_=2;
    if( iPosX/10==3 ) alignX_=3;
    //if( iPosX == 0  ) relPosX = 0.12;
    int align_ = 10*alignX_ + alignY_;

    float H = pad->GetWh();
    float W = pad->GetWw();
    float l = pad->GetLeftMargin();
    float t = pad->GetTopMargin();
    float r = pad->GetRightMargin();
    float b = pad->GetBottomMargin();
    //  float e = 0.025;

    pad->cd();
 
    TString lumiText = "";
    if(lumi_map.find(period) != lumi_map.end())
        lumiText = lumi_map[period];
    else
        lumiText = period;
   
    TLatex latex;
    latex.SetNDC();
    latex.SetTextAngle(0);
    latex.SetTextColor(kBlack);    

    float extraTextSize = extraOverCmsTextSize*cmsTextSize;

    latex.SetTextFont(42);
    latex.SetTextAlign(31); 
    latex.SetTextSize(lumiTextSize*t);    
    latex.DrawLatex(1-r,1-t+lumiTextOffset*t,lumiText);

    if(iPosX==0)
        cmsText += "#scale[0.76]{#bf{#it{ "+extraText+"}}}";
    if( outOfFrame )
    {
        latex.SetTextFont(cmsTextFont);
        latex.SetTextAlign(11); 
        latex.SetTextSize(cmsTextSize*t);    
        latex.DrawLatex(l,1-t+lumiTextOffset*t,cmsText);
    }
  
    pad->cd();

    float posX_=0;
    if( iPosX%10<=1 )
    {
        posX_ =   l + relPosX*(1-l-r);
    }
    else if( iPosX%10==2 )
    {
        posX_ =  l + 0.5*(1-l-r);
    }
    else if( iPosX%10==3 )
    {
        posX_ =  1-r - relPosX*(1-l-r);
    }
    float posY_ = 1-t - relPosY*(1-t-b);
    if( !outOfFrame )
    {
        if( drawLogo )
	{
            posX_ =   l + 0.045*(1-l-r)*W/H;
            posY_ = 1-t - 0.045*(1-t-b);
            float xl_0 = posX_;
            float yl_0 = posY_ - 0.15;
            float xl_1 = posX_ + 0.15*H/W;
            float yl_1 = posY_;
            TASImage* CMS_logo = new TASImage("CMS-BW-label.png");
            TPad* pad_logo = new TPad("logo","logo", xl_0, yl_0, xl_1, yl_1 );
            pad_logo->Draw();
            pad_logo->cd();
            CMS_logo->Draw("X");
            pad_logo->Modified();
            pad->cd();
	}
        else
	{
            latex.SetTextFont(cmsTextFont);
            latex.SetTextSize(cmsTextSize*t);
            latex.SetTextAlign(align_);
            latex.DrawLatex(posX_, posY_, cmsText);
            if( extraText != "" ) 
	    {
                latex.SetTextFont(extraTextFont);
                latex.SetTextAlign(align_);
                latex.SetTextSize(extraTextSize*t);
                latex.DrawLatex(posX_, posY_- relExtraDY*cmsTextSize*t, extraText);
	    }
	}
    }
    else if(extraText != "" && iPosX != 0)
    {
        latex.SetTextFont(extraTextFont);
        latex.SetTextSize(extraTextSize*t);
        latex.SetTextAlign(align_);
        latex.DrawLatex(posX_, posY_, extraText);      
    }

    pad->Update();
    
    return;
}
