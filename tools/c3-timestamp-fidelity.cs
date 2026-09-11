using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;

public sealed class C3TimestampEvent
{
    public long Index { get; set; }
    public long TimestampSeconds { get; set; }
    public long TimestampNanoseconds { get; set; }
    public long TimestampNs { get; set; }
    public string TimestampText { get; set; }
    public string Type { get; set; }

    public C3TimestampEvent()
    {
        TimestampText = "";
        Type = "";
    }
}

[ComVisible(true)]
[Guid("E728AC14-E3E0-4559-BA3E-A643A694777A")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IC3TimestampEngineEvents
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
public sealed class C3TimestampEventSink : IC3TimestampEngineEvents
{
    public int NotifyCount { get; private set; }
    public int SummaryCount { get; private set; }
    public long DeclaredEventCount { get; private set; }
    public int FinishedResult { get; private set; }
    public string Error { get; private set; }
    public List<string> Reports { get; private set; }
    public List<C3TimestampEvent> Events { get; private set; }

    public C3TimestampEventSink()
    {
        FinishedResult = -1;
        Error = "";
        Reports = new List<string>();
        Events = new List<C3TimestampEvent>();
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
        if (eventId == 2601)
        {
            if (values.Length != 4)
            {
                Error = "timestamp batch payload did not contain 4 items";
                return;
            }

            string marker = Convert.ToString(values.GetValue(lower)) ?? "";
            if (marker != "C3-TIMESTAMP-FIDELITY")
            {
                Error = "unexpected C3 timestamp marker: " + marker;
                return;
            }

            int expectedBatchCount = Convert.ToInt32(values.GetValue(lower + 2));
            string batchText = Convert.ToString(values.GetValue(lower + 3)) ?? "";
            string[] records = batchText.Split(
                new[] { '\n' },
                StringSplitOptions.RemoveEmptyEntries);

            if (records.Length != expectedBatchCount)
            {
                Error = "timestamp batch record count did not match payload count";
                return;
            }

            foreach (string record in records)
            {
                string[] fields = record.Split('|');
                if (fields.Length != 5)
                {
                    Error = "timestamp record did not contain 5 fields";
                    return;
                }

                long seconds = Convert.ToInt64(fields[1].Trim());
                long nanoseconds = Convert.ToInt64(fields[2].Trim());
                if (seconds < 0 || nanoseconds < 0 || nanoseconds >= 1000000000L)
                {
                    Error = "timestamp components were outside the expected range";
                    return;
                }

                long timestampNs;
                try
                {
                    timestampNs = checked(seconds * 1000000000L + nanoseconds);
                }
                catch (OverflowException)
                {
                    Error = "timestamp nanoseconds overflowed Int64";
                    return;
                }

                Events.Add(new C3TimestampEvent
                {
                    Index = Convert.ToInt64(fields[0].Trim()),
                    TimestampSeconds = seconds,
                    TimestampNanoseconds = nanoseconds,
                    TimestampNs = timestampNs,
                    TimestampText = fields[3].Trim(),
                    Type = fields[4].Trim()
                });
            }
            return;
        }

        if (eventId == 2602)
        {
            if (values.Length != 2)
            {
                Error = "timestamp summary payload did not contain 2 items";
                return;
            }

            string marker = Convert.ToString(values.GetValue(lower)) ?? "";
            if (marker != "C3-TIMESTAMP-FIDELITY-SUMMARY")
            {
                Error = "unexpected C3 timestamp summary marker: " + marker;
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
public interface IC3TimestampConnectionPointContainer
{
    void EnumConnectionPoints([MarshalAs(UnmanagedType.Interface)] out object connectionPoints);

    void FindConnectionPoint(
        ref Guid eventInterface,
        [MarshalAs(UnmanagedType.Interface)] out IC3TimestampConnectionPoint connectionPoint);
}

[ComImport]
[Guid("B196B286-BAB4-101A-B69C-00AA00341D07")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IC3TimestampConnectionPoint
{
    void GetConnectionInterface(out Guid eventInterface);

    void GetConnectionPointContainer(
        [MarshalAs(UnmanagedType.Interface)] out IC3TimestampConnectionPointContainer container);

    void Advise([MarshalAs(UnmanagedType.Interface)] object sink, out int cookie);

    void Unadvise(int cookie);

    void EnumConnections([MarshalAs(UnmanagedType.Interface)] out object connections);
}

public sealed class C3TimestampResult
{
    public int RunResult { get; set; }
    public long ElapsedMilliseconds { get; set; }
    public int NotifyCount { get; set; }
    public int SummaryCount { get; set; }
    public long DeclaredEventCount { get; set; }
    public int FinishedResult { get; set; }
    public List<C3TimestampEvent> Events { get; set; }
    public List<string> Reports { get; set; }
    public string Error { get; set; }

    public C3TimestampResult()
    {
        Events = new List<C3TimestampEvent>();
        Reports = new List<string>();
        Error = "";
    }
}

public static class C3TimestampRunner
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

    public static C3TimestampResult Run(string tracePath, string scriptPath)
    {
        var result = new C3TimestampResult();
        object analyzer = null;
        object trace = null;
        object engine = null;
        IC3TimestampConnectionPoint connectionPoint = null;
        int cookie = 0;
        bool advised = false;
        var sink = new C3TimestampEventSink();

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

            var container = (IC3TimestampConnectionPointContainer)engine;
            Guid eventInterface = typeof(IC3TimestampEngineEvents).GUID;
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
