using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

public sealed class M1I1OpenCloseResult
{
    public bool OpenSucceeded { get; set; }
    public bool CloseAttempted { get; set; }
    public bool CloseSucceeded { get; set; }
    public long ElapsedMilliseconds { get; set; }
    public string Error { get; set; } = "";
}

public static class M1I1OpenCloseRunner
{
    public static M1I1OpenCloseResult Run(string tracePath)
    {
        var result = new M1I1OpenCloseResult();
        object analyzer = null;
        object trace = null;
        var watch = Stopwatch.StartNew();

        try
        {
            Type analyzerType = Type.GetTypeFromProgID("CATC.UsbTracer");
            if (analyzerType == null)
            {
                throw new InvalidOperationException("CATC.UsbTracer ProgID was not found.");
            }

            analyzer = Activator.CreateInstance(analyzerType);
            trace = ((dynamic)analyzer).OpenFile(tracePath);
            result.OpenSucceeded = trace != null;
            if (trace == null)
            {
                throw new InvalidOperationException("OpenFile returned null.");
            }

            result.CloseAttempted = true;
            ((dynamic)trace).Close();
            result.CloseSucceeded = true;
        }
        catch (Exception error)
        {
            result.Error = error.GetBaseException().Message;
        }
        finally
        {
            watch.Stop();
            result.ElapsedMilliseconds = watch.ElapsedMilliseconds;

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

        return result;
    }
}
