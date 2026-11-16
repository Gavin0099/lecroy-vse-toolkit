using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Windows.Forms;

public static class TraceTheme {
    public static readonly Color Workspace=ColorTranslator.FromHtml("#F5F5F5"), Reading=Color.White,
        Text=ColorTranslator.FromHtml("#242424"), Secondary=ColorTranslator.FromHtml("#475569"),
        Action=ColorTranslator.FromHtml("#1D4ED8"), Hover=ColorTranslator.FromHtml("#1E40AF"),
        Pressed=ColorTranslator.FromHtml("#1E3A8A"), Border=ColorTranslator.FromHtml("#8A8A8A"),
        Divider=ColorTranslator.FromHtml("#E0E0E0"), Selected=ColorTranslator.FromHtml("#EFF6FF"),
        ConfirmedError=ColorTranslator.FromHtml("#B91C1C"), Review=ColorTranslator.FromHtml("#B45309"),
        Related=ColorTranslator.FromHtml("#6D28D9"), Verified=ColorTranslator.FromHtml("#0F766E"),
        Neutral=ColorTranslator.FromHtml("#475569");
    // Operation errors have a red label; candidate traffic never supplies a
    // confirmed-violation verdict. An observation (including NAK/PM) is neutral.
    public static readonly Color Error=ConfirmedError, Warning=Review;
    public static Color Candidate(bool observation){return observation?Neutral:Review;}
}

// Read-only presentation helpers, shared by USB/PCIe. No detector or ranking.
public static class TracePresentation {
    public static string Text(Dictionary<string,object> data,string key) {
        object value;return data!=null&&data.TryGetValue(key,out value)&&value!=null?Convert.ToString(value,CultureInfo.InvariantCulture):"未知";
    }
    public static object[] Items(Dictionary<string,object> data,string key){
        object value;if(data==null||!data.TryGetValue(key,out value)||value==null)return new object[0];
        var items=value as object[];if(items!=null)return items;var list=value as ArrayList;return list!=null?list.ToArray():new object[0];
    }
    public static string Headline(Dictionary<string,object> card){
        foreach(object fact in Items(card,"facts")) {
            string text=Convert.ToString(fact);
            if(Text(card,"protocol")=="PCIe"&&text.Contains("same association key observed again")&&text.Contains("before an associated completion was observed"))return "同一關聯 Key 再次出現";
        }
        return Text(card,"title");
    }
    public static string FlowLabel(Dictionary<string,object> card){
        object value;
        var view=card.TryGetValue("engineer_view",out value)?value as Dictionary<string,object>:null;
        foreach(object item in Items(view,"resolved_evidence")) {
            var fact=item as Dictionary<string,object>;
            if(Text(fact,"id")=="directional_l0")return "連線觀察（非故障）";
        }
        return "待確認階段（未判錯）";
    }
    public static string Coverage(Dictionary<string,object> analysis){
        if(analysis==null)return "Coverage 未提供；完整範圍待核對";
        object value;var coverage=analysis.TryGetValue("coverage",out value)?value as Dictionary<string,object>:null;
        string protocol=Text(analysis,"protocol"),state=Text(analysis,"state"),counts="擷取數量未提供";
        if(coverage!=null){
            if(protocol=="PCIe")counts=Text(coverage,"tlp_count")+" 筆 TLP";
            else if(protocol=="USB2")counts=Text(coverage,"eligible_controls")+" 筆 EP0 控制傳輸";
            else if(protocol=="USB3")counts=Text(coverage,"link_total")+" Link / "+Text(coverage,"lfps_total")+" LFPS";
            else if(protocol=="PD")counts=Text(coverage,"pd_packet_events")+" PD Packets / "+Text(coverage,"transfers")+" Transfers";
        }
        if(state=="not_observed")return "Coverage · 未觀察到 "+protocol+" 分析事件；不代表測試通過";
        if(state=="failed")return "Coverage · 擷取失敗，無法判定本次範圍";
        bool truncated=coverage!=null&&((coverage.ContainsKey("truncated")&&Equals(coverage["truncated"],true))||(coverage.ContainsKey("headers_truncated")&&Equals(coverage["headers_truncated"],true)));
        return "Coverage · 已取得 "+counts+(state=="partial"||truncated?" · 資料部分缺漏／截斷":" · 完整範圍待核對");
    }
    public static string EvidenceTime(Dictionary<string,object> row){
        object value;if(row.TryGetValue("timestamp_ns",out value)&&value!=null){
            decimal ns;if(decimal.TryParse(Convert.ToString(value,CultureInfo.InvariantCulture),NumberStyles.Number,CultureInfo.InvariantCulture,out ns))return (ns/1000000000m).ToString("0.000000000",CultureInfo.InvariantCulture)+" s";
        }
        return Text(row,"time_display")=="未知"?"時間未知":Text(row,"time_display")+"（原始精度）";
    }
    public static string EvidenceUnit(Dictionary<string,object> row,string protocol){
        string index=Text(row,"index");long number;
        if(!long.TryParse(index,out number))return index; // Transfer/Transaction namespace already supplied by PD.
        return (protocol=="USB2"?"Transfer ":"Packet ")+index;
    }
    public static string EvidenceKey(Dictionary<string,object> row,string protocol){
        return protocol+" · "+EvidenceUnit(row,protocol)+" · "+Text(row,"channel");
    }
    public static bool HasExactTime(Dictionary<string,object> row){object value;return row.TryGetValue("timestamp_ns",out value)&&value!=null;}
    public static string TimelineNote(object[] rows){
        bool exact=rows.Length>0;decimal previous=decimal.MinValue;
        foreach(object item in rows){var row=(Dictionary<string,object>)item;decimal value;
            if(!HasExactTime(row)||!decimal.TryParse(Text(row,"timestamp_ns"),NumberStyles.Number,CultureInfo.InvariantCulture,out value)||value<previous){exact=false;break;}previous=value;
        }
        return exact?"事件時間線 · 僅已保存的關聯事件，非全檔覆蓋":"相關事件順序 · 時間精度有限／未知，不按間距估時";
    }
}

