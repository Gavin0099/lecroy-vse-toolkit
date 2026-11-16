using System.Drawing;
using System.Windows.Forms;

public static class TraceTheme {
    public static readonly Color Workspace=ColorTranslator.FromHtml("#F5F5F5"), Reading=Color.White,
        Text=ColorTranslator.FromHtml("#242424"), Secondary=ColorTranslator.FromHtml("#616161"),
        Action=ColorTranslator.FromHtml("#0F6CBD"), Hover=ColorTranslator.FromHtml("#115EA3"),
        Pressed=ColorTranslator.FromHtml("#0F548C"), Border=ColorTranslator.FromHtml("#8A8A8A"),
        Divider=ColorTranslator.FromHtml("#E0E0E0"), Selected=ColorTranslator.FromHtml("#EBF3FC"),
        Error=ColorTranslator.FromHtml("#B10E1E"), Warning=ColorTranslator.FromHtml("#8A3707");
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
