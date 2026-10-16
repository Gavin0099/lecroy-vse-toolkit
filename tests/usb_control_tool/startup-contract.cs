using System;
using System.IO;
using System.Web.Script.Serialization;

public static class StartupContract {
    static int assertions;
    static void Equal(object actual,object expected){assertions++;if(!Object.Equals(actual,expected))throw new Exception("Expected "+expected+"; observed "+actual);}
    public static void Main(string[] args) {
        string root=args[0];Directory.CreateDirectory(root);
        TraceStartup.LogPath=Path.Combine(root,"startup-fixture.log");
        Equal(TraceStartup.ServerPath("\"C:\\Program Files\\LeCroy\\UsbSuite.exe\" /Automation"),@"C:\Program Files\LeCroy\UsbSuite.exe");
        Equal(TraceStartup.ServerPath(@"C:\Program Files\LeCroy\UsbSuite.exe /Automation"),@"C:\Program Files\LeCroy\UsbSuite.exe");
        Equal(TraceStartup.ServerPath("\"unterminated"),null);
        Equal(TraceStartup.ServerPath(""),null);
        string first=Path.Combine(root,"default 空白.exe"),other=Path.Combine(root,"registered.exe");
        File.WriteAllText(first,"fixture");File.WriteAllText(other,"fixture");
        Equal(TraceStartup.FirstExisting(new[]{first},other),first);
        Equal(TraceStartup.FirstExisting(new[]{Path.Combine(root,"missing")},other),other);
        Equal(TraceStartup.FirstExisting(new[]{Path.Combine(root,"missing")},null),null);
        string actual=TraceStartup.PhysicalDirectory(root);
        Equal(Directory.Exists(actual),true);
        Equal(File.ReadAllText(Path.Combine(actual,Path.GetFileName(first))),"fixture");
        bool failed=false;
        try{TraceStartup.CheckPython(root);}catch(FileNotFoundException ex){failed=ex.Message.Contains("解壓縮整包");}
        Equal(failed,true);
        TraceStartup.Log("fixture failure was retained");
        Equal(File.ReadAllText(TraceStartup.LogPath).Contains("fixture failure was retained"),true);
        if(args.Length>1) {
            string runtime=TraceStartup.CheckPython(args[1]);
            Equal(runtime,Path.Combine(args[1],@"runtime\python.exe"));
        }
        Console.WriteLine(new JavaScriptSerializer().Serialize(new {assertions=assertions,registered=TraceStartup.RegisteredServer(),status="passed"}));
    }
}