public sealed class TraceButton:Button {
    bool primary,hover,pressed;
    public bool Primary {get{return primary;}set{if(primary!=value){primary=value;Invalidate();}}}
    public TraceButton(){SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer,true);}
    protected override void OnMouseEnter(System.EventArgs e){hover=true;Invalidate();base.OnMouseEnter(e);}
    protected override void OnMouseLeave(System.EventArgs e){hover=pressed=false;Invalidate();base.OnMouseLeave(e);}
    protected override void OnMouseDown(MouseEventArgs e){pressed=true;Invalidate();base.OnMouseDown(e);}
    protected override void OnMouseUp(MouseEventArgs e){pressed=false;Invalidate();base.OnMouseUp(e);}
    protected override void OnKeyDown(KeyEventArgs e){if(e.KeyCode==Keys.Space){pressed=true;Invalidate();}base.OnKeyDown(e);}
    protected override void OnKeyUp(KeyEventArgs e){pressed=false;Invalidate();base.OnKeyUp(e);}
    protected override void OnGotFocus(System.EventArgs e){Invalidate();base.OnGotFocus(e);}
    protected override void OnLostFocus(System.EventArgs e){pressed=false;Invalidate();base.OnLostFocus(e);}
    protected override void OnEnabledChanged(System.EventArgs e){pressed=hover=false;Invalidate();base.OnEnabledChanged(e);}
    protected override void OnPaint(PaintEventArgs e) {
        bool hc=SystemInformation.HighContrast;
        Color back=hc?(Primary?SystemColors.Highlight:SystemColors.Control):!Enabled?TraceTheme.Workspace:Primary?(pressed?TraceTheme.Pressed:hover?TraceTheme.Hover:TraceTheme.Action):(pressed?TraceTheme.Divider:hover?TraceTheme.Workspace:TraceTheme.Reading);
        Color ink=!Enabled?SystemColors.GrayText:hc?(Primary?SystemColors.HighlightText:SystemColors.ControlText):Primary?Color.White:TraceTheme.Text;
        using(var brush=new SolidBrush(back))e.Graphics.FillRectangle(brush,ClientRectangle);
        using(var pen=new Pen(hc?SystemColors.ControlText:Primary&&Enabled?back:TraceTheme.Border))e.Graphics.DrawRectangle(pen,0,0,Width-1,Height-1);
        TextRenderer.DrawText(e.Graphics,Text,Font,ClientRectangle,ink,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.SingleLine);
        if(Focused&&Enabled)using(var pen=new Pen(hc?SystemColors.ControlText:Primary?Color.White:TraceTheme.Action,2))e.Graphics.DrawRectangle(pen,3,3,Width-7,Height-7);
    }
}
