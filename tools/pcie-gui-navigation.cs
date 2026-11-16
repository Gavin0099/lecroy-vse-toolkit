// Product navigation command. No coordinates, keyboard injection, or attach to
// an arbitrary desktop window. Parent validates COM trace and Packet first.
using System;
using System.Diagnostics;
using System.IO;
using System.Collections.Generic;
using System.Threading;
using System.Windows.Automation;
using System.Web.Script.Serialization;

public static class PcieGuiNavigation {
    static string Label(AutomationElement e) { return e.Current.Name.Replace("&", "").Split('\t')[0].Trim(); }
    static AutomationElement Named(AutomationElement root,string name,int pid) {
        var found=new List<AutomationElement>();
        // The verified MFC MenuBar is a direct child of the top-level toolbar
        // pane. Do not traverse the trace/document or Link Tracker subtree:
        // UIA providers can spend the whole parent timeout in that traversal.
        var bars=new List<AutomationElement>();
        foreach(AutomationElement child in root.FindAll(TreeScope.Children,Condition.TrueCondition)) {
            if(child.Current.ProcessId!=pid)continue;
            if(Label(child)=="MenuBar")bars.Add(child);
            if(child.Current.ControlType!=ControlType.Pane&&child.Current.ControlType!=ControlType.ToolBar)continue;
            foreach(AutomationElement e in child.FindAll(TreeScope.Children,new PropertyCondition(AutomationElement.NameProperty,"MenuBar")))
                if(e.Current.ProcessId==pid&&!bars.Exists(x=>Automation.Compare(x,e)))bars.Add(e);
        }
        foreach(AutomationElement bar in bars)
            foreach(AutomationElement e in bar.FindAll(TreeScope.Children,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.MenuItem)))
                if(e.Current.ProcessId==pid&&Label(e)==name&&!found.Exists(x=>Automation.Compare(x,e)))found.Add(e);
        if(found.Count==0)return null;
        if(found.Count!=1)throw new InvalidOperationException("MENU_NOT_UNIQUE: "+name+" ("+found.Count+")");
        if(!found[0].Current.IsEnabled)throw new InvalidOperationException("MENU_DISABLED: "+name);
        return found[0];
    }
    [MTAThread] public static int Main(string[] args) {
        var result=new Dictionary<string,object>();
        try {
            if(args.Length!=3&&!(args.Length==4&&args[3]=="check"))throw new ArgumentException("Expected owned PID, creation FILETIME, executable path");
            int pid=int.Parse(args[0]);long birth=long.Parse(args[1]);
            using(var process=Process.GetProcessById(pid)) {
                Console.Error.WriteLine("ownership");
                if(process.StartTime.ToUniversalTime().ToFileTimeUtc()!=birth||!String.Equals(Path.GetFullPath(process.MainModule.FileName),Path.GetFullPath(args[2]),StringComparison.OrdinalIgnoreCase)||!String.Equals(process.ProcessName,"PETracer",StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("OWNERSHIP_CHANGED");
                process.Refresh();if(process.MainWindowHandle==IntPtr.Zero)throw new InvalidOperationException("NO_MAIN_WINDOW");
                var root=AutomationElement.FromHandle(process.MainWindowHandle);
                Console.Error.WriteLine("window");
                if(root.Current.ProcessId!=pid||!root.Current.IsEnabled)throw new InvalidOperationException("MAIN_WINDOW_BLOCKED");
                foreach(AutomationElement e in AutomationElement.RootElement.FindAll(TreeScope.Children,new PropertyCondition(AutomationElement.ProcessIdProperty,pid))) {
                    object pattern;
                    if(e.TryGetCurrentPattern(WindowPattern.Pattern,out pattern)&&((WindowPattern)pattern).Current.IsModal)throw new InvalidOperationException("MODAL_WINDOW");
                }
                if(args.Length==4) {Console.WriteLine("{\"status\":\"ready\"}");return 0;}
                object wp;
                if(root.TryGetCurrentPattern(WindowPattern.Pattern,out wp)) {
                    var window=(WindowPattern)wp;
                    if(window.Current.WindowInteractionState!=WindowInteractionState.ReadyForUserInteraction)throw new InvalidOperationException("WINDOW_NOT_READY");
                    // This is the tool-owned analysis window. Maximizing also
                    // recovers PETracer's stale/off-screen restored placement.
                    if(window.Current.WindowVisualState!=WindowVisualState.Maximized)window.SetWindowVisualState(WindowVisualState.Maximized);
                }
                Console.Error.WriteLine("find_search");
                AutomationElement search=null;var menuWait=Stopwatch.StartNew();
                while(search==null&&menuWait.ElapsedMilliseconds<2000){search=Named(root,"Search",pid);if(search==null)Thread.Sleep(100);}
                if(search==null)throw new InvalidOperationException("SEARCH_MENU_NOT_FOUND");object action;
                Console.Error.WriteLine("open_search");
                Exception openError=null;
                // Some MFC providers block Invoke until the popup closes. Keep
                // the command on its own background thread; the helper process
                // has a hard parent timeout and never sends input elsewhere.
                var opener=new Thread(delegate() {try {
                    object openAction;
                    if(search.TryGetCurrentPattern(ExpandCollapsePattern.Pattern,out openAction))((ExpandCollapsePattern)openAction).Expand();
                    else if(search.TryGetCurrentPattern(InvokePattern.Pattern,out openAction))((InvokePattern)openAction).Invoke();
                    else throw new InvalidOperationException("SEARCH_PATTERN_UNAVAILABLE");
                }catch(Exception ex){openError=ex;}});
                opener.IsBackground=true;opener.Start();
                // MFC popup menus can be separate owned top-level UIA elements.
                var matches=new List<AutomationElement>();var wait=Stopwatch.StartNew();
                while(matches.Count==0&&wait.ElapsedMilliseconds<4000) {
                    Console.Error.WriteLine("find_command");
                    var menus=new List<AutomationElement>();
                    foreach(AutomationElement e in root.FindAll(TreeScope.Children,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Menu)))menus.Add(e);
                    foreach(AutomationElement e in AutomationElement.RootElement.FindAll(TreeScope.Children,new AndCondition(new PropertyCondition(AutomationElement.ProcessIdProperty,pid),new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Menu))))
                        if(!menus.Exists(x=>Automation.Compare(x,e)))menus.Add(e);
                    foreach(AutomationElement menu in menus) {
                        // Verified 13.26 shape: Menu(Search) > ToolBar(Search) >
                        // MenuItem. Inspect only those two child levels. A full
                        // Descendants query enters lazy nested menus and stalls
                        // on the first use; it is not a readiness delay to retry.
                        var containers=new List<AutomationElement>();containers.Add(menu);
                        foreach(AutomationElement child in menu.FindAll(TreeScope.Children,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.ToolBar)))
                            if(child.Current.ProcessId==pid&&Label(child)=="Search")containers.Add(child);
                        foreach(AutomationElement container in containers)
                            foreach(AutomationElement e in container.FindAll(TreeScope.Children,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.MenuItem)))
                                if(e.Current.ProcessId==pid&&Label(e)=="Go to Selected Packet"&&e.Current.IsEnabled&&!matches.Exists(x=>Automation.Compare(x,e)))matches.Add(e);
                    }
                    if(openError!=null)throw openError;
                    if(matches.Count==0)Thread.Sleep(50);
                }
                if(matches.Count!=1)throw new InvalidOperationException("SELECTED_PACKET_MENU_NOT_UNIQUE: "+matches.Count);
                Console.Error.WriteLine("invoke_command");
                if(!matches[0].TryGetCurrentPattern(InvokePattern.Pattern,out action))throw new InvalidOperationException("INVOKE_UNAVAILABLE");
                ((InvokePattern)action).Invoke();
                Console.Error.WriteLine("command_returned");
                result["status"]="invoked";result["pid"]=pid;result["window_handle"]=process.MainWindowHandle.ToInt64();
                result["command"]="Search / Go to Selected Packet";result["method"]="UIAutomation";
                result["gui_verified"]=false;
            }
        } catch(Exception ex) { result["status"]="unavailable";result["error"]=ex.Message; }
        Console.WriteLine(new JavaScriptSerializer().Serialize(result));
        return (string)result["status"]=="invoked"?0:2;
    }
}
