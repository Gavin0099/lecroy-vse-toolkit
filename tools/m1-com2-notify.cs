using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

[ComVisible(true)]
[Guid("E728AC14-E3E0-4559-BA3E-A643A694777A")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IM1Com2VseEngineEvents
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
public sealed class M1Com2EventSink : IM1Com2VseEngineEvents
{
    public int NotifyCount { get; private set; }
    public int EventId { get; private set; }
    public int Tag { get; private set; }
    public string Marker { get; private set; } = "UNKNOWN";
    public long EventCount { get; private set; }
    public long Usb3RxCount { get; private set; }
    public long Usb3TxCount { get; private set; }
    public long UsbCcCount { get; private set; }
    public string PayloadError { get; private set; } = "";

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

        if (!(eventBody is Array values))
        {
            PayloadError = "eventBody was not an array";
            return;
        }

        int lower = values.GetLowerBound(0);
        if (values.Length != 5)
        {
            PayloadError = $"expected 5 payload items, got {values.Length}";
            return;
        }

        Marker = Convert.ToString(values.GetValue(lower)) ?? "NULL";
        EventCount = Convert.ToInt64(values.GetValue(lower + 1));
        Usb3RxCount = Convert.ToInt64(values.GetValue(lower + 2));
        Usb3TxCount = Convert.ToInt64(values.GetValue(lower + 3));
        UsbCcCount = Convert.ToInt64(values.GetValue(lower + 4));
    }
}

[ComImport]
[Guid("B196B284-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM1Com2ConnectionPointContainer
{
    void EnumConnectionPoints([MarshalAs(UnmanagedType.Interface)] out object connectionPoints);

    void FindConnectionPoint(
        ref Guid eventInterface,
        [MarshalAs(UnmanagedType.Interface)] out IM1Com2ConnectionPoint connectionPoint);
}

[ComImport]
[Guid("B196B286-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM1Com2ConnectionPoint
{
    void GetConnectionInterface(out Guid eventInterface);

    void GetConnectionPointContainer(
        [MarshalAs(UnmanagedType.Interface)] out IM1Com2ConnectionPointContainer container);

    void Advise(
        [MarshalAs(UnmanagedType.Interface)] object sink,
        out int cookie);

    void Unadvise(int cookie);

    void EnumConnections([MarshalAs(UnmanagedType.Interface)] out object connections);
}

public sealed class M1Com2Result
{
    public int RunResult { get; set; }
    public long ElapsedMilliseconds { get; set; }
    public int NotifyCount { get; set; }
    public int EventId { get; set; }
    public int Tag { get; set; }
    public string Marker { get; set; } = "UNKNOWN";
    public long EventCount { get; set; }
    public long Usb3RxCount { get; set; }
    public long Usb3TxCount { get; set; }
    public long UsbCcCount { get; set; }
    public string PayloadError { get; set; } = "";
    public string Error { get; set; } = "";
}

public static class M1Com2Runner
{
    public static M1Com2Result Run(string tracePath, string scriptPath)
    {
        var result = new M1Com2Result();
        object analyzer = null;
        object trace = null;
        object engine = null;
        IM1Com2ConnectionPoint connectionPoint = null;
        int cookie = 0;
        bool advised = false;
        var sink = new M1Com2EventSink();

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
            var container = (IM1Com2ConnectionPointContainer)engine;
            Guid eventInterface = typeof(IM1Com2VseEngineEvents).GUID;
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
        result.Marker = sink.Marker;
        result.EventCount = sink.EventCount;
        result.Usb3RxCount = sink.Usb3RxCount;
        result.Usb3TxCount = sink.Usb3TxCount;
        result.UsbCcCount = sink.UsbCcCount;
        result.PayloadError = sink.PayloadError;
        return result;
    }
}
