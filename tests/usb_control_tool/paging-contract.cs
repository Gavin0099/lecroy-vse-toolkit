using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using System.Web.Script.Serialization;

// Synthetic large UI data only. Never opens native analyzers.
public static class PagingContract {
    static int checks;
    static BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
    static object Get(object o,string n){return o.GetType().GetField(n,flags).GetValue(o);}
    static void Call(object o,string n,params object[] a){o.GetType().GetMethod(n,flags).Invoke(o,a);}
    static void Check(bool v,string n){checks++;if(!v)throw new Exception(n);}
    [STAThread] public static void Main(string[] args){try{Run(args);}catch(Exception e){Console.WriteLine(e);Environment.ExitCode=1;}}
    static void Run(string[] args){
        string id=args[3],folder=Path.Combine(args[2],id);
        Check(new FileInfo(Path.Combine(folder,"inspection.json")).Length>16777216,"synthetic file exceeds legacy size");
        using(var form=new TraceToolEntry(args[0],args[1],args[2])){
            try{
                Call(form,"LoadModel",id);
                var list=(ListBox)Get(form,"candidates");
                Check(list.Items.Count==3,"primary view is three targets");
                Check(Get(form,"pageIndex")!=null,"bounded projection loaded");
                ((CheckBox)Get(form,"showAll")).Checked=true;
                Check(list.Items.Count>0&&list.Items.Count<=20,"bounded first page");
                int firstRank=Convert.ToInt32(((Dictionary<string,object>)((object[])Get(form,"cards"))[0])["rank"]);
                Call(form,"ChangePage",1);
                int secondRank=Convert.ToInt32(((Dictionary<string,object>)((object[])Get(form,"cards"))[0])["rank"]);
                Check(secondRank!=firstRank,"next page changes original rank");
                Check(((Label)Get(form,"pageLabel")).Text.StartsWith("2 /"),"page position visible");
                ((ComboBox)Get(form,"flowView")).SelectedIndex=1;
                Check(list.Items.Count==1,"packet view retained");
                Check(((Label)Get(form,"coordinates")).Text.Contains("225043"),"original packet locator retained");
                ((ComboBox)Get(form,"flowView")).SelectedIndex=0;
                Check(list.Items.Count==3,"return to first flow page");
                Call(form,"ResetForImport");
                Check(Get(form,"pageIndex")==null&&list.Items.Count==0,"new import clears prior pages");
                Check((int)Get(form,"currentPage")==0,"page offset reset");
            }finally{
                var child=(Process)Get(form,"controller");child.StandardInput.WriteLine("{\"action\":\"close\"}");child.StandardInput.Flush();
                Check(child.WaitForExit(5000),"fixture cleanup");
            }
        }
        Console.WriteLine("paging assertions="+checks);
    }
}
