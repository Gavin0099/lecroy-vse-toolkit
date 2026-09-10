using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

[ComVisible(true)]
[Guid("E728AC14-E3E0-4559-BA3E-A643A694777A")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IM1Com1VseEngineEvents
{
    [DispId(1)]
    void OnVScriptReportUpdated(
        [MarshalAs(UnmanagedType.BStr)] string newLine,
        int tag);

    [DispId(2)]
    void OnVScriptFinished(
        [MarshalAs(UnmanagedType.BStr)] string scriptName,
        int result,
        int tag);

    [DispId(3)]
    void OnNotifyClient(
        int eventId,
        [MarshalAs(UnmanagedType.Struct)] object eventBody,
        int tag);
}

[ComVisible(true)]
[ClassInterface(ClassInterfaceType.None)]
public sealed class M1Com1EventSink : IM1Com1VseEngineEvents
{
    public int NotifyCount { get; private set; }
    public int EventId { get; private set; }
    public int Tag { get; private set; }
    public string Payload0 { get; private set; } = "UNKNOWN";
    public string Payload1 { get; private set; } = "UNKNOWN";

    public void OnVScriptReportUpdated(string newLine, int tag)
    {
    }

    public void OnVScriptFinished(string scriptName, int result, int tag)
    {
    }

    public void OnNotifyClient(int eventId, object eventBody, int tag)
    {
        NotifyCount++;
        EventId = eventId;
        Tag = tag;

        if (eventBody is Array values)
        {
            int lower = values.GetLowerBound(0);
            if (values.Length > 0)
            {
                Payload0 = Convert.ToString(values.GetValue(lower)) ?? "NULL";
            }
            if (values.Length > 1)
            {
                Payload1 = Convert.ToString(values.GetValue(lower + 1)) ?? "NULL";
            }
        }
        else
        {
            Payload0 = Convert.ToString(eventBody) ?? "NULL";
        }
    }
}

[ComImport]
[Guid("B196B284-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM1ConnectionPointContainer
{
    void EnumConnectionPoints([MarshalAs(UnmanagedType.Interface)] out object connectionPoints);

    void FindConnectionPoint(
        ref Guid eventInterface,
        [MarshalAs(UnmanagedType.Interface)] out IM1ConnectionPoint connectionPoint);
}

[ComImport]
[Guid("B196B286-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM1ConnectionPoint
{
    void GetConnectionInterface(out Guid eventInterface);

    void GetConnectionPointContainer(
        [MarshalAs(UnmanagedType.Interface)] out IM1ConnectionPointContainer container);

    void Advise(
        [MarshalAs(UnmanagedType.Interface)] object sink,
        out int cookie);

    void Unadvise(int cookie);

    void EnumConnections([MarshalAs(UnmanagedType.Interface)] out object connections);
}

public sealed class M1Com1Result
{
    public int RunResult { get; set; }
    public long ElapsedMilliseconds { get; set; }
    public int NotifyCount { get; set; }
    public int EventId { get; set; }
    public int Tag { get; set; }
    public string Payload0 { get; set; } = "UNKNOWN";
    public string Payload1 { get; set; } = "UNKNOWN";
    public string Error { get; set; } = "";
}

public static class M1Com1Runner
{
    public static M1Com1Result Run(string tracePath, string scriptPath)
    {
        var result = new M1Com1Result();
        object analyzer = null;
        object trace = null;
        object engine = null;
        IM1ConnectionPoint connectionPoint = null;
        int cookie = 0;
        bool advised = false;
        var sink = new M1Com1EventSink();

        try
        {
            Type analyzerType = Type.GetTypeFromProgID("CATC.UsbTracer");
            if (analyzerType == null)
            {
                throw new InvalidOperationException("CATC.UsbTracer ProgID was not found.");
            }

            analyzer = Activator.CreateInstance(analyzerType);
            dynamic analyzerDynamic = analyzer;
            trace = analyzerDynamic.OpenFile(tracePath);
            dynamic traceDynamic = trace;
            engine = traceDynamic.GetVScriptEngine(scriptPath);
            if (engine == null)
            {
                throw new InvalidOperationException("GetVScriptEngine returned null.");
            }

            dynamic engineDynamic = engine;
            var container = (IM1ConnectionPointContainer)engine;
            Guid eventInterface = typeof(IM1Com1VseEngineEvents).GUID;
            container.FindConnectionPoint(ref eventInterface, out connectionPoint);
            connectionPoint.Advise(sink, out cookie);
            advised = true;
            engineDynamic.Tag = 4242;

            var watch = Stopwatch.StartNew();
            result.RunResult = (int)engineDynamic.RunVScript();
            watch.Stop();
            result.ElapsedMilliseconds = watch.ElapsedMilliseconds;
        }
        catch (Exception error)
        {
            result.Error = error.GetBaseException().Message;
        }
        finally
        {
            if (advised && connectionPoint != null)
            {
                try { connectionPoint.Unadvise(cookie); } catch { }
            }

            try
            {
                if (trace != null) ((dynamic)trace).Close();
            }
            catch { }
        }

        result.NotifyCount = sink.NotifyCount;
        result.EventId = sink.EventId;
        result.Tag = sink.Tag;
        result.Payload0 = sink.Payload0;
        result.Payload1 = sink.Payload1;
        return result;
    }
}
