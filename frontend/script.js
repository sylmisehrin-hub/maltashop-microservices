'use strict';
const $ = id => document.getElementById(id);
const state = {notifications: [], health: {order:false, notification:false}, loading:false};
const names = {overview:'Overview',orders:'Orders',activity:'Activity'};
async function getJSON(url, options={}) {
  const res = await fetch(url,{cache:'no-store',...options});
  const data = await res.json().catch(()=>null);
  if(!res.ok) throw new Error(data?.error || `Request failed (HTTP ${res.status})`);
  return data;
}
function el(tag, className, text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=String(text);return node;}
function showMessage(target,title,lines,error=false){const box=$(target);box.replaceChildren();box.classList.toggle('error',error);box.append(el('strong','',title));for(const [label,value] of lines){box.append(el('div','',`${label}: ${value ?? '—'}`));}box.hidden=false;}
function navigate(view){if(!names[view])view='overview';document.querySelectorAll('.page-view').forEach(x=>x.classList.toggle('active',x.id===`view-${view}`));document.querySelectorAll('.nav-link').forEach(x=>x.classList.toggle('active',x.dataset.view===view));$('breadcrumb-current').textContent=names[view];$('sidebar').classList.remove('open');if(location.hash!==`#${view}`)history.replaceState(null,'',`#${view}`);}
function toast(message){const node=$('toast');node.textContent=message;node.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>node.hidden=true,3500);}
function renderRecent(){const container=$('recent-activity');container.replaceChildren();if(!state.notifications.length){container.append(el('div','empty','No order updates yet. Create an order to get started.'));return;}for(const item of state.notifications.slice(0,5)){const row=el('div','activity-item');row.append(el('span','activity-icon','✓'));const body=el('div','activity-body');body.append(el('strong','',item.message||`Order #${item.order_id} confirmed`));body.append(el('span','',`Customer #${item.customer_id} · Order #${item.order_id}`));row.append(body,el('span','activity-tag','Received'));container.append(row);}}
function renderTable(){const body=$('activity-rows');body.replaceChildren();$('activity-subtitle').textContent=`${state.notifications.length} notification${state.notifications.length===1?'':'s'} recorded`;if(!state.notifications.length){const tr=el('tr');const td=el('td','empty','No notifications have been recorded yet.');td.colSpan=4;tr.append(td);body.append(tr);return;}for(const item of state.notifications){const tr=el('tr');const td1=el('td');td1.append(el('strong','',item.message||'Order update'));tr.append(td1,el('td','',`#${item.order_id}`),el('td','',`#${item.customer_id}`));const td4=el('td');td4.append(el('code','',item.correlation_id||'—'));tr.append(td4);body.append(tr);}}
async function refresh(){if(state.loading)return;state.loading=true;$('refresh-btn').disabled=true;try{
  const [orders,notifications,items]=await Promise.allSettled([getJSON('/api/order-health'),getJSON('/api/notification-health'),getJSON('/api/notifications')]);
  state.health.order=orders.status==='fulfilled'&&orders.value?.status==='healthy';
  state.health.notification=notifications.status==='fulfilled'&&notifications.value?.status==='healthy';
  const count=Number(state.health.order)+Number(state.health.notification);
  $('stat-services').textContent=`${count} / 2`;$('service-detail').textContent=count===2?'All APIs responding':`${2-count} API${count===1?'':'s'} unavailable`;
  $('sync-dot').className=`sync-dot ${count===2?'good':'bad'}`;$('sync-label').textContent=count===2?'Systems online':'Connection issue';
  if(items.status==='fulfilled'&&Array.isArray(items.value)){
    state.notifications=items.value;
    $('stat-notifications').textContent=String(state.notifications.length);
    $('nav-count').textContent=String(state.notifications.length);
    $('stat-latest').textContent=state.notifications.length?`#${state.notifications[0].order_id}`:'—';
    renderRecent();renderTable();
  }else{if(!state.notifications.length){$('recent-activity').replaceChildren(el('div','empty','Could not load recent activity.'));$('activity-subtitle').textContent='Unable to load notifications';}}
}finally{state.loading=false;$('refresh-btn').disabled=false;}}
function positiveInt(value){const n=Number(value);return Number.isSafeInteger(n)&&n>0?n:null;}
$('order-form').addEventListener('submit',async e=>{e.preventDefault();const customer_id=positiveInt($('customer-id').value),product_id=positiveInt($('product-id').value),quantity=positiveInt($('quantity').value);if(!customer_id||!product_id||!quantity){showMessage('order-result','Check your details',[['Error','Enter positive whole numbers in all fields']],true);return;}const button=$('submit-order');button.disabled=true;button.textContent='Placing order…';try{const order=await getJSON('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer_id,product_id,quantity})});showMessage('order-result','Order placed successfully',[['Order ID',`#${order.order_id}`],['Status',order.status],['Correlation ID',order.correlation_id]]);$('order-form').reset();$('quantity').value='1';toast(`Order #${order.order_id} placed`);setTimeout(refresh,1300);setTimeout(refresh,6000);}catch(err){showMessage('order-result','Could not place order',[['Error',err.message]],true);}finally{button.disabled=false;button.innerHTML='Place order <span>→</span>';}});
$('lookup-form').addEventListener('submit',async e=>{e.preventDefault();const id=positiveInt($('lookup-id').value);if(!id){showMessage('lookup-result','Invalid order ID',[['Error','Enter a positive whole number']],true);return;}try{const order=await getJSON(`/api/orders/${id}`);showMessage('lookup-result',`Order #${order.order_id}`,[['Customer',`#${order.customer_id}`],['Product',`#${order.product_id}`],['Quantity',order.quantity],['Status',order.status]]);}catch(err){showMessage('lookup-result','Order not found',[['Error',err.message]],true);}});
document.querySelectorAll('[data-go]').forEach(button=>button.addEventListener('click',()=>{navigate(button.dataset.go);if(button.dataset.focus==='lookup')$('lookup-id').focus();}));
document.querySelectorAll('.nav-link').forEach(link=>link.addEventListener('click',e=>{e.preventDefault();navigate(link.dataset.view);}));
$('menu-btn').addEventListener('click',()=>$('sidebar').classList.toggle('open'));
$('refresh-btn').addEventListener('click',refresh);$('activity-refresh').addEventListener('click',refresh);
window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));
navigate(location.hash.slice(1)||'overview');refresh();setInterval(refresh,8000);
