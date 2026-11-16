using System;
using System.Collections.Generic;
public static class WorkspaceContract {
    static object A(string state,int count){return new Dictionary<string,object>{{"state",state},{"episode_count",count}};}
    public static void Main(){
        var examples=new[]{new object[]{A("not_observed",0),A("partial",0),A("not_observed",0)},
                           new object[]{A("not_observed",0),A("not_observed",0),A("analyzed",0)},
                           new object[]{A("failed",0),A("analyzed",1),A("partial",0)},
                           new object[]{A("not_observed",0),A("partial",0),A("failed",0)},
                           new object[0]};
        int[] expected={1,2,1,2,0};
        for(int n=0;n<examples.Length;n++)if(TraceToolEntry.PreferredAnalysis(examples[n])!=expected[n])throw new Exception("Wrong default protocol for case "+n);
        var pd=(Dictionary<string,object>)A("analyzed",0);pd["observation_count"]=9;
        if(TraceToolEntry.PreferredAnalysis(new object[]{A("not_observed",0),A("analyzed",0),pd})!=2)throw new Exception("PD evidence hidden behind empty analysis");
        Console.WriteLine("6 default-protocol UI policy checks passed");
    }
}
