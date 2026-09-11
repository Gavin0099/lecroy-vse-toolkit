using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;

public sealed class M2TimelineRaw
{
    public long LfpsType { get; set; }
    public long DurationNs { get; set; }
    public long DurationSec { get; set; }
    public long DurationRemainderNs { get; set; }
    public long PatternType { get; set; }
    public long StartsPattern { get; set; }
}

public sealed class M2TimelineEvent
{
    public string EventClass { get; set; }
    public long Index { get; set; }
    public long TimestampSeconds { get; set; }
    public long TimestampNanoseconds { get; set; }
    public long TimestampNs { get; set; }
    public string Timestamp { get; set; }
    public string Type { get; set; }
    public M2TimelineRaw Raw { get; set; }

    public M2TimelineEvent()
    {
        EventClass = "";
        Timestamp = "";
        Type = "";
    }
}

[ComVisible(true)]
[Guid("E728AC14-E3E0-4559-BA3E-A643A694777A")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IM2TimelineEngineEvents
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
public sealed class M2TimelineEventSink : IM2TimelineEngineEvents
{
    public int NotifyCount { get; private set; }
    public int SummaryCount { get; private set; }
    public long DeclaredLinkCommandCount { get; private set; }
    public long DeclaredLtssmCount { get; private set; }
    public long DeclaredLfpsCount { get; private set; }
    public long DeclaredTotalCount { get; private set; }
    public int FinishedResult { get; private set; }
    public string Error { get; private set; }
    public List<string> Reports { get; private set; }
    public List<M2TimelineEvent> Events { get; private set; }

    public M2TimelineEventSink()
    {
        FinishedResult = -1;
        Error = "";
        Reports = new List<string>();
        Events = new List<M2TimelineEvent>();
    }

    public void OnVScriptReportUpdated(string newLine, int tag)
    {
        if (!string.IsNullOrWhiteSpace(newLine))
        {
            Reports.Add(newLine);
        }
    }

    public void OnVScriptFinished(string scriptName, int result, int tag)
    {
        FinishedResult = result;
    }

    public void OnNotifyClient(int eventId, object eventBody, int tag)
    {
        NotifyCount++;

        Array values = eventBody as Array;
        if (values == null)
        {
            Error = "eventBody was not an array";
            return;
        }

        int lower = values.GetLowerBound(0);
        if (eventId == 2401)
        {
            if (values.Length != 4)
            {
                Error = "timeline event payload did not contain 4 items";
                return;
            }

            string marker = Convert.ToString(values.GetValue(lower)) ?? "";
            if (marker != "M2-PACKET-EXTRACTION-4")
            {
                Error = "unexpected timeline event marker: " + marker;
                return;
            }

            int expectedBatchCount = Convert.ToInt32(values.GetValue(lower + 2));
            string batchText = Convert.ToString(values.GetValue(lower + 3)) ?? "";
            string[] records = batchText.Split(
                new[] { '\n' },
                StringSplitOptions.RemoveEmptyEntries);

            if (records.Length != expectedBatchCount)
            {
                Error = "timeline batch record count did not match payload count";
                return;
            }

            foreach (string record in records)
            {
                string[] fields = record.Split('|');
                if (fields.Length != 12)
                {
                    Error = "timeline record did not contain 12 fields";
                    return;
                }

                string eventClass = fields[0].Trim();
                var timelineEvent = new M2TimelineEvent
                {
                    EventClass = eventClass,
                    Index = Convert.ToInt64(fields[1].Trim()),
                    TimestampSeconds = Convert.ToInt64(fields[2].Trim()),
                    TimestampNanoseconds = Convert.ToInt64(fields[3].Trim()),
                    Timestamp = fields[4].Trim(),
                    Type = fields[5].Trim(),
                    Raw = null
                };

                if (timelineEvent.TimestampSeconds < 0 ||
                    timelineEvent.TimestampNanoseconds < 0 ||
                    timelineEvent.TimestampNanoseconds >= 1000000000L)
                {
                    Error = "timeline timestamp components were outside the expected range";
                    return;
                }

                try
                {
                    timelineEvent.TimestampNs = checked(
                        timelineEvent.TimestampSeconds * 1000000000L +
                        timelineEvent.TimestampNanoseconds);
                }
                catch (OverflowException)
                {
                    Error = "timeline timestamp nanoseconds overflowed Int64";
                    return;
                }

                if (eventClass == "LFPS")
                {
                    timelineEvent.Raw = new M2TimelineRaw
                    {
                        LfpsType = Convert.ToInt64(fields[6].Trim()),
                        DurationNs = Convert.ToInt64(fields[7].Trim()),
                        DurationSec = Convert.ToInt64(fields[8].Trim()),
                        DurationRemainderNs = Convert.ToInt64(fields[9].Trim()),
                        PatternType = Convert.ToInt64(fields[10].Trim()),
                        StartsPattern = Convert.ToInt64(fields[11].Trim())
                    };
                }
                else if (eventClass != "LINK_CMD" && eventClass != "LTSSM_STATE")
                {
                    Error = "unexpected timeline event class: " + eventClass;
                    return;
                }

                Events.Add(timelineEvent);
            }
            return;
        }

        if (eventId == 2402)
        {
            if (values.Length != 5)
            {
                Error = "timeline summary payload did not contain 5 items";
                return;
            }

            string marker = Convert.ToString(values.GetValue(lower)) ?? "";
            if (marker != "M2-PACKET-EXTRACTION-4-SUMMARY")
            {
                Error = "unexpected timeline summary marker: " + marker;
                return;
            }

            SummaryCount++;
            DeclaredLinkCommandCount = Convert.ToInt64(values.GetValue(lower + 1));
            DeclaredLtssmCount = Convert.ToInt64(values.GetValue(lower + 2));
            DeclaredLfpsCount = Convert.ToInt64(values.GetValue(lower + 3));
            DeclaredTotalCount = Convert.ToInt64(values.GetValue(lower + 4));
        }
    }
}

[ComImport]
[Guid("B196B284-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM2TimelineConnectionPointContainer
{
    void EnumConnectionPoints([MarshalAs(UnmanagedType.Interface)] out object connectionPoints);

    void FindConnectionPoint(
        ref Guid eventInterface,
        [MarshalAs(UnmanagedType.Interface)] out IM2TimelineConnectionPoint connectionPoint);
}

[ComImport]
[Guid("B196B286-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM2TimelineConnectionPoint
{
    void GetConnectionInterface(out Guid eventInterface);

    void GetConnectionPointContainer(
        [MarshalAs(UnmanagedType.Interface)] out IM2TimelineConnectionPointContainer container);

    void Advise([MarshalAs(UnmanagedType.Interface)] object sink, out int cookie);

    void Unadvise(int cookie);

    void EnumConnections([MarshalAs(UnmanagedType.Interface)] out object connections);
}

public sealed class M2TimelineResult
{
    public int RunResult { get; set; }
    public long ElapsedMilliseconds { get; set; }
    public int NotifyCount { get; set; }
    public int SummaryCount { get; set; }
    public long DeclaredLinkCommandCount { get; set; }
    public long DeclaredLtssmCount { get; set; }
    public long DeclaredLfpsCount { get; set; }
    public long DeclaredTotalCount { get; set; }
    public int FinishedResult { get; set; }
    public List<M2TimelineEvent> Events { get; set; }
    public List<string> Reports { get; set; }
    public string Error { get; set; }

    public M2TimelineResult()
    {
        Events = new List<M2TimelineEvent>();
        Reports = new List<string>();
        Error = "";
    }
}

public static class M2TimelineRunner
{
    private static object InvokeComMethod(object target, string methodName, params object[] arguments)
    {
        return target.GetType().InvokeMember(
            methodName,
            BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
            null,
            target,
            arguments);
    }

    private static void SetComProperty(object target, string propertyName, object value)
    {
        target.GetType().InvokeMember(
            propertyName,
            BindingFlags.SetProperty | BindingFlags.Public | BindingFlags.Instance,
            null,
            target,
            new[] { value });
    }

    public static M2TimelineResult Run(string tracePath, string scriptPath)
    {
        var result = new M2TimelineResult();
        object analyzer = null;
        object trace = null;
        object engine = null;
        IM2TimelineConnectionPoint connectionPoint = null;
        int cookie = 0;
        bool advised = false;
        var sink = new M2TimelineEventSink();

        try
        {
            Type analyzerType = Type.GetTypeFromProgID("CATC.UsbTracer");
            if (analyzerType == null)
            {
                throw new InvalidOperationException("CATC.UsbTracer ProgID was not found.");
            }

            analyzer = Activator.CreateInstance(analyzerType);
            trace = InvokeComMethod(analyzer, "OpenFile", tracePath);
            if (trace == null)
            {
                throw new InvalidOperationException("OpenFile returned null.");
            }

            engine = InvokeComMethod(trace, "GetVScriptEngine", scriptPath);
            if (engine == null)
            {
                throw new InvalidOperationException("GetVScriptEngine returned null.");
            }

            var container = (IM2TimelineConnectionPointContainer)engine;
            Guid eventInterface = typeof(IM2TimelineEngineEvents).GUID;
            container.FindConnectionPoint(ref eventInterface, out connectionPoint);
            connectionPoint.Advise(sink, out cookie);
            advised = true;
            SetComProperty(engine, "Tag", 4242);

            var watch = Stopwatch.StartNew();
            result.RunResult = Convert.ToInt32(InvokeComMethod(engine, "RunVScript"));
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
                if (trace != null) InvokeComMethod(trace, "Close");
            }
            catch { }

            try
            {
                if (engine != null && Marshal.IsComObject(engine))
                    Marshal.FinalReleaseComObject(engine);
            }
            catch { }

            try
            {
                if (trace != null && Marshal.IsComObject(trace))
                    Marshal.FinalReleaseComObject(trace);
            }
            catch { }

            try
            {
                if (analyzer != null && Marshal.IsComObject(analyzer))
                    Marshal.FinalReleaseComObject(analyzer);
            }
            catch { }
        }

        result.NotifyCount = sink.NotifyCount;
        result.SummaryCount = sink.SummaryCount;
        result.DeclaredLinkCommandCount = sink.DeclaredLinkCommandCount;
        result.DeclaredLtssmCount = sink.DeclaredLtssmCount;
        result.DeclaredLfpsCount = sink.DeclaredLfpsCount;
        result.DeclaredTotalCount = sink.DeclaredTotalCount;
        result.FinishedResult = sink.FinishedResult;
        result.Events = sink.Events;
        result.Reports = sink.Reports;
        if (result.Error == "" && sink.Error != "")
        {
            result.Error = sink.Error;
        }

        return result;
    }
}
