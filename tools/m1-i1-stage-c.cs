using System;
using System.IO;
using System.Runtime.InteropServices;

public sealed class M1I1StageCResult
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
    public bool HostWriteCompleted { get; set; }
    public string Error { get; set; } = "";
}

public static class M1I1StageCRunner
{
    public static M1I1StageCResult Run(string tracePath, string scriptPath, string outputPath)
    {
        var result = new M1I1StageCResult();
        object analyzer = null;
        object trace = null;
        object engine = null;
        IM1Com2ConnectionPoint connectionPoint = null;
        int cookie = 0;
        bool advised = false;
        var sink = new M1Com2EventSink();
        var watch = System.Diagnostics.Stopwatch.StartNew();

        try
        {
            Type analyzerType = Type.GetTypeFromProgID("CATC.UsbTracer");
            if (analyzerType == null)
            {
                throw new InvalidOperationException("CATC.UsbTracer ProgID was not found.");
            }

            analyzer = Activator.CreateInstance(analyzerType);
            trace = ((dynamic)analyzer).OpenFile(tracePath);
            if (trace == null)
            {
                throw new InvalidOperationException("OpenFile returned null.");
            }

            engine = ((dynamic)trace).GetVScriptEngine(scriptPath);
            if (engine == null)
            {
                throw new InvalidOperationException("GetVScriptEngine returned null.");
            }

            var container = (IM1Com2ConnectionPointContainer)engine;
            Guid eventInterface = typeof(IM1Com2VseEngineEvents).GUID;
            container.FindConnectionPoint(ref eventInterface, out connectionPoint);
            connectionPoint.Advise(sink, out cookie);
            advised = true;
            ((dynamic)engine).Tag = 4242;

            result.RunResult = (int)((dynamic)engine).RunVScript();

            if (sink.NotifyCount != 1 || sink.EventId != 2001 || sink.Tag != 4242 ||
                sink.Marker != "M1-COM2" || sink.EventCount != 3186175 ||
                sink.Usb3RxCount != 632512 || sink.Usb3TxCount != 2553662 ||
                sink.UsbCcCount != 1 || sink.PayloadError != "")
            {
                throw new InvalidOperationException("COM2 payload acceptance failed before host write.");
            }

            if (File.Exists(outputPath))
            {
                throw new InvalidOperationException("Refusing to overwrite existing output: " + outputPath);
            }

            string json = "{\r\n" +
                "  \"event_count\": " + sink.EventCount + ",\r\n" +
                "  \"usb3_rx\": " + sink.Usb3RxCount + ",\r\n" +
                "  \"usb3_tx\": " + sink.Usb3TxCount + ",\r\n" +
                "  \"usb_cc\": " + sink.UsbCcCount + "\r\n" +
                "}\r\n";
            File.WriteAllText(outputPath, json, new System.Text.UTF8Encoding(false));
            result.HostWriteCompleted = File.Exists(outputPath);
        }
        catch (Exception error)
        {
            result.Error = error.GetBaseException().Message;
        }
        finally
        {
            watch.Stop();
            result.ElapsedMilliseconds = watch.ElapsedMilliseconds;

            if (advised && connectionPoint != null)
            {
                try { connectionPoint.Unadvise(cookie); } catch { }
            }

            try
            {
                if (trace != null) ((dynamic)trace).Close();
            }
            catch (Exception error)
            {
                if (result.Error == "") result.Error = error.GetBaseException().Message;
            }

            try
            {
                if (engine != null && Marshal.IsComObject(engine))
                    Marshal.FinalReleaseComObject(engine);
                if (trace != null && Marshal.IsComObject(trace))
                    Marshal.FinalReleaseComObject(trace);
                if (analyzer != null && Marshal.IsComObject(analyzer))
                    Marshal.FinalReleaseComObject(analyzer);
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
