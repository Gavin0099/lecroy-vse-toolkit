using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

public sealed class TraceMutationRange
{
    public long StartOffset { get; set; }
    public long EndOffset { get; set; }
    public long Length { get; set; }
    public string BeforeHex { get; set; } = "";
    public string AfterHex { get; set; } = "";
    public bool HexTruncated { get; set; }
}

public sealed class TraceMutationReport
{
    public string BeforePath { get; set; } = "";
    public string AfterPath { get; set; } = "";
    public long BeforeSize { get; set; }
    public long AfterSize { get; set; }
    public long SizeDelta { get; set; }
    public long? FirstDifferingOffset { get; set; }
    public long? LastDifferingOffset { get; set; }
    public long ChangedByteCount { get; set; }
    public List<TraceMutationRange> Ranges { get; } = new List<TraceMutationRange>();
}

public static class TraceMutationLocalizer
{
    private const int BufferSize = 1024 * 1024;
    private const int MaxHexBytesPerRange = 64;

    public static TraceMutationReport Compare(string beforePath, string afterPath)
    {
        var beforeInfo = new FileInfo(beforePath);
        var afterInfo = new FileInfo(afterPath);
        var report = new TraceMutationReport
        {
            BeforePath = beforePath,
            AfterPath = afterPath,
            BeforeSize = beforeInfo.Length,
            AfterSize = afterInfo.Length,
            SizeDelta = afterInfo.Length - beforeInfo.Length
        };

        long commonLength = Math.Min(beforeInfo.Length, afterInfo.Length);
        using var before = new FileStream(beforePath, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var after = new FileStream(afterPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        byte[] beforeBuffer = new byte[BufferSize];
        byte[] afterBuffer = new byte[BufferSize];
        long offset = 0;
        TraceMutationRange current = null;

        while (offset < commonLength)
        {
            int requested = (int)Math.Min(BufferSize, commonLength - offset);
            ReadExactly(before, beforeBuffer, requested);
            ReadExactly(after, afterBuffer, requested);

            for (int i = 0; i < requested; i++)
            {
                long absolute = offset + i;
                if (beforeBuffer[i] == afterBuffer[i])
                {
                    CloseRange(report, ref current, absolute - 1);
                    continue;
                }

                if (current == null)
                {
                    current = new TraceMutationRange
                    {
                        StartOffset = absolute,
                        EndOffset = absolute,
                        Length = 0
                    };
                    if (!report.FirstDifferingOffset.HasValue)
                    {
                        report.FirstDifferingOffset = absolute;
                    }
                }

                current.EndOffset = absolute;
                current.Length++;
                report.ChangedByteCount++;
                if (current.Length <= MaxHexBytesPerRange)
                {
                    current.BeforeHex += beforeBuffer[i].ToString("X2");
                    current.AfterHex += afterBuffer[i].ToString("X2");
                }
                else
                {
                    current.HexTruncated = true;
                }
                report.LastDifferingOffset = absolute;
            }

            offset += requested;
        }

        CloseRange(report, ref current, commonLength - 1);

        if (afterInfo.Length > commonLength)
        {
            AddTailRange(report, after, commonLength, afterInfo.Length, true);
        }
        else if (beforeInfo.Length > commonLength)
        {
            AddTailRange(report, before, commonLength, beforeInfo.Length, false);
        }

        return report;
    }

    private static void ReadExactly(FileStream stream, byte[] buffer, int count)
    {
        int read = 0;
        while (read < count)
        {
            int current = stream.Read(buffer, read, count - read);
            if (current == 0)
            {
                throw new EndOfStreamException("Unexpected end of trace while comparing bytes.");
            }
            read += current;
        }
    }

    private static void CloseRange(
        TraceMutationReport report,
        ref TraceMutationRange current,
        long endOffset)
    {
        if (current == null)
        {
            return;
        }

        current.EndOffset = endOffset;
        report.Ranges.Add(current);
        current = null;
    }

    private static void AddTailRange(
        TraceMutationReport report,
        FileStream stream,
        long start,
        long endExclusive,
        bool afterTail)
    {
        var range = new TraceMutationRange
        {
            StartOffset = start,
            EndOffset = endExclusive - 1,
            Length = endExclusive - start
        };
        byte[] buffer = new byte[Math.Min(MaxHexBytesPerRange, (int)range.Length)];
        stream.Position = start;
        int read = stream.Read(buffer, 0, buffer.Length);
        string hex = BytesToHex(buffer, read);
        if (afterTail)
        {
            range.AfterHex = hex;
        }
        else
        {
            range.BeforeHex = hex;
        }
        range.HexTruncated = range.Length > MaxHexBytesPerRange;
        report.Ranges.Add(range);
        report.ChangedByteCount += range.Length;
        if (!report.FirstDifferingOffset.HasValue)
        {
            report.FirstDifferingOffset = start;
        }
        report.LastDifferingOffset = endExclusive - 1;
    }

    private static string BytesToHex(byte[] bytes, int count)
    {
        var builder = new StringBuilder(count * 2);
        for (int i = 0; i < count; i++)
        {
            builder.Append(bytes[i].ToString("X2"));
        }
        return builder.ToString();
    }
}
