using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

// Native workspace: inspection JSON is displayed as data, never as a website.
public sealed class TraceToolEntry : Form {
    [STAThread]
    public static void Main(string[] args) {
        try {if(args.Length==0){Application.EnableVisualStyles();TraceStartup.Run();}else if(args.Length==3)Run(args[0],args[1],args[2]);else throw new ArgumentException("請解壓縮整包後執行 USBTraceTriage.exe。");}
        catch(Exception ex) {TraceStartup.Log(ex.ToString());MessageBox.Show(ex.GetBaseException().Message+"\n"+TraceStartup.LogPath,"USB Trace Triage startup");Environment.ExitCode=1;}
    }
    static readonly Color Ink=TraceTheme.Text, Muted=TraceTheme.Secondary,
        Accent=TraceTheme.Action, Surface=TraceTheme.Workspace, Line=TraceTheme.Divider;
    readonly Label message=new Label(), identity=new Label(), totals=new Label(), title=new Label(), coordinates=new Label();
    readonly TraceButton choose=new TraceButton(), export=new TraceButton(), folder=new TraceButton(), locate=new TraceButton(), end=new TraceButton(), copy=new TraceButton();
    readonly TabControl tabs=new TabControl();
    readonly ListBox candidates=new ListBox();
    readonly RichTextBox summary=Document(), gaps=Document(), raw=Document();
    readonly DataGridView context=new DataGridView();
    readonly ProgressBar progress=new ProgressBar();
    readonly JavaScriptSerializer json=new JavaScriptSerializer {MaxJsonLength=16*1024*1024};
    readonly string directory;
    readonly Process controller;
    readonly System.Windows.Forms.Timer timer=new System.Windows.Forms.Timer();
    readonly ToolTip tips=new ToolTip();
    readonly Font cardFont=new Font("Microsoft JhengHei",10.5f,FontStyle.Bold), metaFont=new Font("Microsoft JhengHei",10,FontStyle.Bold);
    volatile string url;
    string caseId, reportFile, phase="starting",shownError;
    Dictionary<string,object> model;
    object[] cards=new object[0];
    bool busy,closing,allowClose;
    static Dictionary<string,object> Map(object value) {return (Dictionary<string,object>)value;}
    static string S(Dictionary<string,object> value,string key) {object x;return value.TryGetValue(key,out x)&&x!=null?Convert.ToString(x,CultureInfo.InvariantCulture):"未知";}
    static object[] Items(Dictionary<string,object> value,string key) {
        object x;if(!value.TryGetValue(key,out x)||x==null)return new object[0];
        var a=x as object[];if(a!=null)return a;var b=x as ArrayList;return b!=null?b.ToArray():new object[0];
    }
    static string Seconds(object ns) {return (Convert.ToDecimal(ns,CultureInfo.InvariantCulture)/1000000000m).ToString("0.000000000",CultureInfo.InvariantCulture)+" s";}
    static RichTextBox Document() {return new RichTextBox {ReadOnly=true,BorderStyle=BorderStyle.None,BackColor=Color.White,ForeColor=Ink,Dock=DockStyle.Fill,DetectUrls=false,ScrollBars=RichTextBoxScrollBars.Vertical,TabStop=true};}
    static Label TextLabel(string text,float size,Color color,bool bold) {return new Label {Text=text,ForeColor=color,Font=new Font("Microsoft JhengHei",size,bold?FontStyle.Bold:FontStyle.Regular),Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft};}
    static void ButtonStyle(TraceButton button,string text,bool primary) {
        button.Primary=primary;button.Text=text;button.AutoSize=true;button.Height=36;button.MinimumSize=new Size(90,36);
        button.Padding=new Padding(12,4,12,4);button.Margin=new Padding(0,0,10,0);button.FlatStyle=FlatStyle.Flat;
        button.FlatAppearance.BorderColor=primary?Accent:Line;button.BackColor=primary?Accent:Color.White;button.ForeColor=primary?Color.White:Ink;button.Cursor=Cursors.Hand;
        button.UseVisualStyleBackColor=false;
    }
    static Panel Padded(Control child,Padding padding) {var p=new Panel {Dock=DockStyle.Fill,BackColor=Color.White,Padding=padding};p.Controls.Add(child);return p;}
    static void Section(RichTextBox box,string heading,string body) {
        using(var bold=new Font("Microsoft JhengHei",11,FontStyle.Bold)) {box.SelectionFont=bold;box.SelectionColor=Ink;box.AppendText(heading+"\r\n");}
        using(var normal=new Font("Microsoft JhengHei",10.5f)) {box.SelectionFont=normal;box.SelectionColor=Ink;box.AppendText(body+"\r\n\r\n");}
    }
    static string Bullets(object[] lines) {var text=new StringBuilder();foreach(object line in lines)text.Append("• ").Append(line).Append("\r\n");return text.ToString().TrimEnd();}
    public static string Quote(string value) {
        var result=new StringBuilder("\"");int slashes=0;
        foreach(char c in value) {
            if(c=='\\') {slashes++;continue;}
            if(c=='\"') {result.Append('\\',slashes*2+1);result.Append(c);slashes=0;continue;}
            result.Append('\\',slashes);slashes=0;result.Append(c);
        }
        result.Append('\\',slashes*2);result.Append('"');return result.ToString();
    }
    public TraceToolEntry(string python,string script,string output) {
        directory=output;Text="USB Trace Triage — 檢查工作區";Size=new Size(1180,820);MinimumSize=new Size(960,680);
        Font=new Font("Microsoft JhengHei",10);ForeColor=Ink;BackColor=Surface;StartPosition=FormStartPosition.CenterScreen;
        AutoScaleMode=AutoScaleMode.Dpi;KeyPreview=true;
        var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=5,Padding=new Padding(20,12,20,12),BackColor=Surface};
        foreach(int h in new int[]{78,52,58})layout.RowStyles.Add(new RowStyle(SizeType.Absolute,h));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,78));Controls.Add(layout);
        var header=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=2,BackColor=Surface,Margin=Padding.Empty};
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,210));
        header.RowStyles.Add(new RowStyle(SizeType.Absolute,23));header.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        header.Controls.Add(TextLabel("USB TRACE TRIAGE",10,Accent,true),0,0);header.Controls.Add(TextLabel("優先檢查工作區",22,Ink,true),0,1);
        var badge=TextLabel("USB2  /  EP0\n本機分析 · 來源唯讀",10,Muted,false);badge.TextAlign=ContentAlignment.MiddleRight;
        header.Controls.Add(badge,1,0);header.SetRowSpan(badge,2);layout.Controls.Add(header,0,0);
        var toolbar=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false,Padding=new Padding(0,5,0,5),Margin=Padding.Empty};
        ButtonStyle(choose,"匯入 Trace…",true);ButtonStyle(end,"結束定位工作",false);ButtonStyle(export,"匯出 HTML…",false);ButtonStyle(folder,"工作資料夾",false);
        toolbar.Controls.AddRange(new Control[]{choose,end,export,folder});layout.Controls.Add(toolbar,0,1);
        choose.Click+=delegate {ChooseFile();};end.Click+=delegate {Send(new {action="end"});};export.Click+=delegate {ExportReport();};
        folder.Click+=delegate {ThreadPool.QueueUserWorkItem(delegate {try {Process.Start(new ProcessStartInfo("explorer.exe",Quote(directory)){UseShellExecute=false});}catch{}});};
        identity.Text="尚未載入 Trace  ·  拖入一份 .usb，或按「匯入 Trace」";identity.Dock=DockStyle.Fill;identity.TextAlign=ContentAlignment.MiddleLeft;
        identity.Padding=new Padding(14,0,14,0);identity.BackColor=Color.White;identity.AutoEllipsis=true;layout.Controls.Add(identity,0,2);
        var split=new SplitContainer {Dock=DockStyle.Fill,BackColor=Surface,SplitterWidth=12,Margin=new Padding(0,12,0,0),Size=new Size(1100,480)};
        split.Panel1MinSize=260;split.Panel2MinSize=500;split.SplitterDistance=300;
        var left=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,BackColor=Color.White,Padding=new Padding(12)};
        left.RowStyles.Add(new RowStyle(SizeType.Absolute,60));left.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        totals.Text="待檢查區段\n載入後顯示優先候選";totals.Font=metaFont;totals.Dock=DockStyle.Fill;left.Controls.Add(totals,0,0);
        candidates.Dock=DockStyle.Fill;candidates.BorderStyle=BorderStyle.None;candidates.BackColor=Color.White;
        candidates.DrawMode=DrawMode.OwnerDrawFixed;candidates.ItemHeight=112;candidates.IntegralHeight=false;candidates.AccessibleName="優先候選清單";
        candidates.DrawItem+=DrawCandidate;candidates.SelectedIndexChanged+=delegate {ShowCandidate();};left.Controls.Add(candidates,0,1);split.Panel1.Controls.Add(left);
        var right=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=4,BackColor=Color.White,Padding=new Padding(18,10,18,8)};
        foreach(int h in new int[]{46,28,50})right.RowStyles.Add(new RowStyle(SizeType.Absolute,h));right.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        title.Font=new Font("Microsoft JhengHei",14,FontStyle.Bold);title.Dock=DockStyle.Fill;title.TextAlign=ContentAlignment.MiddleLeft;title.AutoEllipsis=true;
        title.Text="從一份 Trace 開始";right.Controls.Add(title,0,0);coordinates.Dock=DockStyle.Fill;coordinates.ForeColor=Muted;right.Controls.Add(coordinates,0,1);
        var actions=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false,Padding=new Padding(0,4,0,4)};
        ButtonStyle(locate,"在 LeCroy 定位",false);ButtonStyle(copy,"複製位置",false);actions.Controls.AddRange(new Control[]{locate,copy});
        locate.Enabled=copy.Enabled=false;locate.Click+=delegate {if(OperationError)ShowRecovery();else NavigateSelected();};copy.Click+=delegate {if(coordinates.Text.Length>0)Clipboard.SetText(identity.Text+"\r\n"+coordinates.Text);};right.Controls.Add(actions,0,2);
        tabs.Dock=DockStyle.Fill;tabs.Padding=new Point(16,7);tabs.DrawMode=TabDrawMode.OwnerDrawFixed;
        tabs.DrawItem+=delegate(object sender,DrawItemEventArgs e) {
            bool active=e.Index==tabs.SelectedIndex;var rect=tabs.GetTabRect(e.Index);
            using(var brush=new SolidBrush(active?Color.White:Surface))e.Graphics.FillRectangle(brush,rect);
            TextRenderer.DrawText(e.Graphics,tabs.TabPages[e.Index].Text,Font,rect,active?Ink:Muted,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter);
            if(active)using(var pen=new Pen(Accent,3))e.Graphics.DrawLine(pen,rect.Left+6,rect.Bottom-2,rect.Right-6,rect.Bottom-2);
            if(tabs.Focused&&active)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(rect,-4,-4),Ink,Color.White);
        };
        tabs.SelectedIndexChanged+=delegate {tabs.Invalidate();};tabs.GotFocus+=delegate {tabs.Invalidate();};tabs.LostFocus+=delegate {tabs.Invalidate();};
        var overview=new TabPage("檢查提示");overview.Controls.Add(Padded(summary,new Padding(10,14,10,8)));tabs.TabPages.Add(overview);
        var evidence=new TabPage("前後交易");var evidenceLayout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,BackColor=Color.White};
        evidenceLayout.RowStyles.Add(new RowStyle(SizeType.Percent,70));evidenceLayout.RowStyles.Add(new RowStyle(SizeType.Percent,30));
        context.Dock=DockStyle.Fill;context.ReadOnly=true;context.AllowUserToAddRows=false;context.AllowUserToDeleteRows=false;context.AllowUserToResizeRows=false;
        context.AutoGenerateColumns=false;context.BackgroundColor=Color.White;context.BorderStyle=BorderStyle.None;context.RowHeadersVisible=false;
        context.SelectionMode=DataGridViewSelectionMode.FullRowSelect;context.MultiSelect=false;context.AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill;
        context.DefaultCellStyle.SelectionBackColor=TraceTheme.Selected;context.DefaultCellStyle.SelectionForeColor=Ink;
        context.AlternatingRowsDefaultCellStyle.BackColor=TraceTheme.Workspace;context.ColumnHeadersHeight=34;context.RowTemplate.Height=30;
        foreach(string column in new string[]{"Transfer","時間 (s)","Addr/EP","Request","完成欄位","資料長度"})context.Columns.Add(column,column);
        context.Columns[1].FillWeight=160;context.SelectionChanged+=delegate {ShowContext();};
        evidenceLayout.Controls.Add(context,0,0);evidenceLayout.Controls.Add(Padded(raw,new Padding(10)),0,1);evidence.Controls.Add(evidenceLayout);tabs.TabPages.Add(evidence);
        var limits=new TabPage("限制與來源");limits.Controls.Add(Padded(gaps,new Padding(10,14,10,8)));tabs.TabPages.Add(limits);right.Controls.Add(tabs,0,3);split.Panel2.Controls.Add(right);layout.Controls.Add(split,0,3);
        var status=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Padding=new Padding(0,10,0,0),Margin=Padding.Empty};
        status.RowStyles.Add(new RowStyle(SizeType.Absolute,5));status.RowStyles.Add(new RowStyle(SizeType.Percent,100));status.RowStyles.Add(new RowStyle(SizeType.Absolute,20));
        progress.Dock=DockStyle.Fill;progress.Visible=false;status.Controls.Add(progress,0,0);
        message.Dock=DockStyle.Fill;message.ForeColor=Muted;message.TextAlign=ContentAlignment.MiddleLeft;message.Text="正在檢查執行環境…";message.AutoEllipsis=true;
        status.Controls.Add(message,0,1);status.Controls.Add(TextLabel("分析範圍：USB2 標準 EP0。未涵蓋 USB3／PD；沒有候選不代表 USB PASS。",9,Muted,false),0,2);layout.Controls.Add(status,0,4);
        Section(summary,"先找值得檢查的位置","拖入一份 .usb Trace 後，工具會列出最多三個優先候選。\r\n選擇候選，即可查看觀察事實、推薦理由與下一步。");
        Section(summary,"直接核對封包","按「在 LeCroy 定位」，到原生分析器核對同一份唯讀副本。\r\n若 LeCroy 已有工作階段，工具會顯示共存限制。");
        tips.SetToolTip(export,"另存可分享的離線報告；日常檢查留在本視窗。");tips.SetToolTip(end,"釋放本工具擁有的定位工作，不關閉其他工作階段。");
        WireDrop(this);WireDrop(identity);WireDrop(candidates);WireDrop(summary);
        KeyDown+=delegate(object s,KeyEventArgs e) {if(e.Control&&e.KeyCode==Keys.O){ChooseFile();e.SuppressKeyPress=true;}};
        var info=new ProcessStartInfo(python,Quote(script)+" --native-ipc --no-browser --output "+Quote(output));
        info.UseShellExecute=false;info.CreateNoWindow=true;info.RedirectStandardInput=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        info.StandardOutputEncoding=Encoding.UTF8;info.StandardErrorEncoding=Encoding.UTF8;info.EnvironmentVariables["PYTHONUTF8"]="1";info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1";
        controller=new Process();controller.StartInfo=info;
        controller.OutputDataReceived+=delegate(object s,DataReceivedEventArgs e) {if(e.Data==null)return;try {var data=json.Deserialize<Dictionary<string,object>>(e.Data);if(data.ContainsKey("url"))url=(string)data["url"];}catch{}};
        controller.ErrorDataReceived+=delegate(object s,DataReceivedEventArgs e) {if(e.Data!=null) {try {File.AppendAllText(Path.Combine(Path.GetDirectoryName(directory),"launcher-errors.log"),e.Data+Environment.NewLine,Encoding.UTF8);}catch{}}};
        controller.Start();controller.BeginOutputReadLine();controller.BeginErrorReadLine();timer.Interval=400;timer.Tick+=delegate {RefreshStatus();};timer.Start();
        FormClosing+=delegate(object sender,FormClosingEventArgs e) {
            if(allowClose)return;if(busy) {e.Cancel=true;message.Text="原生操作仍在進行；請等待完成或無回應狀態，再結束工作。";return;}
            if(!controller.HasExited) {e.Cancel=true;if(!closing) {closing=true;choose.Enabled=false;Send(new {action="close"});message.Text="正在檢查完整性並釋放工具工作…";}}
        };
        FormClosed+=delegate {timer.Stop();timer.Dispose();tips.Dispose();cardFont.Dispose();metaFont.Dispose();controller.Dispose();};
    }
    void WireDrop(Control control) {
        control.AllowDrop=true;control.DragEnter+=delegate(object s,DragEventArgs e) {e.Effect=!busy&&!closing&&e.Data.GetDataPresent(DataFormats.FileDrop)?DragDropEffects.Copy:DragDropEffects.None;};
        control.DragDrop+=delegate(object s,DragEventArgs e) {if(e.Data.GetDataPresent(DataFormats.FileDrop))Import((string[])e.Data.GetData(DataFormats.FileDrop),"drag_drop");};
    }
    void ChooseFile() {if(busy||closing)return;using(var dialog=new OpenFileDialog()) {dialog.Filter="USB Trace (*.usb)|*.usb";dialog.Multiselect=false;if(dialog.ShowDialog(this)==DialogResult.OK)Import(new string[]{dialog.FileName},"file_picker");}}
    void Send(object command) {
        try {if(controller.HasExited)throw new InvalidOperationException("控制程序已結束");controller.StandardInput.WriteLine(json.Serialize(command));controller.StandardInput.Flush();}
        catch(Exception ex) {message.Text="無法傳送操作："+ex.Message;}
    }
    void Import(string[] files,string method) {
        if(busy||closing) {message.Text="目前工作尚未完成，請稍後再匯入。";return;}
        if(files==null||files.Length!=1||!File.Exists(files[0])||!String.Equals(Path.GetExtension(files[0]),".usb",StringComparison.OrdinalIgnoreCase)) {message.Text="一次只接受一份可讀取的 .usb 檔案；不接受資料夾或多檔。";return;}
        if(url==null||controller.HasExited) {message.Text="工具尚未就緒，請檢查執行環境。";return;}
        Send(new {action="import",path=Path.GetFullPath(files[0]),input_method=method});busy=true;choose.Enabled=locate.Enabled=false;message.Text="已接收檔案，正在開始分析…";
    }
    void NavigateSelected() {
        if(busy||caseId==null||candidates.SelectedIndex<0)return;
        Send(new {action="navigate",case_id=caseId,rank=Convert.ToInt32(Map(cards[candidates.SelectedIndex])["rank"])});busy=true;locate.Enabled=false;message.Text="正在定位，請稍候…";
    }
    void ExportReport() {
        if(reportFile==null||!File.Exists(reportFile))return;
        using(var save=new SaveFileDialog()) {save.Filter="HTML report (*.html)|*.html";save.FileName="usb-trace-report.html";
            if(save.ShowDialog(this)==DialogResult.OK) {try {
                if(!String.Equals(Path.GetExtension(save.FileName),".html",StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("請以 .html 副檔名儲存報告。");
                File.Copy(reportFile,save.FileName,true);message.Text="已匯出離線報告："+save.FileName;
            }catch(Exception ex){MessageBox.Show(this,"匯出失敗："+ex.Message,"匯出 HTML");}}}
    }
    void DrawCandidate(object sender,DrawItemEventArgs e) {
        if(e.Index<0||e.Index>=cards.Length)return;var c=Map(cards[e.Index]);bool selected=(e.State&DrawItemState.Selected)!=0;
        using(var brush=new SolidBrush(selected?TraceTheme.Selected:Color.White))e.Graphics.FillRectangle(brush,e.Bounds);
        if(selected)using(var brush=new SolidBrush(Accent))e.Graphics.FillRectangle(brush,new Rectangle(e.Bounds.Left,e.Bounds.Top,4,e.Bounds.Height));
        var box=new Rectangle(e.Bounds.Left+14,e.Bounds.Top+10,e.Bounds.Width-26,22);
        TextRenderer.DrawText(e.Graphics,"#"+S(c,"rank")+"   TRANSFER "+Items(c,"transfer_indices")[0],metaFont,box,selected?Accent:Muted,TextFormatFlags.EndEllipsis);
        box.Y+=26;box.Height=42;TextRenderer.DrawText(e.Graphics,S(c,"title"),cardFont,box,Ink,TextFormatFlags.WordBreak|TextFormatFlags.EndEllipsis);
        box.Y+=45;box.Height=20;TextRenderer.DrawText(e.Graphics,Seconds(c["start_ns"]),Font,box,Muted,TextFormatFlags.EndEllipsis);
        using(var pen=new Pen(Line))e.Graphics.DrawLine(pen,e.Bounds.Left+12,e.Bounds.Bottom-1,e.Bounds.Right-12,e.Bounds.Bottom-1);e.DrawFocusRectangle();
    }
    void LoadModel(string id) {
        Guid parsed;if(!Guid.TryParseExact(id,"N",out parsed))throw new InvalidDataException("Invalid case identity");
        model=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(directory,id,"inspection.json"),Encoding.UTF8));
        caseId=id;reportFile=Path.Combine(directory,id,"report.html");cards=Items(model,"candidates");
        candidates.Items.Clear();foreach(object c in cards)candidates.Items.Add("Transfer "+Items(Map(c),"transfer_indices")[0]);
        totals.Text="優先檢查 "+cards.Length+" / "+S(model,"episode_count")+" 個區段\n另 "+S(model,"omitted_episodes")+" 個未顯示";
        if(cards.Length>0)candidates.SelectedIndex=0;
        else {title.Text="本次未找到足夠可疑的區段";coordinates.Text="分析範圍：USB2 標準 EP0";summary.Clear();
            Section(summary,"目前結果","本次分析範圍內未找到足夠可疑的區段。\r\n這不代表整份 USB Trace 或 USB-CV 測試通過。");
            Section(summary,"下一步","若測試仍失敗，請核對測試 log 與分析範圍；USB3、PD 或其他傳輸需另外檢查。");context.Rows.Clear();raw.Clear();ShowLimits(null);}
    }
    void ShowCandidate() {
        int i=candidates.SelectedIndex;if(i<0||i>=cards.Length)return;var c=Map(cards[i]);title.Text=S(c,"title");
        coordinates.Text="Transfer "+Items(c,"transfer_indices")[0]+"   ·   "+Seconds(c["start_ns"])+"   ·   Address "+S(c,"address")+" / EP "+S(c,"endpoint");
        summary.Clear();Section(summary,"工程師下一步",S(c,"next_step"));Section(summary,"發生什麼事",Bullets(Items(c,"facts")));
        Section(summary,"為什麼優先看這裡",Bullets(Items(c,"reasons")));summary.SelectionStart=0;summary.ScrollToCaret();context.Rows.Clear();
        foreach(object item in Items(c,"context")) {var row=Map(item);
            int n=context.Rows.Add(S(row,"index"),row.ContainsKey("timestamp_ns")?Seconds(row["timestamp_ns"]).Replace(" s",""):"未知",S(row,"address")+"/"+S(row,"endpoint"),S(row,"request"),S(row,"completed"),S(row,"data_length"));context.Rows[n].Tag=row;}
        context.ClearSelection();
        foreach(DataGridViewRow row in context.Rows) {
            if(Convert.ToString(row.Cells[0].Value)==Convert.ToString(Items(c,"transfer_indices")[0])) {
                row.DefaultCellStyle.Font=metaFont;context.CurrentCell=row.Cells[0];row.Selected=true;break;
            }
        }
        ShowLimits(c);copy.Enabled=true;locate.Enabled=!busy&&phase!="unresponsive"&&phase!="cleanup_unknown";ShowContext();
    }
    void ShowLimits(Dictionary<string,object> c) {
        gaps.Clear();if(c!=null)Section(gaps,"這個候選的證據缺口",Bullets(Items(c,"evidence_gaps")));
        Section(gaps,"本次分析限制",Bullets(Items(model,"limitations")));Section(gaps,"來源識別","規則："+S(model,"rule_version")+"\r\nSHA-256："+S(model,"trace_sha256")+"\r\nTransfer 與 Packet 編號不同；API 成功仍須核對 LeCroy 畫面。");gaps.SelectionStart=0;gaps.ScrollToCaret();
    }
    void ShowContext() {
        raw.Clear();if(context.SelectedRows.Count==0)return;var row=context.SelectedRows[0].Tag as Dictionary<string,object>;if(row==null)return;
        raw.Text="Transfer "+S(row,"index")+" · native Completed="+S(row,"completed")+" · Error="+S(row,"error")+"\r\nSETUP/payload prefix: "+S(row,"native_prefix_hex")+"\r\nData prefix: "+S(row,"data_prefix_hex")+"\r\n子封包對應尚未核實；以上欄位不能單獨當成根因判定。";
    }
    bool OperationError {get{return phase=="error"||phase=="unresponsive"||phase=="cleanup_unknown";}}
    void ShowRecovery() {
        MessageBox.Show(this,message.Text+"\n\n先查看工作資料夾的 analysis.log、operations.jsonl 與定位日誌。\n若已有 LeCroy 工作階段，先儲存既有工作，再安排獨立分析。\n若原生呼叫無回應或清理狀態未知，請先確認 LeCroy 狀態；工具不會強制關閉其他工作。\n可先複製定位資訊供人工核對。","錯誤與恢復方式",MessageBoxButtons.OK,MessageBoxIcon.Error);
    }
    void RefreshStatus() {
        try {
            string status=Path.Combine(directory,"status.json");
            if(File.Exists(status)) {
                var value=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(status,Encoding.UTF8));
                busy=(bool)value["busy"];message.Text=S(value,"message");phase=S(value,"phase");
                message.ForeColor=OperationError?TraceTheme.Error:Muted;
                if(OperationError&&model==null&&shownError!=message.Text) {
                    shownError=message.Text;title.Text="未能完成 Trace 分析";coordinates.Text="請先查看錯誤與恢復方式";
                    totals.Text="分析未完成\n尚無可用候選";summary.Clear();
                    Section(summary,"發生什麼事",message.Text);
                    Section(summary,"下一步","按「查看錯誤與恢復方式」，或開啟工作資料夾檢查完整日誌。修復後再匯入 Trace。");
                }
                if(!OperationError)shownError=null;
                if((phase=="preparing"||phase=="extracting")&&(model!=null||title.Text!="正在讀取 Trace")) {
                    model=null;caseId=reportFile=null;cards=new object[0];candidates.Items.Clear();context.Rows.Clear();raw.Clear();gaps.Clear();summary.Clear();
                    totals.Text="正在分析…";title.Text="正在讀取 Trace";coordinates.Text="完成後在這裡顯示優先候選";copy.Enabled=false;
                }
                string id=S(value,"case_id");if(id!="未知"&&id!=caseId)LoadModel(id);
                string name=S(value,"trace_name");if(name!="未知")identity.Text=name+(model!=null?"   ·   SHA "+S(model,"trace_sha256").Substring(0,12):"");
            } else if(url!=null) {message.Text="已就緒。拖入一份 .usb 或按「匯入 Trace」。";busy=false;}
            bool usable=url!=null&&!controller.HasExited&&!busy&&!closing;
            choose.Enabled=usable&&phase!="unresponsive"&&phase!="cleanup_unknown";
            choose.Text=busy?(phase=="navigating"?"正在定位…":"正在分析…"):model!=null||OperationError?"匯入其他 Trace…":"匯入 Trace…";
            choose.Primary=!busy&&!OperationError&&cards.Length==0;
            locate.Visible=cards.Length>0||OperationError;
            locate.Text=OperationError?"查看錯誤與恢復方式":"在 LeCroy 定位";
            locate.Primary=!busy&&(cards.Length>0||OperationError);
            locate.Enabled=usable&&(OperationError||(caseId!=null&&candidates.SelectedIndex>=0));
            end.Enabled=usable&&caseId!=null;export.Enabled=reportFile!=null&&File.Exists(reportFile)&&!closing;
            progress.Visible=busy;progress.Style=busy?ProgressBarStyle.Marquee:ProgressBarStyle.Blocks;
            if(controller.HasExited) {choose.Enabled=locate.Enabled=end.Enabled=false;if(closing) {allowClose=true;Close();}else message.Text="本機控制程序已結束。請檢查工作資料夾與 launcher-errors.log。";}
        } catch(IOException) {} catch(Exception ex) {message.Text="狀態讀取失敗："+ex.Message;}
    }
    public static void Run(string python,string script,string output) {
        if(Thread.CurrentThread.GetApartmentState()!=ApartmentState.STA)throw new InvalidOperationException("STA required");Application.EnableVisualStyles();Application.Run(new TraceToolEntry(python,script,output));
    }
}
