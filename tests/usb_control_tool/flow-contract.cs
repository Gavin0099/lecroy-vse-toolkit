using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

// Actual form state/selection behavior. The IPC fixture never opens LeCroy.
public static class FlowContract {
    static int checks;
    static BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
    static object Get(object o,string n){return o.GetType().GetField(n,flags).GetValue(o);}
    static void Call(object o,string n,params object[] a){o.GetType().GetMethod(n,flags).Invoke(o,a);}
    static void Check(bool v,string n){checks++;if(!v)throw new Exception(n);}
    static Dictionary<string,object> Map(object o){return (Dictionary<string,object>)o;}
    static object[] Items(object o){return o is object[]?(object[])o:((ArrayList)o).ToArray();}
    [STAThread] public static void Main(string[] args){try{Run(args);}catch(Exception e){Console.WriteLine(e.ToString());Environment.ExitCode=1;}}
    static void Run(string[] args){
        var json=new JavaScriptSerializer {MaxJsonLength=16000000};
        var model=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(args[3],Encoding.UTF8));
        string id=Convert.ToString(model["analysis_id"]),folder=Path.Combine(args[2],id);Directory.CreateDirectory(folder);
        File.WriteAllText(Path.Combine(folder,"inspection.json"),json.Serialize(model),Encoding.UTF8);
        using(var f=new TraceToolEntry(args[0],args[1],args[2])){
            try{
                Call(f,"LoadModel",id);var list=(ListBox)Get(f,"candidates");var mode=(ComboBox)Get(f,"flowView");
                Check(mode.SelectedIndex==0,"default is flow");Check(list.Items.Count<=3&&list.Items.Count>0,"bounded visible flow list");
                var flow=Map(model["flow_analysis"]);string sid=Convert.ToString(flow["primary_scenario"]);Dictionary<string,object> primary=null;
                foreach(object e in Items(model["flow_items"]))if(Convert.ToString(Map(e)["scenario_id"])==sid)primary=Map(e);
                Check(((Label)Get(f,"coordinates")).Text.Contains(Convert.ToString(Map(primary["locator"])["packet_index"])),"primary uses independent phase locator");
                Check(((RichTextBox)Get(f,"summary")).Text.Contains(Convert.ToString(Map(primary["engineer_view"])["next_check"])),"plain next check visible in summary");
                Check(((Label)Get(f,"candidateStatus")).Text.Contains("不是故障"),"milestone not orange fault verdict");
                ((CheckBox)Get(f,"showAll")).Checked=true;Check(list.Items.Count==Items(model["flow_items"]).Length,"historical intervals expandable");
                mode.SelectedIndex=1;Check(list.Items.Count==Items(model["candidates"]).Length,"packet records retained");
                Check(((Label)Get(f,"coordinates")).Text.Contains("225043"),"known-case packet locator retained");
                Check(((Label)Get(f,"totals")).Text.Contains("依擷取順序"),"packet order not fake ranking");
                mode.SelectedIndex=0;Check(((Label)Get(f,"coordinates")).Text.Contains("1484298"),"phase switching restores phase anchor");
                // No TLP candidates must not hide the phase workflow.
                model["candidates"]=new object[0];model["episode_count"]=model["candidate_count_total"]=0;Map(Items(model["analyses"])[0])["episode_count"]=0;
                File.WriteAllText(Path.Combine(folder,"inspection.json"),json.Serialize(model),Encoding.UTF8);Call(f,"LoadModel",id);
                Check(list.Items.Count>0,"zero-packet model still offers phase checks");mode.SelectedIndex=1;Check(list.Items.Count==0,"empty packet layer");
                Check(((RichTextBox)Get(f,"summary")).Text.Contains("不代表整份 PCIe"),"empty layer never PASS");
                Call(f,"ResetForImport");Check(list.Items.Count==0&&Get(f,"caseId")==null,"new import clears phase identity");
            }finally{var p=(Process)Get(f,"controller");p.StandardInput.WriteLine("{\"action\":\"close\"}");p.StandardInput.Flush();Check(p.WaitForExit(5000),"fixture exits");}
        }
        Console.WriteLine("flow form assertions="+checks);
    }
}
