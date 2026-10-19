using System;
using System.Collections.Generic;
public static class NavigationContract {
    static Dictionary<string,object> T(string protocol,object level,object index){return new Dictionary<string,object>{{"protocol",protocol},{"level",level},{"index",index}};}
    public static void Main(){
        if(TraceNavigationWorker.TargetKey(T("USB3",0,8))!="USB3:0:8")throw new Exception("Packet identity");
        if(TraceNavigationWorker.TargetKey(T("PD",3,8))!="PD:3:8")throw new Exception("PD Transfer identity");
        if(TraceNavigationWorker.TargetKey(T("USB2",3,1386))!="USB2:3:1386")throw new Exception("legacy Transfer identity");
        foreach(var t in new[]{T("USB3",3,8),T("USB2",0,8),T("PD",2,8),T("PD",0,-1),T("PD",false,8),T("PD",0,true),T("unknown",0,8)}){
            bool rejected=false;try{TraceNavigationWorker.TargetKey(t);}catch{rejected=true;}
            if(!rejected)throw new Exception("invalid native identity accepted");
        }
        Console.WriteLine("10 native target policy checks passed");
    }
}
