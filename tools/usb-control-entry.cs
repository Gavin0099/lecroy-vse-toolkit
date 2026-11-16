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
    readonly Label findings=TextLabel("從一份 Trace 開始",14,Ink,true), coverage=TextLabel("分析後顯示擷取範圍與限制",10,Muted,false);
    readonly Label candidateStatus=TextLabel("等待匯入",9,Muted,true), timelineNote=TextLabel("尚無關聯證據",9,Muted,false);
    readonly ListBox timeline=new ListBox();
    readonly TableLayoutPanel overviewLayout;
    readonly TraceButton inspectEvidence=new TraceButton();
    readonly TraceButton toggleEvidence=new TraceButton();
    readonly Label badge=TextLabel("USB / PCIe TRACE\n本機分析 · 來源唯讀",10,Muted,false), scopeLabel=TextLabel("分析完成後顯示實際協定範圍；無候選不代表協定測試通過。",9,Muted,false);
    readonly ComboBox protocols=new ComboBox(), nativeTargets=new ComboBox(),flowView=new ComboBox();
    readonly TraceButton engineerContext=new TraceButton();
    readonly TraceButton configUr=new TraceButton();
    readonly TraceButton nextCheck=new TraceButton();
    readonly CheckBox observed=new CheckBox {Text="已觀察流程（非候選）",AutoSize=true,Enabled=false};
    readonly CheckBox showAll=new CheckBox {Text="顯示全部候選",AutoSize=true,Visible=false};
    readonly Button previousPage=new Button {Text="上一頁",AutoSize=true,Visible=false},nextPage=new Button {Text="下一頁",AutoSize=true,Visible=false};
    readonly Label pageLabel=new Label {AutoSize=true,Visible=false};
    readonly TraceButton copyFile=new TraceButton(), cancel=new TraceButton(),locateStage=new TraceButton();
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
    Dictionary<string,object> pageIndex;
    Dictionary<string,object> configUrStatus;
    ConfigUrForm configUrView;
    int currentPage;
    object[] cards=new object[0];
    object[] allCards=new object[0];
    object[] allObservations=new object[0];
    object[] allFlows=new object[0];
    string modelRevision="0";
    bool changingProtocol;
    bool busy,closing,allowClose;
    bool pendingPcie;
    bool syncingEvidence;
    bool IsPcie {get{return model!=null&&S(model,"protocol")=="pcie";}}
    bool FlowReady {get{return IsPcie&&model.ContainsKey("flow_analysis");}}
    bool FlowMode {get{return FlowReady&&flowView.SelectedIndex==0;}}
    static string CardTime(Dictionary<string,object> c){return c.ContainsKey("start_ns")&&c["start_ns"]!=null?Seconds(c["start_ns"]):S(c,"time_display")+"（原始顯示精度）";}
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
    static void Brief(RichTextBox box,string heading,string body){
        using(var bold=new Font("Microsoft JhengHei",10.5f,FontStyle.Bold)){box.SelectionFont=bold;box.SelectionColor=Ink;box.AppendText(heading+"　");}
        using(var normal=new Font("Microsoft JhengHei",10.5f)){box.SelectionFont=normal;box.AppendText(body+"\r\n\r\n");}
    }
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
        directory=output;Text="USB / PCIe Trace Triage — 檢查工作區";Size=new Size(1180,820);MinimumSize=new Size(960,680);
        Font=new Font("Microsoft JhengHei",10);ForeColor=Ink;BackColor=Surface;StartPosition=FormStartPosition.CenterScreen;
        AutoScaleMode=AutoScaleMode.Dpi;KeyPreview=true;
        var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=5,Padding=new Padding(20,12,20,12),BackColor=Surface};
        foreach(int h in new int[]{64,48,94})layout.RowStyles.Add(new RowStyle(SizeType.Absolute,h));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,64));Controls.Add(layout);
        var header=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=2,BackColor=Surface,Margin=Padding.Empty};
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,210));
        header.RowStyles.Add(new RowStyle(SizeType.Absolute,23));header.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        header.Controls.Add(TextLabel("USB / PCIe TRACE TRIAGE",10,Muted,true),0,0);header.Controls.Add(TextLabel("Trace 檢查工作區",18,Ink,true),0,1);
        badge.TextAlign=ContentAlignment.MiddleRight;
        header.Controls.Add(badge,1,0);header.SetRowSpan(badge,2);layout.Controls.Add(header,0,0);
        var toolbar=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false,Padding=new Padding(0,5,0,5),Margin=Padding.Empty};
        ButtonStyle(choose,"匯入 Trace…",true);ButtonStyle(end,"結束定位工作",false);ButtonStyle(export,"匯出 HTML…",false);ButtonStyle(folder,"工作資料夾",false);
        ButtonStyle(cancel,"取消分析",false);cancel.Visible=false;cancel.Click+=delegate {Send(new {action="cancel"});cancel.Enabled=false;};
        ButtonStyle(engineerContext,"工程情境…",false);engineerContext.Visible=false;engineerContext.Click+=delegate {EditContext();};
        ButtonStyle(configUr,"暫存器與 UR…",false);configUr.Visible=false;configUr.Click+=delegate {OpenConfigUr();};
        toolbar.Controls.AddRange(new Control[]{choose,end,export,folder,engineerContext,configUr,cancel});layout.Controls.Add(toolbar,0,1);
        choose.Click+=delegate {ChooseFile();};end.Click+=delegate {Send(new {action="end"});};export.Click+=delegate {ExportReport();};
        folder.Click+=delegate {ThreadPool.QueueUserWorkItem(delegate {try {Process.Start(new ProcessStartInfo("explorer.exe",Quote(directory)){UseShellExecute=false});}catch{}});};
        identity.Text="尚未載入 Trace  ·  拖入一份 .usb / .pex，或按「匯入 Trace」";identity.Dock=DockStyle.Fill;identity.TextAlign=ContentAlignment.MiddleLeft;
        identity.BackColor=Color.White;identity.AutoEllipsis=true;identity.Font=new Font("Microsoft JhengHei",9);
        var discovery=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Padding=new Padding(14,4,14,4),BackColor=Color.White,Margin=Padding.Empty};
        discovery.RowStyles.Add(new RowStyle(SizeType.Absolute,24));discovery.RowStyles.Add(new RowStyle(SizeType.Absolute,32));discovery.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        findings.AutoEllipsis=coverage.AutoEllipsis=true;
        discovery.Controls.Add(identity,0,0);discovery.Controls.Add(findings,0,1);discovery.Controls.Add(coverage,0,2);layout.Controls.Add(discovery,0,2);
        var split=new SplitContainer {Dock=DockStyle.Fill,BackColor=Surface,SplitterWidth=12,Margin=new Padding(0,12,0,0),Size=new Size(1100,480)};
        split.Panel1MinSize=260;split.Panel2MinSize=500;split.SplitterDistance=300;
        var left=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=4,BackColor=Color.White,Padding=new Padding(12)};
        left.RowStyles.Add(new RowStyle(SizeType.Absolute,36));left.RowStyles.Add(new RowStyle(SizeType.Absolute,60));left.RowStyles.Add(new RowStyle(SizeType.Absolute,30));left.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        protocols.Dock=DockStyle.Fill;protocols.DropDownStyle=ComboBoxStyle.DropDownList;protocols.AccessibleName="分析協定與資料狀態";
        protocols.Items.Add("分析後顯示協定範圍");protocols.SelectedIndex=0;protocols.Enabled=false;
        protocols.SelectedIndexChanged+=delegate {SelectProtocol();};left.Controls.Add(protocols,0,0);
        totals.Text="待檢查區段\n載入後顯示優先候選";totals.Font=metaFont;totals.Dock=DockStyle.Fill;left.Controls.Add(totals,0,1);
        candidates.Dock=DockStyle.Fill;candidates.BorderStyle=BorderStyle.None;candidates.BackColor=Color.White;
        candidates.DrawMode=DrawMode.OwnerDrawFixed;candidates.ItemHeight=124;candidates.IntegralHeight=false;candidates.AccessibleName="候選清單；待覆核不代表故障";
        observed.CheckedChanged+=delegate {if(!changingProtocol)PopulateProtocol();};
        showAll.CheckedChanged+=delegate {if(!changingProtocol)ChangePage(0);};
        flowView.DropDownStyle=ComboBoxStyle.DropDownList;flowView.Width=245;flowView.AccessibleName="流程階段或次要交易觀察";flowView.Visible=false;
        flowView.Items.AddRange(new object[]{"連線觀察與待確認階段","次要交易觀察"});flowView.SelectedIndex=0;
        flowView.SelectedIndexChanged+=delegate {if(!changingProtocol){changingProtocol=true;showAll.Checked=false;changingProtocol=false;ChangePage(0);}};
        previousPage.Click+=delegate {if(!busy)ChangePage(currentPage-1);};
        nextPage.Click+=delegate {if(!busy)ChangePage(currentPage+1);};
        var listOptions=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=true};listOptions.Controls.AddRange(new Control[]{flowView,observed,showAll,previousPage,nextPage,pageLabel});left.Controls.Add(listOptions,0,2);
        candidates.DrawItem+=DrawCandidate;candidates.SelectedIndexChanged+=delegate {ShowCandidate();};left.Controls.Add(candidates,0,3);split.Panel1.Controls.Add(left);
        var right=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=4,BackColor=Color.White,Padding=new Padding(18,10,18,8)};
        foreach(int h in new int[]{60,28,50})right.RowStyles.Add(new RowStyle(SizeType.Absolute,h));right.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        title.Font=new Font("Microsoft JhengHei",14,FontStyle.Bold);title.Dock=DockStyle.Fill;title.TextAlign=ContentAlignment.MiddleLeft;title.AutoEllipsis=true;
        title.Text="從一份 Trace 開始";var issueHeader=new TableLayoutPanel {Dock=DockStyle.Fill,RowCount=2,ColumnCount=1,Margin=Padding.Empty};
        issueHeader.RowStyles.Add(new RowStyle(SizeType.Absolute,20));issueHeader.RowStyles.Add(new RowStyle(SizeType.Percent,100));issueHeader.Controls.Add(candidateStatus,0,0);issueHeader.Controls.Add(title,0,1);right.Controls.Add(issueHeader,0,0);
        coordinates.Dock=DockStyle.Fill;coordinates.ForeColor=Muted;coordinates.AutoEllipsis=true;right.Controls.Add(coordinates,0,1);
        var actions=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false,Padding=new Padding(0,4,0,4)};
        ButtonStyle(locate,"在 LeCroy 定位",false);ButtonStyle(copy,"複製位置",false);ButtonStyle(copyFile,"複製副本路徑",false);copyFile.Visible=false;
        copyFile.Click+=delegate {if(IsPcie)Clipboard.SetText(S(model,"display_trace_path"));};actions.Controls.AddRange(new Control[]{locate,copy,copyFile});
        ButtonStyle(locateStage,"定位最後階段",false);locateStage.Visible=false;actions.Controls.Add(locateStage);
        ButtonStyle(nextCheck,"查看需補資料",false);nextCheck.Visible=false;actions.Controls.Add(nextCheck);
        nextCheck.Click+=delegate {ShowNextCheck();};
        locateStage.Click+=delegate {Send(new {action="navigate",case_id=caseId,rank=1,target_index=0,item_kind="observation"});busy=true;locateStage.Enabled=false;};
        nativeTargets.DropDownStyle=ComboBoxStyle.DropDownList;nativeTargets.Width=210;nativeTargets.AccessibleName="原生定位目標";
        nativeTargets.SelectedIndexChanged+=delegate {UpdateCoordinates();};actions.Controls.Add(nativeTargets);nativeTargets.Visible=false;
        locate.Enabled=copy.Enabled=false;locate.Click+=delegate {if(OperationError)ShowRecovery();else NavigateSelected();};copy.Click+=delegate {if(IsPcie&&candidates.SelectedIndex>=0)Clipboard.SetText(S(Primary(Map(cards[candidates.SelectedIndex])),"index"));else if(coordinates.Text.Length>0)Clipboard.SetText(identity.Text+"\r\n"+coordinates.Text);};right.Controls.Add(actions,0,2);
        tabs.Dock=DockStyle.Fill;tabs.Padding=new Point(16,7);tabs.DrawMode=TabDrawMode.OwnerDrawFixed;
        tabs.DrawItem+=delegate(object sender,DrawItemEventArgs e) {
            bool active=e.Index==tabs.SelectedIndex;var rect=tabs.GetTabRect(e.Index);
            using(var brush=new SolidBrush(active?Color.White:Surface))e.Graphics.FillRectangle(brush,rect);
            TextRenderer.DrawText(e.Graphics,tabs.TabPages[e.Index].Text,Font,rect,active?Ink:Muted,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter);
            if(active)using(var pen=new Pen(Accent,3))e.Graphics.DrawLine(pen,rect.Left+6,rect.Bottom-2,rect.Right-6,rect.Bottom-2);
            if(tabs.Focused&&active)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(rect,-4,-4),Ink,Color.White);
        };
        tabs.SelectedIndexChanged+=delegate {tabs.Invalidate();};tabs.GotFocus+=delegate {tabs.Invalidate();};tabs.LostFocus+=delegate {tabs.Invalidate();};
        var overview=new TabPage("事件說明");overviewLayout=new TableLayoutPanel {Dock=DockStyle.Fill,RowCount=3,ColumnCount=1,BackColor=Color.White};
        overviewLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));overviewLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,36));overviewLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,128));
        overviewLayout.Controls.Add(Padded(summary,new Padding(10,10,10,2)),0,0);
        ButtonStyle(toggleEvidence,"展開關聯事件",false);toggleEvidence.Height=30;toggleEvidence.MinimumSize=new Size(90,30);toggleEvidence.Margin=new Padding(10,0,10,3);
        toggleEvidence.Click+=delegate{bool expand=overviewLayout.RowStyles[2].Height==0;overviewLayout.GetControlFromPosition(0,2).Visible=expand;overviewLayout.RowStyles[2].Height=expand?128:0;toggleEvidence.Text=expand?"收合關聯事件":"展開關聯事件（"+timeline.Items.Count+"）";};overviewLayout.Controls.Add(toggleEvidence,0,1);
        var timelineLayout=new TableLayoutPanel {Dock=DockStyle.Fill,RowCount=3,ColumnCount=1,Padding=new Padding(10,0,10,4),BackColor=Color.White};
        timelineLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,24));timelineLayout.RowStyles.Add(new RowStyle(SizeType.Percent,100));timelineLayout.RowStyles.Add(new RowStyle(SizeType.Absolute,32));
        timeline.AccessibleName="關聯事件；選取後同步來源證據";timeline.Dock=DockStyle.Fill;timeline.BorderStyle=BorderStyle.None;timeline.DrawMode=DrawMode.OwnerDrawFixed;timeline.ItemHeight=32;timeline.IntegralHeight=false;timeline.BackColor=Color.White;
        timeline.DrawItem+=DrawEvidence;timeline.SelectedIndexChanged+=delegate {SelectEvidence();};
        ButtonStyle(inspectEvidence,"查看選取事件的完整證據",false);inspectEvidence.Height=30;inspectEvidence.MinimumSize=new Size(90,30);inspectEvidence.Enabled=false;
        inspectEvidence.Click+=delegate {if(IsPcie&&context.SelectedRows.Count>0){tabs.SelectedIndex=2;var row=context.SelectedRows[0].Tag as Dictionary<string,object>;if(row!=null){Section(gaps,"所選事件原始欄位",json.Serialize(row));gaps.SelectionStart=gaps.TextLength;gaps.ScrollToCaret();}}else{tabs.SelectedIndex=1;context.Focus();}};
        timelineLayout.Controls.Add(timelineNote,0,0);timelineLayout.Controls.Add(timeline,0,1);timelineLayout.Controls.Add(inspectEvidence,0,2);overviewLayout.Controls.Add(timelineLayout,0,2);overview.Controls.Add(overviewLayout);tabs.TabPages.Add(overview);
        overviewLayout.RowStyles[1].Height=overviewLayout.RowStyles[2].Height=0;
        toggleEvidence.Visible=timelineLayout.Visible=false;
        var evidence=new TabPage("前後交易");var evidenceLayout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,BackColor=Color.White};
        evidenceLayout.RowStyles.Add(new RowStyle(SizeType.Percent,70));evidenceLayout.RowStyles.Add(new RowStyle(SizeType.Percent,30));
        context.Dock=DockStyle.Fill;context.ReadOnly=true;context.AllowUserToAddRows=false;context.AllowUserToDeleteRows=false;context.AllowUserToResizeRows=false;
        context.AutoGenerateColumns=false;context.BackgroundColor=Color.White;context.BorderStyle=BorderStyle.None;context.RowHeadersVisible=false;
        context.SelectionMode=DataGridViewSelectionMode.FullRowSelect;context.MultiSelect=false;context.AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill;
        context.DefaultCellStyle.SelectionBackColor=TraceTheme.Selected;context.DefaultCellStyle.SelectionForeColor=Ink;
        context.AlternatingRowsDefaultCellStyle.BackColor=TraceTheme.Workspace;context.ColumnHeadersHeight=34;context.RowTemplate.Height=30;
        foreach(string column in new string[]{"Transfer","時間 (s)","Addr/EP","Request","完成欄位","資料長度"})context.Columns.Add(column,column);
        foreach(DataGridViewColumn column in context.Columns)column.SortMode=DataGridViewColumnSortMode.NotSortable;
        context.Columns[1].FillWeight=160;context.SelectionChanged+=delegate {ShowContext();};
        evidenceLayout.Controls.Add(context,0,0);evidenceLayout.Controls.Add(Padded(raw,new Padding(10)),0,1);evidence.Controls.Add(evidenceLayout);tabs.TabPages.Add(evidence);
        var limits=new TabPage("限制與來源");limits.Controls.Add(Padded(gaps,new Padding(10,14,10,8)));tabs.TabPages.Add(limits);right.Controls.Add(tabs,0,3);split.Panel2.Controls.Add(right);layout.Controls.Add(split,0,3);
        var status=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Padding=new Padding(0,10,0,0),Margin=Padding.Empty};
        status.RowStyles.Add(new RowStyle(SizeType.Absolute,5));status.RowStyles.Add(new RowStyle(SizeType.Percent,100));status.RowStyles.Add(new RowStyle(SizeType.Absolute,20));
        progress.Dock=DockStyle.Fill;progress.Visible=false;status.Controls.Add(progress,0,0);
        message.Dock=DockStyle.Fill;message.ForeColor=Muted;message.TextAlign=ContentAlignment.MiddleLeft;message.Text="正在檢查執行環境…";message.AutoEllipsis=true;
        status.Controls.Add(message,0,1);status.Controls.Add(scopeLabel,0,2);layout.Controls.Add(status,0,4);
        Section(summary,"先找值得檢查的位置","拖入一份 .usb 或 .pex Trace 後，工具會整理值得優先核對的位置。\r\nUSB 顯示最多三個候選；PCIe 先顯示流程階段與下一步，並保留次要交易觀察的原始順序。");
        Section(summary,"核對原生封包","USB 可傳送定位請求；PCIe 嘗試原生選單定位，無法核對時顯示 Ctrl+G 備援。\r\n若 LeCroy 已有工作階段，工具會顯示共存限制。");
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
    void ChooseFile() {if(busy||closing)return;using(var dialog=new OpenFileDialog()) {dialog.Filter="USB / PCIe Trace (*.usb;*.pex)|*.usb;*.pex|USB Trace (*.usb)|*.usb|PCIe Trace (*.pex)|*.pex";dialog.Multiselect=false;if(dialog.ShowDialog(this)==DialogResult.OK)Import(new string[]{dialog.FileName},"file_picker");}}
    void Send(object command) {
        try {
            if(controller.HasExited)throw new InvalidOperationException("控制程序已結束");
            // Process.StandardInput inherits the Windows console code page.
            // The private JSON-lines pipe is UTF-8, including Unicode filenames.
            byte[] payload=Encoding.UTF8.GetBytes(json.Serialize(command)+"\n");
            Stream input=controller.StandardInput.BaseStream;input.Write(payload,0,payload.Length);input.Flush();
        }
        catch(Exception ex) {message.Text="無法傳送操作："+ex.Message;}
    }
    void Import(string[] files,string method) {
        if(busy||closing) {message.Text="目前工作尚未完成，請稍後再匯入。";return;}
        if(files==null||files.Length!=1||!File.Exists(files[0])||!(String.Equals(Path.GetExtension(files[0]),".usb",StringComparison.OrdinalIgnoreCase)||String.Equals(Path.GetExtension(files[0]),".pex",StringComparison.OrdinalIgnoreCase))) {message.Text="一次只接受一份可讀取的 .usb 或 .pex 檔案；不接受資料夾或多檔。";return;}
        if(url==null||controller.HasExited) {message.Text="工具尚未就緒，請檢查執行環境。";return;}
        pendingPcie=String.Equals(Path.GetExtension(files[0]),".pex",StringComparison.OrdinalIgnoreCase);
        Send(new {action="import",path=Path.GetFullPath(files[0]),input_method=method});ResetForImport();busy=true;choose.Enabled=locate.Enabled=copy.Enabled=protocols.Enabled=nativeTargets.Enabled=false;message.Text="已接收檔案，正在開始分析…";
    }
    void ResetForImport(){
        CloseConfigUr();
        pageIndex=null;currentPage=0;previousPage.Visible=nextPage.Visible=pageLabel.Visible=false;
        shownError=null;
        model=null;caseId=reportFile=null;cards=allCards=allObservations=allFlows=new object[0];flowView.Visible=engineerContext.Visible=false;modelRevision="0";changingProtocol=true;observed.Enabled=false;observed.Checked=false;showAll.Checked=false;showAll.Visible=false;changingProtocol=false;
        candidates.Items.Clear();ClearEvidence();raw.Clear();gaps.Clear();summary.Clear();
        SetProtocolScopePlaceholder("正在分析協定範圍…","正在分析；無候選不代表協定測試通過。");nativeTargets.Items.Clear();nativeTargets.Visible=false;
        badge.Text=(pendingPcie?"PCIe":"USB / PCIe")+" TRACE\n本機分析 · 來源唯讀";badge.ForeColor=Muted;
        totals.Text="正在分析…";title.Text="正在讀取 Trace";coordinates.Text="完成後在這裡顯示候選";copy.Enabled=copyFile.Enabled=false;
        findings.Text="正在分析本次 Trace";findings.ForeColor=Ink;coverage.Text="Coverage 尚未取得；不沿用上一份 Trace 的結果";candidateStatus.Text="分析中";candidateStatus.ForeColor=Muted;
    }
    void SetProtocolScopePlaceholder(string selection,string scope) {
        protocols.Items.Clear();protocols.Items.Add(selection);protocols.SelectedIndex=0;
        scopeLabel.Text=scope;
    }
    void NavigateSelected() {
        if(busy||caseId==null||candidates.SelectedIndex<0)return;
        Send(new {action="navigate",case_id=caseId,rank=Convert.ToInt32(Map(cards[candidates.SelectedIndex])["rank"]),target_index=Math.Max(0,nativeTargets.SelectedIndex),item_kind=FlowMode?"flow":observed.Checked?"observation":"candidate"});busy=true;locate.Enabled=false;message.Text="正在定位，請稍候…";
    }
    void CloseConfigUr() {
        if(configUrView!=null)configUrView.Close();
        configUrView=null;configUrStatus=null;configUr.Visible=false;
    }
    bool ConfigUrControlsAvailable {
        get{return IsPcie&&caseId!=null&&url!=null&&!controller.HasExited&&!closing&&phase!="unresponsive"&&phase!="cleanup_unknown";}
    }
    void OpenConfigUr() {
        if(!IsPcie||caseId==null||controller.HasExited||closing)return;
        if(configUrView!=null){configUrView.Activate();return;}
        string id=caseId;
        configUrView=new ConfigUrForm(Path.Combine(directory,id),id,model,
            delegate {if(caseId==id&&ConfigUrControlsAvailable&&!busy)Send(new {action="config_ur_run",case_id=id});},
            delegate {if(caseId==id&&ConfigUrControlsAvailable&&busy&&phase=="config_ur")Send(new {action="cancel"});},
            delegate(string row,string target) {
                if(caseId==id&&ConfigUrControlsAvailable&&!busy)
                    Send(new {action="config_ur_navigate",case_id=id,row_id=row,target=target});
            });
        configUrView.FormClosed+=delegate {configUrView=null;};
        configUrView.ApplyStatus(configUrStatus,busy,ConfigUrControlsAvailable,phase=="config_ur");
        configUrView.Show(this);
    }
    void ExportReport() {
        if(reportFile==null||!File.Exists(reportFile))return;
        using(var save=new SaveFileDialog()) {save.Filter=IsPcie?"HTML report (*.html)|*.html|Markdown report (*.md)|*.md":"HTML report (*.html)|*.html";save.FileName=IsPcie?"pcie-trace-report":"usb-trace-report.html";
            if(save.ShowDialog(this)==DialogResult.OK) {try {
                string extension=Path.GetExtension(save.FileName).ToLowerInvariant();if(extension!=".html"&&!(IsPcie&&extension==".md"))throw new InvalidOperationException("請使用報告對應的 .html 或 .md 副檔名。");
                bool attachments=TraceReportExport.Copy(extension==".md"?Path.ChangeExtension(reportFile,".md"):reportFile,save.FileName,model);message.Text="已匯出離線報告"+(attachments?"及證據附件資料夾（分享時請一併提供）":"")+"："+save.FileName;
            }catch(Exception ex){MessageBox.Show(this,"匯出失敗："+ex.Message,"匯出 HTML");}}}
    }
    void DrawCandidate(object sender,DrawItemEventArgs e) {
        if(e.Index<0||e.Index>=cards.Length)return;var c=Map(cards[e.Index]);bool selected=(e.State&DrawItemState.Selected)!=0;
        using(var brush=new SolidBrush(selected?TraceTheme.Selected:Color.White))e.Graphics.FillRectangle(brush,e.Bounds);
        using(var brush=new SolidBrush(selected?Accent:FlowMode?TraceTheme.Neutral:TraceTheme.Candidate(observed.Checked)))e.Graphics.FillRectangle(brush,new Rectangle(e.Bounds.Left,e.Bounds.Top,4,e.Bounds.Height));
        var box=new Rectangle(e.Bounds.Left+14,e.Bounds.Top+6,e.Bounds.Width-26,20);
        TextRenderer.DrawText(e.Graphics,(FlowMode?TracePresentation.FlowLabel(c)+" · ":observed.Checked?"一般流程 · ":"交易覆核 · ")+(c.ContainsKey("protocol_rank")?S(c,"protocol_rank"):S(c,"rank")),Font,box,FlowMode?Muted:TraceTheme.Candidate(observed.Checked),TextFormatFlags.EndEllipsis);
        box.Y+=23;TextRenderer.DrawText(e.Graphics,TargetLabel(Primary(c)),metaFont,box,selected?Accent:Ink,TextFormatFlags.EndEllipsis);
        box.Y+=23;box.Height=42;TextRenderer.DrawText(e.Graphics,TracePresentation.Headline(c),cardFont,box,Ink,TextFormatFlags.WordBreak|TextFormatFlags.EndEllipsis);
        box.Y+=43;box.Height=20;TextRenderer.DrawText(e.Graphics,CardTime(c),Font,box,Muted,TextFormatFlags.EndEllipsis);
        using(var pen=new Pen(Line))e.Graphics.DrawLine(pen,e.Bounds.Left+12,e.Bounds.Bottom-1,e.Bounds.Right-12,e.Bounds.Bottom-1);e.DrawFocusRectangle();
    }
    void LoadModel(string id) {
        Guid parsed;if(!Guid.TryParseExact(id,"N",out parsed))throw new InvalidDataException("Invalid case identity");
        if(caseId!=id)CloseConfigUr();
        caseId=id;currentPage=0;pageIndex=null;
        string indexPath=Path.Combine(directory,id,"ui-index.json");
        if(File.Exists(indexPath)){
            pageIndex=ReadBounded(indexPath);
            if(S(pageIndex,"schema")!="pcie.desktop-pages/v1"||S(pageIndex,"analysis_id")!=id)throw new InvalidDataException("PCIe 分頁來源不符");
            LoadPage(0,"flow_items");
        }else model=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(directory,id,"inspection.json"),Encoding.UTF8));
        caseId=id;reportFile=Path.Combine(directory,id,"report.html");allCards=Items(model,"candidates");allObservations=Items(model,"observations");
        allFlows=Items(model,"flow_items");flowView.Visible=FlowReady;engineerContext.Visible=FlowReady;
        changingProtocol=true;flowView.SelectedIndex=0;changingProtocol=false;
        ((TableLayoutPanel)flowView.Parent.Parent).RowStyles[2].Height=pageIndex!=null?100:FlowReady?64:30;
        changingProtocol=true;showAll.Checked=false;changingProtocol=false;showAll.Visible=IsPcie&&allCards.Length>3;observed.Visible=!IsPcie;
        protocols.Items.Clear();var analyses=Items(model,"analyses");
        if(analyses.Length==0)protocols.Items.Add("USB2 · 已分析 EP0");
        else foreach(object item in analyses){var a=Map(item);protocols.Items.Add(S(a,"protocol")+" · "+StateText(S(a,"state"))+" · "+S(a,"episode_count")+" 個區段");}
        int first=PreferredAnalysis(analyses);
        protocols.SelectedIndex=first;scopeLabel.Text=S(model,"scope");
        try{File.WriteAllText(Path.Combine(directory,id,"ui-loaded.json"),json.Serialize(new Dictionary<string,object>{{"at_utc",DateTime.UtcNow.ToString("o")},{"paged",pageIndex!=null},{"case_id",id}}),Encoding.UTF8);}catch{}
    }
    Dictionary<string,object> ReadBounded(string path){
        using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
            if(stream.Length>1024*1024)throw new InvalidDataException("UI 分頁超過安全上限；完整資料保留於工作資料夾。");
            using(var reader=new StreamReader(stream,Encoding.UTF8))return json.Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
        }
    }
    void ChangePage(int number){
        try{if(pageIndex!=null)LoadPage(number);PopulateProtocol();}
        catch(Exception ex){ClearEvidence();candidates.Items.Clear();cards=new object[0];locate.Enabled=copy.Enabled=false;message.Text="分頁讀取失敗："+ex.Message+" 請查看工作資料夾的完整報告。";}
    }
    void LoadPage(int number,string group=null){
        if(pageIndex==null)return;
        group=group??(FlowMode?"flow_items":"candidates");
        var pages=Items(Map(Map(pageIndex["groups"])[group]),"pages");
        if(number<0||number>=pages.Length)return;
        string relative=Convert.ToString(pages[number]);
        if(!System.Text.RegularExpressions.Regex.IsMatch(relative,@"^ui-[0-9a-f]{32}/(flow_items|candidates|observations)-[0-9]+\.json$"))throw new InvalidDataException("無效的 UI 分頁路徑");
        var loaded=ReadBounded(Path.Combine(directory,caseId,relative.Replace('/',Path.DirectorySeparatorChar)));
        if(S(loaded,"analysis_id")!=caseId||S(Map(loaded["ui_page"]),"group")!=group)throw new InvalidDataException("UI 分頁工作身分不符");
        model=loaded;currentPage=number;allCards=Items(model,"candidates");allFlows=Items(model,"flow_items");allObservations=Items(model,"observations");
    }
    int PageTotal(string name,int fallback){
        return pageIndex==null?fallback:Convert.ToInt32(Map(Map(pageIndex["groups"])[name])["total"]);
    }
    public static int PreferredAnalysis(object[] analyses){
        int first=0;bool picked=false;
        for(int n=0;n<analyses.Length;n++)if(Convert.ToInt32(Map(analyses[n])["episode_count"])>0){first=n;picked=true;break;}
        if(!picked)foreach(string preferred in new string[]{"failed","partial"}){
            for(int n=0;n<analyses.Length;n++)if(S(Map(analyses[n]),"state")==preferred){first=n;picked=true;break;}
            if(picked)break;
        }
        if(!picked)for(int n=0;n<analyses.Length;n++)if(Map(analyses[n]).ContainsKey("observation_count")&&Convert.ToInt32(Map(analyses[n])["observation_count"])>0){first=n;picked=true;break;}
        if(!picked)for(int n=0;n<analyses.Length;n++)if(S(Map(analyses[n]),"state")=="analyzed"){first=n;break;}
        return first;
    }
    static string StateText(string state){switch(state){case "analyzed":return "已分析";case "not_observed":return "未觀察到";case "partial":return "資料部分缺漏";case "failed":return "執行失敗";default:return "尚未支援";}}
    static Dictionary<string,object> Primary(Dictionary<string,object> c){var ts=Items(c,"native_targets");return ts.Length>0?Map(ts[0]):new Dictionary<string,object>{{"protocol","USB2"},{"level",3},{"index",Items(c,"transfer_indices")[0]}};}
    static string TargetLabel(Dictionary<string,object> t){int level=Convert.ToInt32(t["level"]);return (level==0?"Packet":level==1?"Transaction":"Transfer")+" "+S(t,"index");}
    void SelectProtocol(){
        if(model==null||protocols.SelectedIndex<0)return;
        var analyses=Items(model,"analyses");string protocol=analyses.Length>0?S(Map(analyses[protocols.SelectedIndex]),"protocol"):"USB2";
        int nc=0,nf=0;foreach(object c in allCards)if(analyses.Length==0||S(Map(c),"protocol")==protocol)nc++;foreach(object c in allObservations)if(S(Map(c),"protocol")==protocol)nf++;
        changingProtocol=true;observed.Enabled=nf>0&&!busy;observed.Checked=!FlowReady&&nf>0&&nc==0;changingProtocol=false;
        PopulateProtocol();
    }
    void PopulateProtocol(){
        if(model==null||protocols.SelectedIndex<0)return;
        nextCheck.Visible=false;
        var analyses=Items(model,"analyses");Dictionary<string,object> a=analyses.Length>0?Map(analyses[protocols.SelectedIndex]):null;
        string protocol=a!=null?S(a,"protocol"):"USB2";
        tabs.SelectedIndex=0;
        var selected=new List<object>();foreach(object c in FlowMode?allFlows:observed.Checked?allObservations:allCards)if(a==null||S(Map(c),"protocol")==protocol)selected.Add(c);
        if(FlowMode&&!showAll.Checked){var visible=new HashSet<string>();foreach(object id in Items(Map(model["flow_analysis"]),"displayed_scenarios"))visible.Add(Convert.ToString(id));selected.RemoveAll(c=>!visible.Contains(S(Map(c),"scenario_id")));}
        cards=selected.ToArray();
        if(IsPcie&&!FlowMode&&!showAll.Checked&&cards.Length>3)cards=selected.GetRange(0,3).ToArray();
        showAll.Visible=FlowMode?PageTotal("flow_items",allFlows.Length)>cards.Length||showAll.Checked:IsPcie&&PageTotal("candidates",allCards.Length)>3;showAll.Text=FlowMode?"包含較早流程":"顯示全部候選";
        bool paged=pageIndex!=null&&showAll.Checked;
        previousPage.Visible=nextPage.Visible=pageLabel.Visible=paged;
        if(paged){int pageCount=Items(Map(Map(pageIndex["groups"])[FlowMode?"flow_items":"candidates"]),"pages").Length;
            previousPage.Enabled=!busy&&currentPage>0;nextPage.Enabled=!busy&&currentPage+1<pageCount;pageLabel.Text=(currentPage+1)+" / "+pageCount+" 頁";}
        candidates.Items.Clear();foreach(object c in cards)candidates.Items.Add((FlowMode?TracePresentation.FlowLabel(Map(c))+" · ":observed.Checked?"一般流程 · ":"交易覆核 · ")+TargetLabel(Primary(Map(c)))+(FlowMode?" · "+S(Map(Map(c)["locator"]),"direction"):"")+" · "+TracePresentation.Headline(Map(c)));
        string total=a!=null?S(a,"episode_count"):S(model,"episode_count");
        totals.Text=observed.Checked?"可疑候選 "+total+"；流程 "+cards.Length+" / "+S(a,"observation_count")+"\n中性證據，未列入可疑候選":"優先檢查 "+cards.Length+" / "+total+" 個區段\n"+(a!=null?StateText(S(a,"state")):"已分析 USB2 EP0");
        if(IsPcie)totals.Text="候選 "+cards.Length+" / "+total+" 個區段\n依擷取順序（未做優先排名）";
        if(FlowMode)totals.Text="連線觀察／待確認 "+cards.Length+" / "+PageTotal("flow_items",allFlows.Length)+" 個區間\n非故障排名 · 另有 "+PageTotal("candidates",allCards.Length)+" 筆次要交易觀察";
        badge.Text=protocol+"\n本機分析 · 來源唯讀";
        badge.ForeColor=Muted;coverage.Text=TracePresentation.Coverage(a);tips.SetToolTip(coverage,coverage.Text);
        int count=a==null?allCards.Length:Convert.ToInt32(a["episode_count"]);
        findings.Text=count>0?"本次分析發現 · "+protocol+" · "+count+" 個值得覆核的候選":"本次分析發現 · "+protocol+" · 本範圍未找到足夠候選";
        findings.ForeColor=count>0?TraceTheme.Review:Ink;
        var stage=StagePresentation();if(stage!=null){findings.Text=S(stage,"headline")+" · 候選 "+count;findings.ForeColor=Ink;tips.SetToolTip(findings,S(stage,"claim_boundary"));}
        if(FlowReady){var fp=Map(Map(model["flow_analysis"])["presentation"]);findings.Text=model.ContainsKey("engineer_view")?S(Map(model["engineer_view"]),"headline"):S(fp,"headline");findings.ForeColor=Ink;tips.SetToolTip(findings,"流程核對入口，尚未判定故障或初始化成功。");}
        if(a!=null&&S(a,"state")!="analyzed"){findings.Text="本次分析 · "+protocol+" · "+StateText(S(a,"state"));findings.ForeColor=Muted;}
        if(a!=null&&IsPcie){object cv;if(a.TryGetValue("coverage",out cv)&&cv is Dictionary<string,object>){var facts=Map(cv);if(facts.ContainsKey("subscription_complete")&&Equals(facts["subscription_complete"],true)&&S(a,"state")=="analyzed"){badge.Text="PCIe\nTLP 訂閱擷取完成";badge.ForeColor=TraceTheme.Verified;}}}
        if(cards.Length>0)candidates.SelectedIndex=0;
        else {candidateStatus.Text="分析範圍內無候選 · 非測試 PASS";candidateStatus.ForeColor=Muted;title.Text=a!=null&&S(a,"state")!="analyzed"?StateText(S(a,"state"))+" "+protocol:"本次未找到足夠可疑的區段";coordinates.Text=a!=null?S(a,"scope"):"分析範圍：USB2 標準 EP0";summary.Clear();nativeTargets.Items.Clear();nativeTargets.Visible=false;copy.Enabled=false;
            AppendStageSummary();Section(summary,"目前結果","本次分析範圍內未找到足夠可疑的區段。\r\n"+(IsPcie?"這不代表整份 PCIe Trace 正常或測試通過。":"這不代表整份 USB Trace 或 USB-CV 測試通過。"));
            if(a!=null)Section(summary,"資料與範圍",StateText(S(a,"state"))+"\r\n"+Bullets(Items(a,"limitations")));
            Section(summary,"下一步","核對測試 log、協定選單與本次分析範圍；未觀察到／部分缺漏不能當成正常。");summary.SelectionStart=0;summary.ScrollToCaret();ClearEvidence();ShowLimits(null);}
        if(FlowMode&&cards.Length==0){var p=model.ContainsKey("engineer_view")?Map(model["engineer_view"]):Map(Map(model["flow_analysis"])["presentation"]);title.Text=S(p,"headline");candidateStatus.Text="資料不足 · 未判定故障";summary.Clear();Brief(summary,"觀察到什麼",S(p,"observed"));if(p.ContainsKey("uncertain"))Brief(summary,"仍待確認",S(p,"uncertain"));Brief(summary,"下一步核對",S(p,"next_check"));}
    }
    void UpdateCoordinates(){int i=candidates.SelectedIndex;if(i<0||i>=cards.Length)return;var c=Map(cards[i]);var ts=Items(c,"native_targets");var t=ts.Length>0?Map(ts[Math.Max(0,nativeTargets.SelectedIndex)]):Primary(c);
        if(FlowMode){var locs=Items(c,"navigation_locators");if(locs.Length>1&&nativeTargets.SelectedIndex>0){var l=Map(locs[nativeTargets.SelectedIndex]);coordinates.Text=TargetLabel(t)+" · "+S(l,"direction")+" · "+(t["timestamp_ns"]!=null?Seconds(t["timestamp_ns"]):S(l,"time_display")+"（原始精度）");}else coordinates.Text=S(c,"time_display");return;}
        if(IsPcie){coordinates.Text="PCIe · "+TargetLabel(t)+" · "+CardTime(c)+" · "+S(Map(c["locator"]),"direction");return;}
        coordinates.Text=S(t,"protocol")+" · "+TargetLabel(t)+"   ·   "+Seconds(t.ContainsKey("timestamp_ns")&&t["timestamp_ns"]!=null?t["timestamp_ns"]:c["start_ns"])+(S(t,"protocol")=="USB2"?"   ·   Address "+S(c,"address")+" / EP "+S(c,"endpoint"):"   ·   channel "+S(t,"channel"));}
    void ShowCandidate() {
        int i=candidates.SelectedIndex;if(i<0||i>=cards.Length)return;var c=Map(cards[i]);title.Text=TracePresentation.Headline(c);tips.SetToolTip(title,S(c,"title"));
        candidateStatus.Text=observed.Checked?"一般流程 · 未列為故障候選":"待覆核 · 尚未確認故障";candidateStatus.ForeColor=TraceTheme.Candidate(observed.Checked);
        if(FlowMode){candidateStatus.Text=S(c,"output_class")=="EVIDENCE_GAP"?"資料不足 · 尚未判定":"階段核對 · 里程碑不是故障位置";candidateStatus.ForeColor=Muted;}
        nativeTargets.Items.Clear();foreach(object t in Items(c,"native_targets"))nativeTargets.Items.Add(TargetLabel(Map(t)));nativeTargets.Visible=nativeTargets.Items.Count>1;if(nativeTargets.Items.Count>0)nativeTargets.SelectedIndex=0;UpdateCoordinates();
        summary.Clear();var facts=Items(c,"facts");var reasons=Items(c,"reasons");
        if(!FlowReady)AppendStageSummary();
        bool plain=FlowMode&&c.ContainsKey("engineer_view");
        if(plain){var v=Map(c["engineer_view"]);title.Text=S(v,"headline");Brief(summary,"觀察到什麼",S(v,"observed"));Brief(summary,"仍待確認",S(v,"uncertain"));Brief(summary,"下一步核對",S(v,"next_check"));Brief(summary,"這個位置代表什麼",S(v,"meaning"));}
        else {
        Brief(summary,"觀察到什麼",FlowMode?Bullets(facts):facts.Length>0?Convert.ToString(facts[0]):"觀察摘要未提供，請核對原始證據。");
        Brief(summary,observed.Checked?"流程說明（非候選）":"為什麼值得看",reasons.Length>0?Convert.ToString(reasons[0]):"列出理由未提供，請先核對證據。");
        Brief(summary,"下一步核對",S(c,"next_step"));summary.SelectionStart=0;summary.ScrollToCaret();
        if(!IsPcie&&Items(c,"next_actions").Length>0){var action=Map(Items(c,"next_actions")[0]);Brief(summary,"工程知識 · 尚未判定合規",S(action,"text"));summary.SelectionStart=0;summary.ScrollToCaret();}
        if(FlowMode){var fp=Map(Map(model["flow_analysis"])["presentation"]);Brief(summary,"工程情境",S(fp,"context"));}
        }
        summary.SelectionStart=0;summary.ScrollToCaret();ClearEvidence();
        nextCheck.Visible=plain;nextCheck.Enabled=plain&&!busy;if(plain)nextCheck.Text=S(Map(Map(c["engineer_view"])["action"]),"label");
        tabs.TabPages[2].Text=IsPcie?"進階證據":"限制與來源";
        bool usb2=S(Primary(c),"protocol")=="USB2";string[] headers=usb2?new string[]{"Transfer","時間 (s)","Addr/EP","Request","完成欄位","資料長度"}:new string[]{"原生單位","時間 (s)","Channel / SOP","事件 / 訊息","結果 / 角色","詳細資料"};for(int h=0;h<6;h++)context.Columns[h].HeaderText=headers[h];
        object[] evidenceRows=Items(c,"context");timelineNote.Text=TracePresentation.TimelineNote(evidenceRows);overviewLayout.RowStyles[1].Height=evidenceRows.Length>0?36:0;toggleEvidence.Visible=evidenceRows.Length>0;toggleEvidence.Text="展開關聯事件（"+evidenceRows.Length+"）";
        foreach(object item in evidenceRows) {var row=Map(item);timeline.Items.Add(TracePresentation.EvidenceKey(row,S(Primary(c),"protocol"))+" · "+TracePresentation.EvidenceTime(row));
            int n=context.Rows.Add(S(row,"index"),row.ContainsKey("timestamp_ns")&&row["timestamp_ns"]!=null?Seconds(row["timestamp_ns"]).Replace(" s",""):IsPcie?S(row,"time_display"):"未知",usb2?S(row,"address")+"/"+S(row,"endpoint"):S(row,"channel"),usb2?S(row,"request"):S(row,"message"),usb2?S(row,"completed"):S(row,"result"),usb2?S(row,"data_length"):S(row,"detail"));context.Rows[n].Tag=row;}
        context.ClearSelection();
        foreach(DataGridViewRow row in context.Rows) {
            if(Convert.ToString(row.Cells[0].Value)==S(Primary(c),"index")||Convert.ToString(row.Cells[0].Value)==TargetLabel(Primary(c))) {
                row.DefaultCellStyle.Font=metaFont;context.CurrentCell=row.Cells[0];row.Selected=true;break;
            }
        }
        ShowLimits(c);copy.Enabled=true;locate.Enabled=!busy&&phase!="unresponsive"&&phase!="cleanup_unknown";ShowContext();
    }
    void ShowNextCheck(){
        if(busy||OperationError||candidates.SelectedIndex<0)return;var c=Map(cards[candidates.SelectedIndex]);if(!c.ContainsKey("engineer_view"))return;
        var v=Map(c["engineer_view"]);if(S(Map(v["action"]),"kind")=="NAVIGATE"&&nativeTargets.Items.Count>1){nativeTargets.SelectedIndex=1;NavigateSelected();return;}
        tabs.SelectedIndex=1;raw.Clear();Section(raw,"下一步需要補充的資料",Bullets(Items(v,"missing_evidence")));Section(raw,"從哪裡開始",S(v,"next_check"));Section(raw,"判讀限制",S(v,"completion_note"));raw.SelectionStart=0;raw.ScrollToCaret();
        var layout=raw.Parent.Parent as TableLayoutPanel;if(layout!=null){layout.RowStyles[0].Height=25;layout.RowStyles[1].Height=75;}
    }
    void ShowLimits(Dictionary<string,object> c) {
        gaps.Clear();if(c!=null){Section(gaps,"完整觀察事實",Bullets(Items(c,"facts")));Section(gaps,"列出理由（不是根因判定）",Bullets(Items(c,"reasons")));Section(gaps,"這個區段的證據缺口",Bullets(Items(c,"evidence_gaps")));}
        if(c!=null&&c.ContainsKey("provenance_details"))Section(gaps,"知識卡完整條件、來源與限制（不是本次缺口清單）",Bullets(Items(c,"provenance_details")));
        if(c!=null&&Items(c,"knowledge_notes").Length>0)Section(gaps,"工程知識與來源（非合規判定）",Bullets(Items(c,"knowledge_notes")));
        if(IsPcie&&model.ContainsKey("native_details"))Section(gaps,"候選與最後階段附近的原生明細（僅匯出列）",json.Serialize(model["native_details"]));
        var analyses=Items(model,"analyses");if(analyses.Length>0&&protocols.SelectedIndex>=0){var a=Map(analyses[protocols.SelectedIndex]);Section(gaps,"本協定資料狀態",StateText(S(a,"state"))+"\r\n"+S(a,"scope")+"\r\n"+Bullets(Items(a,"limitations")));Section(gaps,"擷取範圍",json.Serialize(a["coverage"]));}
        Section(gaps,"本次分析限制",Bullets(Items(model,"limitations")));Section(gaps,"來源識別","規則："+S(model,"rule_version")+"\r\nSHA-256："+S(model,"trace_sha256")+"\r\nTransfer 與 Packet 編號不同；API 成功仍須核對 LeCroy 畫面。");gaps.SelectionStart=0;gaps.ScrollToCaret();
        if(IsPcie)Section(gaps,"PCIe 副本與編號","Display SHA-256："+S(model,"display_trace_sha256")+"\r\n"+S(model,"display_trace_path")+"\r\n"+S(model,"packet_namespace")+"\r\n先嘗試原生選單定位並讀回主視圖起點；無法核對時提供 Ctrl+G 備援。");
        if(StagePresentation()!=null){var stage=Map(model["stage_summary"]);Section(gaps,"階段證據與限制",Bullets(Items(stage,"coverage_and_limitations")));Section(gaps,"來源事件鏈（Packet 與方向 epoch）",json.Serialize(stage["observed_milestones"]));if(model.ContainsKey("transaction_crosscheck"))Section(gaps,"原生交易核對（不是根因判定）",json.Serialize(model["transaction_crosscheck"]));}
        if(FlowReady){var f=Map(model["flow_analysis"]);var p=Map(f["presentation"]);Section(gaps,"Flow 情境與 Completion",S(p,"context")+"\r\n"+S(p,"completion_summary"));if(c!=null&&c.ContainsKey("scenario_id")){foreach(object item in Items(f,"scenarios")){var e=Map(item);if(S(e,"scenario_id")!=S(c,"scenario_id"))continue;Section(gaps,"本階段知識來源與適用範圍",json.Serialize(e["applicable_cards"]));Section(gaps,"本階段觀察與情境分類",json.Serialize(e["observations"]));}}Section(gaps,"完整 Flow 證據","請開啟工作資料夾中的 flow-analysis.json；包含全部階段、Completion 狀態、來源參照及未評估項目。知識卡 SHA-256："+S(f,"knowledge_pack_sha256"));}
    }
    void EditContext(){
        if(!FlowReady||busy)return;
        using(var dialog=new Form {Text="本次 Trace 的工程情境",Size=new Size(650,430),MinimumSize=new Size(570,410),StartPosition=FormStartPosition.CenterParent,Font=Font,BackColor=Surface}){
            var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=8,Padding=new Padding(16)};
            foreach(int h in new int[]{26,32,26,72,26,32,46,46})layout.RowStyles.Add(new RowStyle(SizeType.Absolute,h));dialog.Controls.Add(layout);
            layout.Controls.Add(new Label {Text="可選輸入；只影響本次 Trace 的解釋，不改寫觀察",Dock=DockStyle.Fill},0,0);
            var kind=new ComboBox {Dock=DockStyle.Fill,DropDownStyle=ComboBoxStyle.DropDownList};kind.Items.AddRange(new object[]{"未提供／清除情境","預期 Hot Plug 裝置切換","指定區間不預期 Link Down"});kind.SelectedIndex=0;layout.Controls.Add(kind,0,1);
            layout.Controls.Add(new Label {Text="測試操作或期待",Dock=DockStyle.Fill},0,2);
            var description=new TextBox {Dock=DockStyle.Fill,Multiline=true,MaxLength=1200,AccessibleName="工程情境說明"};layout.Controls.Add(description,0,3);
            layout.Controls.Add(new Label {Text="來源（工程師回覆／測試文件）",Dock=DockStyle.Fill},0,4);
            var source=new TextBox {Dock=DockStyle.Fill,MaxLength=1200,AccessibleName="工程情境來源"};layout.Controls.Add(source,0,5);
            var scoped=new CheckBox {Text="只套用目前選取流程的方向、epoch 與 Packet 區間\n未勾選時僅作背景，不將斷線標為預期。",Dock=DockStyle.Fill,Enabled=false};layout.Controls.Add(scoped,0,6);
            Dictionary<string,object> scope=null;
            if(FlowMode&&candidates.SelectedIndex>=0){string scenario=S(Map(cards[candidates.SelectedIndex]),"scenario_id");foreach(object entry in Items(Map(model["flow_analysis"]),"scenarios")){var e=Map(entry);if(S(e,"scenario_id")!=scenario)continue;var ls=Map(e["link_scope"]);if(ls["channel"]!=null&&ls["epoch"]!=null&&(S(ls,"direction")=="Upstream"||S(ls,"direction")=="Downstream")){scope=new Dictionary<string,object>{{"channel",ls["channel"]},{"direction",ls["direction"]},{"epoch",ls["epoch"]},{"start_packet",e["start_packet"]},{"end_packet",e["end_packet"]}};scoped.Enabled=true;tips.SetToolTip(scoped,json.Serialize(scope));}}}
            object previous;var flow=Map(model["flow_analysis"]);if(flow.TryGetValue("expected_context",out previous)&&previous is Dictionary<string,object>){var c=Map(previous);kind.SelectedIndex=S(c,"kind")=="EXPECTED_HOTPLUG"?1:2;description.Text=S(c,"description");source.Text=S(c,"source");if(c["scope"] is Dictionary<string,object>){scope=Map(c["scope"]);scoped.Enabled=true;scoped.Checked=true;scoped.Text="保留已綁定區間："+S(scope,"direction")+" · epoch "+S(scope,"epoch")+" · Packet "+S(scope,"start_packet")+"–"+S(scope,"end_packet")+"\n取消勾選則改為背景情境。";tips.SetToolTip(scoped,json.Serialize(scope));}}
            var buttons=new FlowLayoutPanel {Dock=DockStyle.Fill,FlowDirection=FlowDirection.RightToLeft};var save=new Button {Text="套用",AutoSize=true};var cancelContext=new Button {Text="取消",DialogResult=DialogResult.Cancel,AutoSize=true};buttons.Controls.AddRange(new Control[]{save,cancelContext});layout.Controls.Add(buttons,0,7);dialog.CancelButton=cancelContext;
            save.Click+=delegate {
                if(kind.SelectedIndex>0&&(description.Text.Trim().Length==0||source.Text.Trim().Length==0)){MessageBox.Show(dialog,"請填寫操作說明與來源。","工程情境");return;}
                Dictionary<string,object> value=null;
                if(kind.SelectedIndex>0)value=new Dictionary<string,object>{{"kind",kind.SelectedIndex==1?"EXPECTED_HOTPLUG":"UNEXPECTED_LINK_DOWN"},{"description",description.Text.Trim()},{"source",source.Text.Trim()},{"scope",scoped.Checked?scope:null},{"source_trace_sha256",model["source_trace_sha256"]},{"display_trace_sha256",model["display_trace_sha256"]},{"packet_namespace",model["packet_namespace"]}};
                Send(new {action="context",case_id=caseId,context=value});dialog.DialogResult=DialogResult.OK;dialog.Close();
            };
            dialog.ShowDialog(this);
        }
    }
    Dictionary<string,object> StagePresentation(){
        object value;if(!IsPcie||model==null||!model.TryGetValue("stage_summary",out value)||!(value is Dictionary<string,object>))return null;
        var stage=Map(value);if(!stage.TryGetValue("presentation",out value)||!(value is Dictionary<string,object>))return null;return Map(value);
    }
    void AppendStageSummary(){var stage=StagePresentation();if(stage==null)return;Brief(summary,S(stage,"headline"),S(stage,"last_observation"));Brief(summary,"下一個待核對步驟",S(stage,"next_check"));Brief(summary,"判讀範圍",S(stage,"claim_boundary"));}
    void ShowContext() {
        raw.Clear();if(context.SelectedRows.Count==0)return;var row=context.SelectedRows[0].Tag as Dictionary<string,object>;if(row==null)return;
        var layout=raw.Parent.Parent as TableLayoutPanel;if(layout!=null){layout.RowStyles[0].Height=70;layout.RowStyles[1].Height=30;}
        if(!syncingEvidence){syncingEvidence=true;timeline.SelectedIndex=context.SelectedRows[0].Index;syncingEvidence=false;}
        inspectEvidence.Enabled=true;timeline.Invalidate();
        if(candidates.SelectedIndex>=0)inspectEvidence.Text="查看 "+TracePresentation.EvidenceUnit(row,S(Primary(Map(cards[candidates.SelectedIndex])),"protocol"))+" 的完整證據";
        if(IsPcie){raw.Text="Packet "+S(row,"index")+" · "+S(row,"time_display")+"\r\n"+S(row,"message")+"\r\n"+S(row,"result")+"\r\n"+S(row,"detail")+"\r\n完整來源與原始欄位保留於進階證據與匯出報告。";return;}
        if(candidates.SelectedIndex>=0&&S(Primary(Map(cards[candidates.SelectedIndex])),"protocol")!="USB2"){raw.Text=json.Serialize(row);return;}
        raw.Text="Transfer "+S(row,"index")+" · native Completed="+S(row,"completed")+" · Error="+S(row,"error")+"\r\nSETUP/payload prefix: "+S(row,"native_prefix_hex")+"\r\nData prefix: "+S(row,"data_prefix_hex")+"\r\n子封包對應尚未核實；以上欄位不能單獨當成根因判定。";
    }
    void ClearEvidence(){syncingEvidence=true;context.Rows.Clear();timeline.Items.Clear();raw.Clear();inspectEvidence.Enabled=false;timelineNote.Text="尚無關聯證據";overviewLayout.RowStyles[1].Height=overviewLayout.RowStyles[2].Height=0;toggleEvidence.Visible=false;overviewLayout.GetControlFromPosition(0,2).Visible=false;syncingEvidence=false;}
    void SelectEvidence(){
        if(syncingEvidence||timeline.SelectedIndex<0||timeline.SelectedIndex>=context.Rows.Count)return;
        syncingEvidence=true;context.ClearSelection();context.CurrentCell=context.Rows[timeline.SelectedIndex].Cells[0];context.Rows[timeline.SelectedIndex].Selected=true;syncingEvidence=false;ShowContext();
    }
    void DrawEvidence(object sender,DrawItemEventArgs e){
        if(e.Index<0||e.Index>=context.Rows.Count||candidates.SelectedIndex<0)return;
        var row=context.Rows[e.Index].Tag as Dictionary<string,object>;if(row==null)return;var c=Map(cards[candidates.SelectedIndex]);
        bool selected=(e.State&DrawItemState.Selected)!=0;string protocol=S(Primary(c),"protocol");
        bool anchor=TracePresentation.EvidenceUnit(row,protocol)==TargetLabel(Primary(c));
        using(var brush=new SolidBrush(selected?TraceTheme.Selected:Color.White))e.Graphics.FillRectangle(brush,e.Bounds);
        string text=(anchor?(observed.Checked?"[流程位置] ":"[候選位置] "):"[關聯證據] ")+TracePresentation.EvidenceUnit(row,protocol)+" · "+TracePresentation.EvidenceTime(row)+" · "+S(row,"channel");
        TextRenderer.DrawText(e.Graphics,text,Font,new Rectangle(e.Bounds.Left+6,e.Bounds.Top+4,e.Bounds.Width-12,e.Bounds.Height-6),selected?Accent:anchor?TraceTheme.Candidate(observed.Checked):TraceTheme.Related,TextFormatFlags.EndEllipsis|TextFormatFlags.VerticalCenter);
        e.DrawFocusRectangle();
    }
    bool OperationError {get{return phase=="error"||phase=="partial"||phase=="unresponsive"||phase=="cleanup_unknown";}}
    bool CanRetryNavigation() {return phase=="error"&&!busy&&!closing&&model!=null&&caseId!=null&&candidates.SelectedIndex>=0;}
    void ShowRecovery() {
        bool retry=CanRetryNavigation();
        string guidance=message.Text+"\n\n先查看工作資料夾的 analysis.log、operations.jsonl 與定位日誌。\n若已有 LeCroy 工作階段，先儲存既有工作，再安排獨立分析。\n若原生呼叫無回應或清理狀態未知，請先確認 LeCroy 狀態；工具不會強制關閉其他工作。\n可先複製定位資訊供人工核對。";
        if(retry)guidance+="\n\n關閉原生對話框或排除原因後，可按「重試」定位目前選取的項目。";
        var choice=MessageBox.Show(this,guidance,"錯誤與恢復方式",retry?MessageBoxButtons.RetryCancel:MessageBoxButtons.OK,MessageBoxIcon.Error,retry?MessageBoxDefaultButton.Button2:MessageBoxDefaultButton.Button1);
        if(choice==DialogResult.Retry&&CanRetryNavigation())NavigateSelected();
    }
    void RefreshStatus() {
        try {
            string status=Path.Combine(directory,"status.json");
            if(File.Exists(status)) {
                var value=json.Deserialize<Dictionary<string,object>>(File.ReadAllText(status,Encoding.UTF8));
                busy=(bool)value["busy"];message.Text=S(value,"message");phase=S(value,"phase");
                if(busy&&(DateTime.UtcNow-File.GetLastWriteTimeUtc(status)).TotalSeconds>90)
                    message.Text+=" · 狀態記錄超過 90 秒未更新；請檢查工作日誌，尚未確認取消或清理。";
                message.ForeColor=OperationError?TraceTheme.Error:Muted;
                if(OperationError&&model==null&&shownError!=message.Text) {
                    shownError=message.Text;title.Text="未能完成 Trace 分析";coordinates.Text="請先查看錯誤與恢復方式";
                    findings.Text="本次分析未完成";findings.ForeColor=TraceTheme.Error;coverage.Text="Coverage 尚無可用結果；不能判定 Trace 是否正常";candidateStatus.Text="操作錯誤 · 非協定故障判定";candidateStatus.ForeColor=TraceTheme.Error;
                    SetProtocolScopePlaceholder("分析未完成","協定範圍未確認。");
                    totals.Text="分析未完成\n尚無可用候選";summary.Clear();
                    Section(summary,"發生什麼事",message.Text);
                    Section(summary,"下一步","按「查看錯誤與恢復方式」，或開啟工作資料夾檢查完整日誌。修復後再匯入 Trace。");
                }
                if(!OperationError)shownError=null;
                if((phase=="preparing"||phase=="extracting")&&(model!=null||title.Text!="正在讀取 Trace")) {
                    ResetForImport();
                }
                if(phase=="cancelled"&&model==null&&title.Text!="分析已取消"){
                    findings.Text="本次分析已取消";findings.ForeColor=Muted;coverage.Text="Coverage 未確認；未使用本次分析結果";candidateStatus.Text="已取消";candidateStatus.ForeColor=Muted;
                    SetProtocolScopePlaceholder("分析已取消","未使用本次分析結果。");
                    title.Text="分析已取消";coordinates.Text="可以匯入另一份 Trace";totals.Text="未使用本次分析結果";summary.Clear();Section(summary,"目前狀態",message.Text);Section(summary,"下一步","工作副本與日誌已保留。重新匯入會建立獨立工作，不會重用本次候選。");
                }
                string id=S(value,"case_id"),revision=S(value,"model_revision");
                if(id!="未知"&&(model==null||id!=caseId||revision!=modelRevision)){
                    LoadModel(id);
                    modelRevision=revision;
                }
                string name=S(value,"trace_name");if(name!="未知")identity.Text=name;
                object config;
                configUrStatus=value.TryGetValue("config_ur",out config)?config as Dictionary<string,object>:null;
            } else if(url!=null) {message.Text="已就緒。拖入一份 .usb / .pex 或按「匯入 Trace」。";busy=false;}
            bool usable=url!=null&&!controller.HasExited&&!busy&&!closing;
            choose.Enabled=usable&&phase!="unresponsive"&&phase!="cleanup_unknown";
            choose.Text=busy?(phase=="navigating"?"正在定位…":"正在分析…"):model!=null||OperationError?"匯入其他 Trace…":"匯入 Trace…";
            choose.Primary=!busy&&!OperationError&&cards.Length==0;
            locate.Visible=cards.Length>0||OperationError;
            locate.Text=OperationError?"查看錯誤與恢復方式":FlowMode?"在 PETracer 查看里程碑":IsPcie?"在 PETracer 定位":"在 LeCroy 定位";
            locate.Primary=!busy&&(cards.Length>0||OperationError);
            locate.Enabled=usable&&(OperationError||(caseId!=null&&candidates.SelectedIndex>=0));
            nextCheck.Visible=FlowMode&&candidates.SelectedIndex>=0&&Map(cards[candidates.SelectedIndex]).ContainsKey("engineer_view");nextCheck.Enabled=usable&&!OperationError&&nextCheck.Visible;
            protocols.Enabled=usable&&model!=null;nativeTargets.Enabled=usable&&cards.Length>0;
            bool hasFlows=false;if(model!=null&&protocols.SelectedIndex>=0){var aa=Items(model,"analyses");if(aa.Length>0)foreach(object c in allObservations)if(S(Map(c),"protocol")==S(Map(aa[protocols.SelectedIndex]),"protocol"))hasFlows=true;}observed.Enabled=usable&&hasFlows;
            copy.Enabled=usable&&cards.Length>0;
            copy.Text=IsPcie?"複製 Packet":"複製位置";copyFile.Visible=IsPcie&&!FlowMode;copyFile.Enabled=usable&&IsPcie;nativeTargets.Width=FlowMode?145:210;
            locateStage.Visible=IsPcie&&!FlowMode&&allObservations.Length>0;locateStage.Enabled=usable&&locateStage.Visible;
            flowView.Enabled=usable;engineerContext.Visible=FlowReady;engineerContext.Enabled=usable&&phase!="unresponsive"&&phase!="cleanup_unknown";
            configUr.Visible=IsPcie&&caseId!=null;configUr.Enabled=configUr.Visible&&url!=null&&!controller.HasExited&&!closing;
            if(configUrView!=null)configUrView.ApplyStatus(configUrStatus,busy,ConfigUrControlsAvailable,phase=="config_ur");
            showAll.Enabled=usable;cancel.Visible=busy&&pendingPcie&&phase!="navigating";cancel.Enabled=cancel.Visible;
            if(pageIndex!=null){int pages=Items(Map(Map(pageIndex["groups"])[FlowMode?"flow_items":"candidates"]),"pages").Length;previousPage.Enabled=usable&&currentPage>0;nextPage.Enabled=usable&&currentPage+1<pages;}
            if(IsPcie)export.Text="匯出報告…";else export.Text="匯出 HTML…";
            end.Enabled=usable&&caseId!=null;export.Enabled=usable&&reportFile!=null&&File.Exists(reportFile);
            progress.Visible=busy;progress.Style=busy?ProgressBarStyle.Marquee:ProgressBarStyle.Blocks;
            if(controller.HasExited) {choose.Enabled=locate.Enabled=end.Enabled=false;if(closing) {allowClose=true;Close();}else message.Text="本機控制程序已結束。請檢查工作資料夾與 launcher-errors.log。";}
        } catch(IOException) {} catch(Exception ex) {message.Text="狀態讀取失敗："+ex.Message;}
    }
    public static void Run(string python,string script,string output) {
        if(Thread.CurrentThread.GetApartmentState()!=ApartmentState.STA)throw new InvalidOperationException("STA required");Application.EnableVisualStyles();Application.Run(new TraceToolEntry(python,script,output));
    }
}

