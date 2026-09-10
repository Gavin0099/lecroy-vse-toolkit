using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;

public sealed class M2LfpsEvent
{
    public long Index { get; set; }
    public string Timestamp { get; set; } = "";
    public string Type { get; set; } = "";
    public long LfpsType { get; set; }
    public long DurationNs { get; set; }
    public long DurationSec { get; set; }
    public long DurationRemainderNs { get; set; }
    public long PatternType { get; set; }
    public long StartsPattern { get; set; }
}

[ComVisible(true)]
[Guid("E728AC14-E3E0-4559-BA3E-A643A694777A")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IM2LfpsEngineEvents
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
public sealed class M2LfpsEventSink : IM2LfpsEngineEvents
{
    public int NotifyCount { get; private set; }
    public int SummaryCount { get; private set; }
    public long DeclaredEventCount { get; private set; }
    public int FinishedResult { get; private set; } = -1;
    public string Error { get; private set; } = "";
    public List<string> Reports { get; } = new List<string>();
    public List<M2LfpsEvent> Events { get; } = new List<M2LfpsEvent>();

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

        if (!(eventBody is Array values))
        {
            Error = "eventBody was not an array";
            return;
        }

        int lower = values.GetLowerBound(0);
        if (eventId == 2301)
        {
            if (values.Length != 4)
            {
                Error = "LFPS event payload did not contain 4 items";
                return;
            }

            string marker = Convert.ToString(values.GetValue(lower)) ?? "";
            if (marker != "M2-PACKET-EXTRACTION-3")
            {
                Error = "unexpected M2 LFPS event marker: " + marker;
                return;
            }

            int expectedBatchCount = Convert.ToInt32(values.GetValue(lower + 2));
            string batchText = Convert.ToString(values.GetValue(lower + 3)) ?? "";
            string[] records = batchText.Split(
                new[] { '\n' },
                StringSplitOptions.RemoveEmptyEntries);

            if (records.Length != expectedBatchCount)
            {
                Error = "LFPS batch record count did not match payload count";
                return;
            }

            foreach (string record in records)
            {
                string[] fields = record.Split('|');
                if (fields.Length != 9)
                {
                    Error = "LFPS record did not contain all expected fields";
                    return;
                }

                Events.Add(new M2LfpsEvent
                {
                    Index = Convert.ToInt64(fields[0].Trim()),
                    Timestamp = fields[1].Trim(),
                    Type = fields[2].Trim(),
                    LfpsType = Convert.ToInt64(fields[3].Trim()),
                    DurationNs = Convert.ToInt64(fields[4].Trim()),
                    DurationSec = Convert.ToInt64(fields[5].Trim()),
                    DurationRemainderNs = Convert.ToInt64(fields[6].Trim()),
                    PatternType = Convert.ToInt64(fields[7].Trim()),
                    StartsPattern = Convert.ToInt64(fields[8].Trim())
                });
            }
            return;
        }

        if (eventId == 2302)
        {
            if (values.Length != 2)
            {
                Error = "LFPS summary payload did not contain 2 items";
                return;
            }

            string marker = Convert.ToString(values.GetValue(lower)) ?? "";
            if (marker != "M2-PACKET-EXTRACTION-3-SUMMARY")
            {
                Error = "unexpected M2 LFPS summary marker: " + marker;
                return;
            }

            SummaryCount++;
            DeclaredEventCount = Convert.ToInt64(values.GetValue(lower + 1));
        }
    }
}

[ComImport]
[Guid("B196B284-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM2LfpsConnectionPointContainer
{
    void EnumConnectionPoints([MarshalAs(UnmanagedType.Interface)] out object connectionPoints);

    void FindConnectionPoint(
        ref Guid eventInterface,
        [MarshalAs(UnmanagedType.Interface)] out IM2LfpsConnectionPoint connectionPoint);
}

[ComImport]
[Guid("B196B286-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IM2LfpsConnectionPoint
{
    void GetConnectionInterface(out Guid eventInterface);

    void GetConnectionPointContainer(
        [MarshalAs(UnmanagedType.Interface)] out IM2LfpsConnectionPointContainer container);

    void Advise([MarshalAs(UnmanagedType.Interface)] object sink, out int cookie);

    void Unadvise(int cookie);

    void EnumConnections([MarshalAs(UnmanagedType.Interface)] out object connections);
}

public sealed class M2LfpsResult
{
    public int RunResult { get; set; }
    public long ElapsedMilliseconds { get; set; }
    public int NotifyCount { get; set; }
    public int SummaryCount { get; set; }
    public long DeclaredEventCount { get; set; }
    public int FinishedResult { get; set; }
    public List<M2LfpsEvent> Events { get; set; } = new List<M2LfpsEvent>();
    public List<string> Reports { get; set; } = new List<string>();
    public string Error { get; set; } = "";
}

public static class M2LfpsRunner
{
    public static M2LfpsResult Run(string tracePath, string scriptPath)
    {
        var result = new M2LfpsResult();
        object analyzer = null;
        object trace = null;
        object engine = null;
        IM2LfpsConnectionPoint connectionPoint = null;
        int cookie = 0;
        bool advised = false;
        var sink = new M2LfpsEventSink();

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
            if (trace == null)
            {
                throw new InvalidOperationException("OpenFile returned null.");
            }

            dynamic traceDynamic = trace;
            engine = traceDynamic.GetVScriptEngine(scriptPath);
            if (engine == null)
            {
                throw new InvalidOperationException("GetVScriptEngine returned null.");
            }

            dynamic engineDynamic = engine;
            var container = (IM2LfpsConnectionPointContainer)engine;
            Guid eventInterface = typeof(IM2LfpsEngineEvents).GUID;
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
        result.DeclaredEventCount = sink.DeclaredEventCount;
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
