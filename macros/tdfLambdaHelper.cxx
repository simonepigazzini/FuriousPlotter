#include <string>
#include <iostream>

#include "ROOT/TDFInterface.hxx"
#include "ROOT/TDataFrame.hxx"

using namespace ROOT::Experimental::TDF;
using namespace ROOT::Detail::TDF;

TInterface<TFilterBase> lambdaForArrays(TInterface<TFilterBase>& node, std::string array, std::string index)
{
    auto def = node.Define(array+"["+index+"]", [](std::array_view<float> a, int i){return a[i];}, {array, index});
    return def;
}

TInterface<TFilterBase> lambdaForArraysInt(TInterface<TFilterBase>& node, std::string array, int index)
{
    auto def = node.Define(array+"["+std::to_string(index)+"]", [index](std::array_view<float> a){return a[index];}, {array});
    return def;
}
