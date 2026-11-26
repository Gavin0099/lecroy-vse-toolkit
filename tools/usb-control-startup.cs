using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;
using System.Runtime.InteropServices;

// No PowerShell or installed Python is needed to show the first window.
public static class TraceStartup {
    public static string LogPath;
    public static void Log(string text) {
        try {File.AppendAllText(LogPath,DateTime.UtcNow.ToString("o")+" "+text+Environment.NewLine,Encoding.UTF8);}catch{}
    }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern SafeFileHandle CreateFile(string path,uint access,uint share,IntPtr security,uint disposition,uint flags,IntPtr template);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern uint GetFinalPathNameByHandle(SafeFileHandle handle,StringBuilder path,uint length,uint flags);
    public static string PhysicalDirectory(string directory) {
        using(var handle=CreateFile(directory,0,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero)) {
            if(handle.IsInvalid)throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
            var value=new StringBuilder(32768);
            uint size=GetFinalPathNameByHandle(handle,value,(uint)value.Capacity,0);
            if(size==0||size>=value.Capacity)throw new IOException("無法確認工作資料夾實際路徑。");
            string path=value.ToString();
            if(path.StartsWith(@"\\?\UNC\"))return @"\\"+path.Substring(8);
            return path.StartsWith(@"\\?\")?path.Substring(4):path;
        }
    }
    public static string ServerPath(string command) {
        if(String.IsNullOrWhiteSpace(command))return null;
        command=Environment.ExpandEnvironmentVariables(command.Trim());
        if(command.StartsWith("\"")) {int end=command.IndexOf('"',1);return end>1?command.Substring(1,end-1):null;}
        int suffix=command.IndexOf(".exe",StringComparison.OrdinalIgnoreCase);
        return suffix>=0?command.Substring(0,suffix+4):null;
    }
    public static string RegisteredServer() {
        foreach(var view in new[]{RegistryView.Registry64,RegistryView.Registry32}) {
            using(var root=RegistryKey.OpenBaseKey(RegistryHive.ClassesRoot,view))
            using(var prog=root.OpenSubKey(@"CATC.USBTracer\CLSID")) {
                string clsid=prog==null?null:prog.GetValue(null) as string;
                if(clsid==null)continue;
                using(var key=root.OpenSubKey(@"CLSID\"+clsid+@"\LocalServer32")) {
                    string path=ServerPath(key==null?null:key.GetValue(null) as string);
                    if(path!=null&&File.Exists(path))return Path.GetFullPath(path);
                }
            }
        }
        return null;
    }
    public static string FindAnalyzer() {
        var defaults=new System.Collections.Generic.List<string>();
        foreach(string folder in new[]{Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                                      Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86)}) {
            defaults.Add(Path.Combine(folder,@"LeCroy\USB Protocol Suite\UsbSuite.exe"));
        }
        return FirstExisting(defaults.ToArray(),RegisteredServer());
    }
    public static string FirstExisting(string[] defaults,string registered) {
        foreach(string path in defaults)if(File.Exists(path))return Path.GetFullPath(path);
        return registered!=null&&File.Exists(registered)?Path.GetFullPath(registered):null;
    }
    public static string CheckPython(string root) {
        string python=Path.Combine(root,@"runtime\python.exe");
        if(!File.Exists(python))throw new FileNotFoundException("內附 Python 不完整。請解壓縮整包後，執行 USBTraceTriage.exe。",python);
        var info=new ProcessStartInfo(python,"-I -B -c "+TraceToolEntry.Quote("import sys,ctypes,ssl,usb_control_app; assert sys.version_info >= (3,10); print(sys.version)"));
        info.UseShellExecute=false;info.CreateNoWindow=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        using(var process=Process.Start(info)) {
            var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
            if(!process.WaitForExit(15000)){try{process.Kill();}catch{}throw new TimeoutException("內附 Python 檢查逾時，請查看啟動日誌。");}
            string result=stdout.Result+stderr.Result;Log("Python: "+result.Trim());
            if(process.ExitCode!=0)throw new InvalidOperationException("內附 Python 無法啟動："+result);
        }
        return python;
    }
    public static void ValidateAnalyzer(string path) {
        if(!File.Exists(path)||!String.Equals(Path.GetFileName(path),"UsbSuite.exe",StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("請指定 LeCroy USB Protocol Suite 的 UsbSuite.exe。");
        string registered=RegisteredServer();
        if(registered==null||!String.Equals(Path.GetFullPath(path),registered,StringComparison.OrdinalIgnoreCase)||Type.GetTypeFromProgID("CATC.USBTracer")==null)
            throw new InvalidOperationException("LeCroy COM 註冊缺少或與指定路徑不一致。請用 LeCroy 安裝程式修復 Automation/COM，再重新啟動本工具。");
        Log("Analyzer: "+path+"; version="+FileVersionInfo.GetVersionInfo(path).FileVersion);
    }
    public static void Run() {
        string logs=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"LeCroyTraceTriage\startup");
        Directory.CreateDirectory(logs);logs=PhysicalDirectory(logs);
        LogPath=Path.Combine(logs,"startup-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,8)+".log");
        Log("Start; root="+AppDomain.CurrentDomain.BaseDirectory+"; OS="+Environment.OSVersion+"; process64="+Environment.Is64BitProcess);
        Application.Run(new StartupWindow());
    }
    sealed class StartupWindow:Form {
        bool finished;
        readonly Label status=new Label {Dock=DockStyle.Fill,Text="正在啟動 USB Trace Triage…\n檢查內附 Python 與 LeCroy。",TextAlign=ContentAlignment.MiddleLeft,Padding=new Padding(24)};
        public StartupWindow() {
            Text="USB Trace Triage — 啟動檢查";ClientSize=new Size(540,150);StartPosition=FormStartPosition.CenterScreen;
            Font=new Font("Microsoft JhengHei",11);BackColor=Color.White;Controls.Add(status);
            FormClosing+=delegate(object sender,FormClosingEventArgs e){if(!finished){e.Cancel=true;status.Text="啟動檢查進行中，請稍候。";}};
            Shown+=async delegate {
                try {
                    string root=AppDomain.CurrentDomain.BaseDirectory;
                    string python=await Task.Run(()=>CheckPython(root));
                    string analyzer=await Task.Run(()=>FindAnalyzer());
                    if(analyzer==null) {
                        status.Text="未找到 LeCroy，請指定 UsbSuite.exe。";
                        using(var picker=new OpenFileDialog {Title="指定 LeCroy UsbSuite.exe",Filter="LeCroy USB Protocol Suite|UsbSuite.exe",CheckFileExists=true}) {
                            if(picker.ShowDialog(this)!=DialogResult.OK)throw new InvalidOperationException("未指定 LeCroy 安裝位置，啟動已停止。");
                            analyzer=picker.FileName;
                        }
                    }
                    await Task.Run(()=>ValidateAnalyzer(analyzer));
                    Environment.SetEnvironmentVariable("LECROY_USB_SUITE_EXE",analyzer);
                    string output=Path.Combine(Path.GetDirectoryName(logsDirectory()),"run-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,8));
                    Log("Workspace: "+output);
                    using(var workspace=new TraceToolEntry(python,Path.Combine(root,@"tools\usb_control_app.py"),output)) {Hide();workspace.ShowDialog();}
                    Log("Workspace closed");finished=true;Close();
                } catch(Exception ex) {
                    Environment.ExitCode=1;Log(ex.ToString());
                    status.Text="無法啟動。啟動日誌已保留。";
                    MessageBox.Show(this,ex.GetBaseException().Message+"\n\n啟動日誌：\n"+LogPath,"USB Trace Triage — 啟動失敗",MessageBoxButtons.OK,MessageBoxIcon.Error);
                    finished=true;Close();
                }
            };
        }
        static string logsDirectory(){return Path.GetDirectoryName(LogPath);}
    }
}