internal sealed class ConfigUrForm : Form {
    const long MaxPageBytes=1024*1024;
    static readonly string[] BindingKeys={"source_trace_sha256","display_trace_sha256","packet_namespace"};
    static readonly string[] GroupKeys={"writes","reads","memory","ur_summary","unmatched"};
    static readonly string[] GroupNames={"Config Write","Config Read","Memory UR／CA","重複 UR","未配對的異常 Completion"};
    static readonly string[] Titles={"Packet","交易","目的／回覆端","位址／暫存器","寫入值／BE","Completion","回讀"};
    static readonly string[] Targets={"request","completion","read_request","read_completion"};
    readonly Action start, stop;
    readonly Action<string,string> navigate;
    readonly string caseFolder, caseId;
    readonly Dictionary<string,object> caseBinding;
    readonly JavaScriptSerializer serializer=new JavaScriptSerializer {MaxJsonLength=1024*1024};
    readonly Label status=new Label {Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,AutoEllipsis=true};
    readonly Label scope=new Label {Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,AutoEllipsis=true};
    readonly Label position=new Label {AutoSize=true,Padding=new Padding(5,7,5,0)};
    readonly ToolTip tips=new ToolTip();
    readonly ComboBox filter=new ComboBox {DropDownStyle=ComboBoxStyle.DropDownList,Width=230};
    readonly Button run=new Button {AutoSize=true,Text="補抽暫存器與 UR"};
    readonly Button cancel=new Button {AutoSize=true,Text="取消補抽"};
    readonly Button previous=new Button {AutoSize=true,Text="上一頁"};
    readonly Button next=new Button {AutoSize=true,Text="下一頁"};
    readonly Button export=new Button {AutoSize=true,Text="匯出暫存器報告…"};
    readonly Button[] openTargets={
        new Button {AutoSize=true,Text="定位原請求"},
        new Button {AutoSize=true,Text="定位 Completion"},
        new Button {AutoSize=true,Text="定位回讀請求"},
        new Button {AutoSize=true,Text="定位回讀 Completion"},
    };
    readonly DataGridView results=new DataGridView {
        Dock=DockStyle.Fill,AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill,
        BorderStyle=BorderStyle.None,BackgroundColor=Color.White,ReadOnly=true,
        AllowUserToAddRows=false,AllowUserToDeleteRows=false,AllowUserToResizeRows=false,
        MultiSelect=false,RowHeadersVisible=false,SelectionMode=DataGridViewSelectionMode.FullRowSelect
    };
    readonly RichTextBox evidence=new RichTextBox {
        Dock=DockStyle.Fill,ReadOnly=true,BackColor=Color.White,DetectUrls=false,ScrollBars=RichTextBoxScrollBars.Vertical
    };
    Dictionary<string,object> index;
    string loadedIndex;
    bool idle, ready, pageLoaded;
    int page;

