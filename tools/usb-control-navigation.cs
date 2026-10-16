// Single owned, read-only LeCroy session. A WinForms timer dispatches the IPC
// queue on the COM-owning STA; the HTTP/UI process never waits on this STA.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public static class TraceNavigationWorker {
    static object analyzer, trace;
    static string root, caption;
    static int nativePid, opens;
    static long nativeStart;
    static readonly JavaScriptSerializer json = new JavaScriptSerializer();
    static readonly System.Text.UTF8Encoding utf8 = new System.Text.UTF8Encoding(false);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int n);
    static object Call(object target,string method,params object[] args) {
        return target.GetType().InvokeMember(method,BindingFlags.InvokeMethod|BindingFlags.Public|BindingFlags.Instance,null,target,args);
    }
    static void Save(string name,object value) {
        string p=Path.Combine(root,name), tmp=p+".tmp";
        File.WriteAllText(tmp,json.Serialize(value),utf8);
        if(File.Exists(p)) File.Delete(p);
        File.Move(tmp,p);
    }
    static Process[] Servers() { return Process.GetProcessesByName("UsbSuite"); }
    static bool Owned(bool requireCaption) {
        var ps=Servers();
        if(nativePid==0 || ps.Length!=1 || ps[0].Id!=nativePid || ps[0].StartTime.ToUniversalTime().Ticks!=nativeStart) return false;
        ps[0].Refresh();
        return !requireCaption || (ps[0].MainWindowHandle!=IntPtr.Zero && ps[0].MainWindowTitle==caption);
    }
    static void Release(object value) { if(value!=null && Marshal.IsComObject(value)) Marshal.FinalReleaseComObject(value); }
    static void Close() {
        // Do not Close a document if the user changed the selected document/window.
        bool safe=trace!=null && Owned(true);
        try { if(safe) Call(trace,"Close"); }
        finally { Release(trace);trace=null;Release(analyzer);analyzer=null; }
        GC.Collect();GC.WaitForPendingFinalizers();
    }
    public static void Run(string directory) {
        if(Thread.CurrentThread.GetApartmentState()!=ApartmentState.STA) throw new InvalidOperationException("STA required");
        using(var ownership=new Mutex(false,@"Local\LeCroyTraceTriage.Native")) {
        bool acquired=false;
        try {acquired=ownership.WaitOne(0);} catch(AbandonedMutexException) {acquired=true;}
        if(!acquired)throw new InvalidOperationException("Another tool session owns native operations");
        try {
        root=directory;
        var binding=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"binding.json"),utf8));
        string path=Path.GetFullPath((string)binding["working_path"]);
        // Candidate whitelist comes from a private controller-created binding file.
        var allowed=new HashSet<int>(((System.Collections.IEnumerable)binding["transfers"]).Cast<object>().Select(Convert.ToInt32));
        var context=new ApplicationContext();
        var timer=new System.Windows.Forms.Timer();timer.Interval=100;
        Save("ready.json",new {state="ready",apartment="STA",message_pump="WinForms",coexistence="restricted"});
        timer.Tick += delegate {
            string req=Path.Combine(root,"request.json");
            if(!File.Exists(req)) return;
            timer.Stop(); // Prevent reentrant requests while COM pumps messages.
            string id="";
            var watch=Stopwatch.StartNew();
            try {
                var command=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(req,utf8));
                File.Delete(req);id=(string)command["id"];
                if((string)command["action"]=="close") {
                    Close();Save("response.json",new {id=id,state="closed",elapsed_ms=watch.ElapsedMilliseconds});context.ExitThread();return;
                }
                int unit=Convert.ToInt32(command["transfer"]);
                if(!allowed.Contains(unit)) throw new InvalidOperationException("Candidate not allowed");
                if(trace==null) {
                    if(Servers().Length!=0) throw new InvalidOperationException("LeCroy conflict: existing session is not owned; no COM activation attempted");
                    analyzer=Activator.CreateInstance(Type.GetTypeFromProgID("CATC.UsbTracer",true));
                    // No pre-existing server, one resulting process, no native file
                    // operation until process exclusivity has been established.
                    var servers=Servers();
                    if(servers.Length!=1) throw new InvalidOperationException("Cannot establish exclusive server ownership");
                    nativePid=servers[0].Id;nativeStart=servers[0].StartTime.ToUniversalTime().Ticks;
                    Save("ownership.json",new {pid=nativePid,start_ticks=nativeStart,baseline_servers=0,coexistence="restricted"});
                    if(!Owned(false)) throw new InvalidOperationException("Server ownership changed before OpenFile");
                    trace=Call(analyzer,"OpenFile",path);opens++;
                    var p=Process.GetProcessById(nativePid);p.Refresh();caption=p.MainWindowTitle;
                    if(String.IsNullOrEmpty(caption) || caption.IndexOf(Path.GetFileName(path),StringComparison.OrdinalIgnoreCase)<0)
                        throw new InvalidOperationException("Native window does not identify the bound copy; ownership remains unqualified");
                }
                if(!Owned(true)) throw new InvalidOperationException("Native session changed; refusing to navigate or take over");
                Call(trace,"GotoUnit",3,unit);
                var native=Process.GetProcessById(nativePid);native.Refresh();
                bool foreground=false;
                if(native.MainWindowHandle!=IntPtr.Zero) {ShowWindow(native.MainWindowHandle,9);foreground=SetForegroundWindow(native.MainWindowHandle);}
                Save("response.json",new {id=id,state="api_returned",transfer=unit,open_count=opens,pid=nativePid,
                    elapsed_ms=watch.ElapsedMilliseconds,foreground_request_accepted=foreground,gui_confirmed=false});
            } catch(Exception ex) {
                Save("response.json",new {id=id,state="error",error=ex.GetBaseException().Message,elapsed_ms=watch.ElapsedMilliseconds});
            } finally { if(!context.Equals(null)) timer.Start(); }
        };
        timer.Start();
        try {Application.Run(context);} finally {timer.Stop();timer.Dispose();Close();}
        } finally {ownership.ReleaseMutex();}
        }
    }
}
