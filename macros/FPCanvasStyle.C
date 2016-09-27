#include "TPad.h"
#include "TLatex.h"
#include "TLine.h"
#include "TBox.h"
#include "TASImage.h"
#include <iostream>

void FPCanvasStyle(TPad* pad, std::string left_text="", std::string right_text="", int iPosX=0, TString extraText="",
                   bool outOfFrame=false, bool is2DCOLZ=false)
{
    //
    // Global variables
    //

    TString leftText     = left_text;
    float leftTextFont   = 62;  // default is helvetic-bold

    float extraTextFont = 52;  // default is helvetica-italics

    // text sizes and text offsets with respect to the top frame
    // in unit of the top margin size
    float rightTextSize     = 0.6;
    float rightTextOffset   = 0.2;
    float leftTextSize      = 0.75;
    float leftTextOffset    = 0.1;  // only used in outOfFrame version

    float relPosX    = 0.045;
    float relPosY    = 0.035;
    float relExtraDX = 1.1;
    float relExtraDY = 1.2;

    // ratio of "CMS" and extra text size
    float extraOverCmsTextSize  = 0.76;

    bool drawLogo      = false;

    pad->SetBottomMargin(0.13);
    pad->SetLeftMargin(0.18);
    pad->SetTopMargin(0.08);
    pad->SetRightMargin(0.05);
    if(is2DCOLZ)
    {
        TGaxis::SetMaxDigits(4);
        pad->SetTopMargin(0.07);
        pad->SetRightMargin(0.17);
        pad->SetLeftMargin(0.15);
        for(auto obj : *pad->GetListOfPrimitives())
        {
            auto obj_name = TString(obj->ClassName());
            if(obj_name.Contains("2"))
            {
                TPaletteAxis* palette =
                    (TPaletteAxis*)((TH2*)gDirectory->Get(obj->GetName()))->GetListOfFunctions()->FindObject("palette");
                palette->SetX1NDC(0.835);
                palette->SetX2NDC(0.875);
                palette->SetY1NDC(0.13);
                palette->SetY2NDC(0.93);
                gPad->Modified();
                gPad->Update();
            }
        }
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
 
    TString rightText = right_text;
   
    TLatex latex;
    latex.SetNDC();
    latex.SetTextAngle(0);
    latex.SetTextColor(kBlack);    

    float extraTextSize = extraOverCmsTextSize*leftTextSize;

    latex.SetTextFont(42);
    latex.SetTextAlign(31); 
    latex.SetTextSize(rightTextSize*t);    
    latex.DrawLatex(1-r,1-t+rightTextOffset*t,rightText);

    if(iPosX==0)
        leftText += "#scale[0.76]{#bf{#it{ "+extraText+"}}}";
    if( outOfFrame )
    {
        latex.SetTextFont(leftTextFont);
        latex.SetTextAlign(11); 
        latex.SetTextSize(leftTextSize*t);    
        latex.DrawLatex(l,1-t+rightTextOffset*t,leftText);
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
            latex.SetTextFont(leftTextFont);
            latex.SetTextSize(leftTextSize*t);
            latex.SetTextAlign(align_);
            latex.DrawLatex(posX_, posY_, leftText);
            if( extraText != "" ) 
	    {
                latex.SetTextFont(extraTextFont);
                latex.SetTextAlign(align_);
                latex.SetTextSize(extraTextSize*t);
                latex.DrawLatex(posX_, posY_- relExtraDY*leftTextSize*t, extraText);
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