    internal ConfigUrForm(string folder,string id,Dictionary<string,object> binding,Action start,Action stop,Action<string,string> navigate) {
        caseFolder=Path.GetFullPath(folder);caseId=id;caseBinding=binding;
        this.start=start;this.stop=stop;this.navigate=navigate;
        Text="PCIe 暫存器與 UR";Size=new Size(1080,720);MinimumSize=new Size(820,500);
        Font=new Font("Microsoft JhengHei",10);ForeColor=TraceTheme.Text;BackColor=TraceTheme.Workspace;
        StartPosition=FormStartPosition.CenterParent;AutoScaleMode=AutoScaleMode.Dpi;
        var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=7,Padding=new Padding(14)};
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute,30));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute,30));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute,38));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,58));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute,38));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,42));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute,40));
        Controls.Add(layout);
        layout.Controls.Add(status,0,0); layout.Controls.Add(scope,0,1);
        var filters=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false};
        filter.AccessibleName="暫存器與 UR 類型";
        filter.Items.AddRange(GroupNames);filter.SelectedIndex=0;
        filters.Controls.AddRange(new Control[]{filter,previous,next,position});
        layout.Controls.Add(filters,0,2); layout.Controls.Add(results,0,3);
        results.AccessibleName="暫存器與 UR 證據列";
        evidence.AccessibleName="所選交易的來源與證據";
        int[] weights={74,97,88,182,126,146,120};
        for(int i=0;i<Titles.Length;i++){
            results.Columns.Add(new DataGridViewTextBoxColumn {HeaderText=Titles[i],FillWeight=weights[i],
                SortMode=DataGridViewColumnSortMode.NotSortable});
        }
        var targets=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false};
        for(int i=0;i<openTargets.Length;i++){
            int slot=i;openTargets[i].Click+=delegate {NavigateSelected(slot);};targets.Controls.Add(openTargets[i]);
        }
        layout.Controls.Add(targets,0,4);layout.Controls.Add(evidence,0,5);
        var actions=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false};
        actions.Controls.AddRange(new Control[]{run,cancel,export});layout.Controls.Add(actions,0,6);
        run.Click+=delegate {if(idle)this.start();};
        cancel.Click+=delegate {this.stop();};
        export.Click+=delegate {Export();};
        previous.Click+=delegate {ShowPage(page-1);};next.Click+=delegate {ShowPage(page+1);};
        filter.SelectedIndexChanged+=delegate {ShowPage(0);};
        results.CurrentCellChanged+=delegate {SelectionChanged();};
        FormClosed+=delegate {tips.Dispose();};
    }

    static string TextValue(Dictionary<string,object> data,string key) {
        object value;
        return data!=null&&data.TryGetValue(key,out value)&&value!=null?Convert.ToString(value,CultureInfo.InvariantCulture):"";
    }
    static object[] Values(Dictionary<string,object> data,string key) {
        object value;
        if(!data.TryGetValue(key,out value)||value==null)throw new InvalidDataException("缺少暫存器報告欄位。");
        var array=value as object[];
        if(array!=null)return array;
        var list=value as ArrayList;
        if(list!=null)return list.ToArray();
        throw new InvalidDataException("暫存器報告欄位格式不符。");
    }
    static Dictionary<string,object> Object(Dictionary<string,object> data,string key) {
        object value;
        if(data.TryGetValue(key,out value)&&value is Dictionary<string,object>)return (Dictionary<string,object>)value;
        throw new InvalidDataException("暫存器報告缺少必要物件。");
    }
    static void VerifyRegularPath(string path) {
        if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)
            throw new InvalidDataException("暫存器報告路徑指向工作區外的連結。");
    }
    internal static string ResolveIndex(string folder,string relative) {
        if(!System.Text.RegularExpressions.Regex.IsMatch(relative??"", @"\Aconfig-ur-[0-9a-f]{32}/index\.json\z"))
            throw new InvalidDataException("暫存器報告索引路徑不符。");
        string path=Path.Combine(folder,relative.Replace('/',Path.DirectorySeparatorChar));
        VerifyRegularPath(folder);VerifyRegularPath(Path.GetDirectoryName(path));VerifyRegularPath(path);
        return path;
    }
    Dictionary<string,object> LoadBounded(string path) {
        VerifyRegularPath(path);
        using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
            if(stream.Length>MaxPageBytes)throw new InvalidDataException("暫存器報告分頁超出大小上限。");
            using(var reader=new StreamReader(stream,new UTF8Encoding(false,true)))
                return serializer.Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
        }
    }
    void VerifyBinding(Dictionary<string,object> data,string schema) {
        if(TextValue(data,"analysis_id")!=caseId||TextValue(data,"schema")!=schema)
            throw new InvalidDataException("暫存器證據不屬於目前案件。");
        foreach(var field in BindingKeys)
            if(TextValue(caseBinding,field).Length==0||TextValue(caseBinding,field)!=TextValue(data,field))
                throw new InvalidDataException("暫存器證據來源或 Packet 命名空間不符。");
    }
    void LoadIndex(string relative) {
        string path=ResolveIndex(caseFolder,relative);
        var data=LoadBounded(path);VerifyBinding(data,"pcie.config-ur-index/v1");
        foreach(string key in GroupKeys)
            if(Values(Object(Object(data,"groups"),key),"pages").Length==0)
                throw new InvalidDataException("暫存器報告缺少分頁。");
        if(TextValue(data,"report_html")!="report.html"||TextValue(data,"report_markdown")!="report.md")
            throw new InvalidDataException("暫存器報告檔名不符。");
        loadedIndex=path; index=data;
        ShowPage(0);
    }
    internal void ApplyStatus(Dictionary<string,object> operation,bool busy,bool enabled,bool supplementActive) {
        if(IsDisposed)return;
        string state=TextValue(operation,"state");
        string notice=TextValue(operation,"message");
        idle=enabled&&!busy;
        cancel.Enabled=enabled&&busy&&supplementActive;
        run.Enabled=idle;
        status.Text=notice.Length>0?notice:state=="running"?"正在補抽暫存器與 UR…":
            state=="ready"?"可查看已核對的暫存器和 UR 證據。":state=="cancelled"?"已取消補抽。":
            state=="error"?"暫存器與 UR 補抽未完成。":"從目前 PCIe 案件補抽暫存器與 UR。";
        ready=state=="ready";
        if(ready){
            string rel=TextValue(operation,"index");
            try {
                string path=ResolveIndex(caseFolder,rel);
                if(path!=loadedIndex)LoadIndex(rel);
                else if(!pageLoaded)ShowPage(page);
            }catch(Exception ex){
                status.Text="暫存器報告讀取失敗："+ex.Message;
                ready=false;
            }
        }
        scope.Text=index==null?"":TextValue(index,"coverage_text")+(ready?"":" · 上次完成的補抽");
        tips.SetToolTip(scope,scope.Text);
        run.Text=index==null?"補抽暫存器與 UR":"重新補抽";
        filter.Enabled=index!=null;
        export.Enabled=index!=null&&ready&&!busy;
        SelectionChanged();
    }
    void ShowPage(int number) {
        if(index==null)return;
        string key=GroupKeys[filter.SelectedIndex];
        try {
            var group=Object(Object(index,"groups"),key);var pages=Values(group,"pages");
            if(number<0||number>=pages.Length)return;
            page=number;
            string leaf=Convert.ToString(pages[number],CultureInfo.InvariantCulture);
            if(leaf!=key+"-"+number.ToString(CultureInfo.InvariantCulture)+".json")
                throw new InvalidDataException("暫存器報告分頁路徑不符。");
            var content=LoadBounded(Path.Combine(Path.GetDirectoryName(loadedIndex),leaf));
            VerifyBinding(content,"pcie.config-ur-page/v1");
            if(TextValue(content,"group")!=key||TextValue(content,"page")!=number.ToString(CultureInfo.InvariantCulture))
                throw new InvalidDataException("暫存器報告分頁身分不符。");
            var pageRows=Values(content,"rows");
            if(pageRows.Length>20)throw new InvalidDataException("暫存器報告列數超過上限。");
            foreach(object entry in pageRows){
                var row=(Dictionary<string,object>)entry;var columns=Values(row,"columns");
                if(columns.Length!=Titles.Length||Array.Exists(columns,v=>!(v is string))||
                    Array.Exists(Values(row,"details"),v=>!(v is string)))
                    throw new InvalidDataException("暫存器報告欄位格式不符。");
                Object(row,"locations");
            }
            results.Rows.Clear();
            foreach(Dictionary<string,object> row in pageRows){
                results.Rows[results.Rows.Add(Values(row,"columns"))].Tag=row;
            }
            pageLoaded=true;
            position.Text=(page+1)+" / "+pages.Length+" 頁 · "+TextValue(group,"count")+" 筆";
            previous.Enabled=page>0;next.Enabled=page+1<pages.Length;
        }catch(Exception ex){
            pageLoaded=false;
            results.Rows.Clear();position.Text="分頁讀取失敗";previous.Enabled=next.Enabled=false;
            evidence.Text=ex.Message;
        }
        SelectionChanged();
    }
    Dictionary<string,object> Selected {
        get{return results.CurrentRow==null?null:results.CurrentRow.Tag as Dictionary<string,object>;}
    }
    void SelectionChanged() {
        var row=Selected;
        if(row==null){
            if(position.Text!="分頁讀取失敗")evidence.Text="";
            foreach(var target in openTargets)target.Enabled=false;
            return;
        }
        var text=new StringBuilder();
        foreach(object line in Values(row,"details"))text.AppendLine(Convert.ToString(line,CultureInfo.InvariantCulture));
        string nextText=text.ToString();
        if(evidence.Text.Replace("\r\n","\n")!=nextText.Replace("\r\n","\n"))evidence.Text=nextText;
        var locations=Object(row,"locations");
        for(int i=0;i<Targets.Length;i++)openTargets[i].Enabled=idle&&ready&&locations.ContainsKey(Targets[i]);
    }
    void NavigateSelected(int slot) {
        var selected=Selected;
        if(selected==null||!ready||!idle||!openTargets[slot].Enabled)return;
        string id=TextValue(selected,"id");
        if(!System.Text.RegularExpressions.Regex.IsMatch(id,@"\Ap[0-9]+\z"))return;
        this.navigate(id,Targets[slot]);
    }
    void Export() {
        if(index==null||!ready)return;
        using(var save=new SaveFileDialog {FileName="pcie-config-ur-report",Filter="HTML report (*.html)|*.html|Markdown report (*.md)|*.md"}){
            if(save.ShowDialog(this)!=DialogResult.OK)return;
            try {
                string dest=Path.GetFullPath(save.FileName);
                if(dest.StartsWith(caseFolder+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
                    throw new IOException("請將報告匯出到案件工作資料夾以外的位置。");
                string ext=Path.GetExtension(dest).ToLowerInvariant();
                if(ext!=".html"&&ext!=".md")throw new IOException("請使用 .html 或 .md 副檔名。");
                VerifyRegularPath(caseFolder);
                VerifyRegularPath(Path.GetDirectoryName(loadedIndex));
                string source=Path.Combine(Path.GetDirectoryName(loadedIndex),ext==".md"?"report.md":"report.html");
                VerifyRegularPath(source);
                TraceReportExport.Copy(source,dest,new Dictionary<string,object>());
                status.Text="已匯出暫存器報告："+dest;
            }catch(Exception ex){MessageBox.Show(this,"匯出失敗："+ex.Message,"暫存器與 UR");}
        }
    }
}

// Export external evidence together with its report; never rewrite sealed source evidence.
public static class TraceReportExport {
    static string Hash(string path) {
        using(var sha=System.Security.Cryptography.SHA256.Create())using(var stream=File.OpenRead(path))
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    public static bool Copy(string source,string destination,Dictionary<string,object> model) {
        source=Path.GetFullPath(source);destination=Path.GetFullPath(destination);
        if(String.Equals(source,destination,StringComparison.OrdinalIgnoreCase))throw new IOException("請選擇工作報告以外的匯出位置。");
        if(!model.ContainsKey("external_model")){File.Copy(source,destination,true);return false;}
        if(new FileInfo(source).Length>16*1024*1024)throw new IOException("報告摘要超過匯出安全預算；完整資料仍在工作資料夾。");
        var meta=(Dictionary<string,object>)model["external_model"];
        var refs=(IEnumerable)meta["refs"];
        string root=Path.GetDirectoryName(source)+Path.DirectorySeparatorChar;
        string sidecar=Path.Combine(Path.GetDirectoryName(destination),Path.GetFileNameWithoutExtension(destination)+"-evidence-"+Guid.NewGuid().ToString("N").Substring(0,8));
        string text=File.ReadAllText(source,Encoding.UTF8);Directory.CreateDirectory(sidecar);
        foreach(object entry in refs) {
            var r=(Dictionary<string,object>)entry;string path=Path.GetFullPath((string)r["path"]),expected=(string)r["sha256"];
            if(!path.StartsWith(root,StringComparison.OrdinalIgnoreCase)||!String.Equals(Hash(path),expected,StringComparison.OrdinalIgnoreCase))throw new IOException("證據附件身分不符，停止匯出。");
            string target=Path.Combine(sidecar,Path.GetFileName(path));File.Copy(path,target,false);
            if(!String.Equals(Hash(target),expected,StringComparison.OrdinalIgnoreCase))throw new IOException("附件複製核對失敗。");
            string relative=path.Substring(root.Length).Replace('\\','/');
            string link=Uri.EscapeDataString(Path.GetFileName(sidecar))+"/"+Uri.EscapeDataString(Path.GetFileName(path));
            text=text.Replace(relative,link).Replace(path,link);
        }
        string temporary=destination+".tmp-"+Guid.NewGuid().ToString("N");File.WriteAllText(temporary,text,new UTF8Encoding(false));
        if(File.Exists(destination))File.Replace(temporary,destination,null);else File.Move(temporary,destination);
        return true;
    }
}
