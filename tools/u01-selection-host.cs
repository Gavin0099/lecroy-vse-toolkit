using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;

// The event IID and dispatch methods match the existing USB M2 host interface.
[ComVisible(true), Guid("E728AC14-E3E0-4559-BA3E-A643A694777A")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IU01Events {
    [DispId(1)] void OnVScriptReportUpdated([MarshalAs(UnmanagedType.BStr)] string text, int tag);
    [DispId(2)] void OnVScriptFinished([MarshalAs(UnmanagedType.BStr)] string script, int result, int tag);
    [DispId(3)] void OnNotifyClient(int id, [MarshalAs(UnmanagedType.Struct)] object body, int tag);
}

// Match the Interface marshaling used by the qualified M2 USB bridge.
[ComImport, Guid("B196B284-BAB4-101A-B69C-00AA00341D07"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IU01ConnectionPointContainer {
    void EnumConnectionPoints([MarshalAs(UnmanagedType.Interface)] out object points);
    void FindConnectionPoint(ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out IU01ConnectionPoint point);
}
[ComImport, Guid("B196B286-BAB4-101A-B69C-00AA00341D07"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IU01ConnectionPoint {
    void GetConnectionInterface(out Guid iid);
    void GetConnectionPointContainer([MarshalAs(UnmanagedType.Interface)] out IU01ConnectionPointContainer container);
    void Advise([MarshalAs(UnmanagedType.Interface)] object sink, out int cookie);
    void Unadvise(int cookie);
    void EnumConnections([MarshalAs(UnmanagedType.Interface)] out object connections);
}

[ComVisible(true), ClassInterface(ClassInterfaceType.None)]
public sealed class U01Sink : IU01Events {
    public List<long[]> Rows = new List<long[]>();
    public long[] Summary;
    public int FinishedResult = -1;
    public int FinishedCount = 0;
    public string Error = "";
    public string LifecycleLog;
    public List<string> Reports = new List<string>();
    private void Log(string value) { if (LifecycleLog != null) File.AppendAllText(LifecycleLog, DateTime.UtcNow.ToString("o") + " " + value + Environment.NewLine); }
    public void OnVScriptReportUpdated(string text, int tag) { if (!String.IsNullOrWhiteSpace(text)) { Reports.Add(text); if (Reports.Count <= 8) Log("report " + text); } }
    public void OnVScriptFinished(string script, int result, int tag) { FinishedCount++; FinishedResult = result; Log("finished " + result); }
    public void OnNotifyClient(int id, object body, int tag) {
        try {
            if (Rows.Count == 0 || id == 2502) Log("notify " + id);
            Array a = body as Array;
            if (a == null || a.Rank != 1) throw new InvalidOperationException("invalid event array");
            int lower = a.GetLowerBound(0);
            string marker = Convert.ToString(a.GetValue(lower));
            if (id == 2501 && marker == "U01-ROW" && a.Length == 9) {
                if (Summary != null) throw new InvalidOperationException("row after end marker");
                if (Rows.Count >= 512) throw new InvalidOperationException("sample exceeds declared limit");
                var row = new long[8];
                for (int n = 0; n < 8; n++) {
                    object field = a.GetValue(lower + 1 + n);
                    row[n] = (n == 7 && field is string && (string)field == "NOT_APPLICABLE") ? -1 : Integer(field);
                }
                Rows.Add(row);
            } else if (id == 2502 && marker == "U01-END" && a.Length == 6) {
                if (Summary != null) throw new InvalidOperationException("duplicate end marker");
                Summary = new long[5];
                for (int n = 0; n < 5; n++) Summary[n] = Integer(a.GetValue(lower + 1 + n));
            } else throw new InvalidOperationException("unexpected notification or marker");
        } catch (Exception ex) { if (Error == "") Error = ex.GetBaseException().Message; }
    }
    private static long Integer(object value) {
        if (!(value is int) && !(value is long) && !(value is short) && !(value is byte)
            && !(value is uint) && !(value is ulong) && !(value is ushort))
            throw new InvalidOperationException("non-integer callback field");
        return Convert.ToInt64(value);
    }
}

public sealed class U01HostResult {
    public int RunResult = -1;
    public U01Sink Sink = new U01Sink();
    public string Error = "";
}

public static class U01Host {
    // Repeated fresh COM servers can race a previous server's shutdown. Retry
    // only class-factory activation RPC failures, before any trace is opened.
    public static object Activate(Func<object> factory, Action<string> stage) {
        for (int attempt = 0; ; attempt++) {
            try { return factory(); }
            catch (Exception ex) {
                int hr = ex.GetBaseException().HResult;
                if (attempt >= 2 || (hr != unchecked((int)0x800706BF) && hr != unchecked((int)0x800706BA))) throw;
                if (stage != null) stage("activate_retry " + (attempt + 1));
                Thread.Sleep(1000 * (attempt + 1));
            }
        }
    }
    private static object Call(object target, string name, params object[] args) {
        return target.GetType().InvokeMember(name, BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, target, args);
    }
    public static U01HostResult Run(string tracePath, string scriptPath) {
        return Run(tracePath, scriptPath, null);
    }
    public static U01HostResult Run(string tracePath, string scriptPath, string lifecycleLog) {
        var result = new U01HostResult();
        object analyzer = null, trace = null, engine = null;
        IU01ConnectionPoint cp = null;
        int cookie = 0;
        bool advised = false;
        Action<string> stage = delegate(string name) { if (lifecycleLog != null) File.AppendAllText(lifecycleLog, DateTime.UtcNow.ToString("o") + " " + name + Environment.NewLine); };
        result.Sink.LifecycleLog = lifecycleLog;
        try {
            stage("activate");
            Type t = Type.GetTypeFromProgID("CATC.UsbTracer");
            if (t == null) throw new InvalidOperationException("USB COM registration missing");
            analyzer = Activate(delegate { return Activator.CreateInstance(t); }, stage);
            stage("open");
            trace = Call(analyzer, "OpenFile", tracePath);
            stage("engine");
            engine = Call(trace, "GetVScriptEngine", scriptPath);
            stage("advise");
            Guid iid = typeof(IU01Events).GUID;
            ((IU01ConnectionPointContainer)engine).FindConnectionPoint(ref iid, out cp);
            cp.Advise(result.Sink, out cookie);
            advised = true;
            engine.GetType().InvokeMember("Tag", BindingFlags.SetProperty | BindingFlags.Public | BindingFlags.Instance, null, engine, new object[] {4242});
            stage("run");
            result.RunResult = Convert.ToInt32(Call(engine, "RunVScript"));
            stage("run_returned");
        } catch (Exception ex) { result.Error = ex.GetBaseException().Message; }
        finally {
            stage("cleanup");
            if (advised) { try { cp.Unadvise(cookie); } catch (Exception ex) { result.Error += " unadvise: " + ex.GetBaseException().Message; } }
            if (trace != null) { try { Call(trace, "Close"); } catch (Exception ex) { result.Error += " close: " + ex.GetBaseException().Message; } }
            foreach (object value in new object[] {cp, engine, trace, analyzer}) {
                try { if (value != null && Marshal.IsComObject(value)) Marshal.FinalReleaseComObject(value); }
                catch (Exception ex) { result.Error += " release: " + ex.GetBaseException().Message; }
            }
        }
        if (result.Sink.Error != "") result.Error += " sink: " + result.Sink.Error;
        if (result.Sink.FinishedCount != 1) result.Error += " expected one finished callback";
        stage("complete");
        return result;
    }
}
