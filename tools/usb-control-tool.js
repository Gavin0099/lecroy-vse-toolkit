function initializeTraceTool() {
  const boot = JSON.parse(document.getElementById('tool-boot').textContent);
  const status = document.getElementById('tool-status');
  let busy = false;
  async function send(path, data) {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json', 'X-Trace-Session':boot.token}, body:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '目前正在處理另一項操作，請稍候。');
    return result;
  }
  document.querySelectorAll('.goto').forEach(button => button.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    document.querySelectorAll('.goto').forEach(b => b.disabled = true);
    status.textContent = '定位請求送出中…';
    try {await send('/navigate', {case_id:boot.case_id, rank:Number(button.dataset.rank)});}
    catch (error) {status.textContent = error.message; busy = false;}
  }));
  document.getElementById('reload').addEventListener('click', () => location.reload());
  document.getElementById('end-session').addEventListener('click', async () => {
    try {await send('/end', {});} catch (error) {status.textContent = error.message;}
  });
  async function poll() {
    try {
      const response = await fetch('/status', {headers:{'X-Trace-Session':boot.token}});
      if (!response.ok) throw new Error('工作階段已失效，請重新開啟工具。');
      const state = await response.json();
      if (state.case_id !== boot.case_id) {location.reload();return;}
      busy = state.busy;
      status.textContent = state.message;
      document.querySelectorAll('.goto').forEach(b => b.disabled = busy || ['unresponsive','cleanup_unknown','closed'].includes(state.phase));
      document.getElementById('end-session').disabled = busy || state.phase === 'closed';
    } catch (error) {status.textContent = '無法連線本機工具。' + error.message;}
    setTimeout(poll, 500);
  }
  poll();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeTraceTool);
else initializeTraceTool();
