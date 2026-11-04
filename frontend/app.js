const translations={
en:{workspace:"WORKSPACE",overview:"Overview",hostName:"HOSTNAME",platform:"PLATFORM",uptime:"UPTIME",services:"Services",storage:"Storage",processes:"Processes",networkPage:"Network",serviceDiscoveryPending:"Service discovery will be enabled after the target Linux init system is identified.",containers:"Containers",terminal:"Terminal",security:"Security",ai:"AI Assistant",demoMode:"Demo mode",awaiting:"Awaiting server connection",settings:"Settings",systemStandby:"SYSTEM STANDBY",controlCenter:"CONTROL CENTER",overviewTitle:"Server overview",overviewSub:"Monitor your infrastructure from one command center.",refresh:"Refresh",preview:"Preview environment",previewText:"Metrics below are sample data until a Linux host is connected.",notConnected:"NOT CONNECTED",cpuUsage:"CPU USAGE",memory:"MEMORY",processorLoad:"Processor load",memoryUsed:"Memory used",diskUsed:"Disk used",network:"NETWORK",download:"↓ DOWNLOAD",upload:"↑ UPLOAD",interface:"Interface",systemHealth:"SYSTEM HEALTH",serviceStatus:"Service status",viewAll:"VIEW ALL ↗",running:"Running",idle:"Idle",monitoring:"MONITORING",recentActivity:"Recent activity",backupCompleted:"Backup completed",serviceRestarted:"Service restarted",securityScan:"Security scan finished",noIssues:"No issues detected",demoActivity:"Illustrative activity · not live system events",footerNote:"Designed for secure, local-first server administration.",aiTitle:"DeepSeek AI Assistant",aiSub:"Ask about Linux, programming, or analyze your connected host.",aiReady:"AI READY",aiOffline:"AI NOT CONFIGURED",aiWelcome:"Hello. I can explain Linux, help with programming, and analyze read-only host metrics when you choose to share them.",aiPlaceholder:"Ask LinuxCore AI something...",aiSend:"Send",aiContext:"Include aggregate host metrics in this request",aiPrivacy:"Only aggregate CPU, memory, disk, uptime and storage summary are shared. No process details or secrets.",aiThinking:"Thinking...",aiSetup:"Add DEEPSEEK_API_KEY to the backend environment to enable the assistant.",aiError:"The assistant could not answer. Check the backend and API configuration.",aiEmpty:"Write a message first.",aiUnavailable:"AI assistant is unavailable until its backend is configured."},
ar:{workspace:"مساحة العمل",overview:"نظرة عامة",hostName:"اسم المضيف",platform:"النظام والمنصة",uptime:"مدة التشغيل",services:"الخدمات",storage:"التخزين",processes:"العمليات",networkPage:"الشبكة",serviceDiscoveryPending:"سيتم تفعيل اكتشاف الخدمات بعد تحديد مدير التشغيل داخل توزيعة Linux.",containers:"الحاويات",terminal:"الطرفية",security:"الأمان",ai:"المساعد الذكي",demoMode:"وضع تجريبي",awaiting:"في انتظار اتصال السيرفر",settings:"الإعدادات",systemStandby:"النظام في وضع الاستعداد",controlCenter:"مركز التحكم",overviewTitle:"نظرة عامة على السيرفر",overviewSub:"راقب البنية التحتية من مركز تحكم واحد.",refresh:"تحديث",preview:"بيئة معاينة",previewText:"المؤشرات التالية تجريبية حتى يتم توصيل خادم Linux.",notConnected:"غير متصل",cpuUsage:"استخدام المعالج",memory:"الذاكرة",processorLoad:"حمل المعالج",memoryUsed:"الذاكرة المستخدمة",diskUsed:"المساحة المستخدمة",network:"الشبكة",download:"↓ تنزيل",upload:"↑ رفع",interface:"واجهة الاتصال",systemHealth:"حالة النظام",serviceStatus:"حالة الخدمات",viewAll:"عرض الكل ↗",running:"يعمل",idle:"خامل",monitoring:"المراقبة",recentActivity:"النشاط الأخير",backupCompleted:"اكتمل النسخ الاحتياطي",serviceRestarted:"أُعيد تشغيل الخدمة",securityScan:"اكتمل فحص الأمان",noIssues:"لم يتم اكتشاف مشكلات",demoActivity:"نشاط توضيحي · ليس أحداثًا مباشرة",footerNote:"مصممة لإدارة السيرفرات محليًا وبشكل آمن.",aiTitle:"مساعد DeepSeek الذكي",aiSub:"اسأل عن Linux والبرمجة أو اطلب تحليل بيانات السيرفر المتصل.",aiReady:"الذكاء الاصطناعي جاهز",aiOffline:"الذكاء الاصطناعي غير مُعد",aiWelcome:"أهلًا. أقدر أشرح Linux وأساعدك في البرمجة وأحلل مؤشرات السيرفر للقراءة فقط لما تختار مشاركتها.",aiPlaceholder:"اسأل LinuxCore AI...",aiSend:"إرسال",aiContext:"إرفاق مؤشرات السيرفر المجمعة في الطلب ده",aiPrivacy:"سيتم إرسال مؤشرات CPU والذاكرة والتخزين ومدة التشغيل فقط. لا نرسل تفاصيل العمليات أو الأسرار.",aiThinking:"جاري التفكير...",aiSetup:"أضف DEEPSEEK_API_KEY إلى بيئة تشغيل Backend لتفعيل المساعد.",aiError:"المساعد لم يتمكن من الرد. راجع إعدادات Backend وAPI.",aiEmpty:"اكتب رسالة الأول.",aiUnavailable:"المساعد غير متاح حتى يتم إعداد Backend."}
};
let lang="en";
try{lang=localStorage.getItem("linuxcore-lang")||"en"}catch{}
let currentPage="overview";
let previousNetwork=null;
let aiConfigured=false;
let aiBusy=false;
const aiHistory=[];
function t(key){return translations[lang][key]||key}
function applyLanguage(){document.documentElement.lang=lang;document.documentElement.dir=lang==="ar"?"rtl":"ltr";document.querySelectorAll("[data-i18n]").forEach(el=>{const k=el.dataset.i18n;if(translations[lang][k])el.textContent=translations[lang][k]});document.getElementById("langBtn").textContent=lang==="en"?"عربي":"English";document.getElementById("pageTitle").textContent=currentPage==="ai"?t("ai"):(translations[lang][currentPage]||currentPage);
 if(currentPage!=="overview"&&currentPage!=="ai")renderModule(currentPage);document.getElementById("aiInput").placeholder=t("aiPlaceholder");document.getElementById("aiSend").textContent=t("aiSend");document.getElementById("aiContextLabel").textContent=t("aiContext");document.getElementById("aiPrivacy").textContent=t("aiPrivacy");document.getElementById("aiTitle").textContent=t("aiTitle");document.getElementById("aiSub").textContent=t("aiSub")}
function toast(message){const el=document.getElementById("toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2200)}
document.getElementById("langBtn").addEventListener("click",()=>{lang=lang==="en"?"ar":"en";try{localStorage.setItem("linuxcore-lang",lang)}catch{}applyLanguage()});
document.getElementById("refreshBtn").addEventListener("click",()=>{loadMetrics(true)});
document.querySelectorAll(".nav-item[data-page]").forEach(btn=>btn.addEventListener("click",()=>navigate(btn.dataset.page,btn)));
function navigate(page,button){
 currentPage=page;
 document.querySelectorAll(".nav-item").forEach(x=>x.classList.remove("active"));
 if(button)button.classList.add("active");
 const ai=page==="ai",module=page!=="overview"&&!ai;
 document.getElementById("aiWorkspace").hidden=!ai;
 document.getElementById("moduleWorkspace").hidden=!module;
 [".page-head",".notice",".metric-grid",".system-facts",".content-grid"].forEach(selector=>document.querySelector(selector).hidden=ai||module);
 document.querySelector(".footer").hidden=ai;
 document.getElementById("pageTitle").dataset.page=ai?"ai":page;
 document.getElementById("pageTitle").textContent=ai?t("ai"):(translations[lang][page]||page);
 if(ai)checkAIStatus();
 if(module)renderModule(page);
 if(page==="overview")loadMetrics();
}
document.querySelectorAll("[data-go]").forEach(a=>a.addEventListener("click",e=>{e.preventDefault();navigate("services",document.querySelector('[data-page="services"]'))}));
function moduleNode(tag,cls,content){const el=document.createElement(tag);if(cls)el.className=cls;if(content!==undefined)el.textContent=content;return el}
function moduleTable(headers,rows){
 const table=moduleNode("table","module-table"),thead=moduleNode("thead"),tr=moduleNode("tr");
 headers.forEach(h=>tr.append(moduleNode("th","",h)));thead.append(tr);table.append(thead);
 const tbody=moduleNode("tbody");
 rows.forEach(row=>{const line=moduleNode("tr");row.forEach(value=>line.append(moduleNode("td","",String(value??"—"))));tbody.append(line)});
 table.append(tbody);return table;
}
function moduleNotice(text){const el=moduleNode("div","module-notice",text);document.getElementById("moduleContent").append(el)}
async function renderModule(page){
 const ar=lang==="ar",content=document.getElementById("moduleContent");
 content.replaceChildren();
 const titles={services:ar?"الخدمات":"Services",storage:ar?"التخزين":"Storage",containers:ar?"الحاويات":"Containers",terminal:ar?"الطرفية":"Terminal",security:ar?"الأمان":"Security",settings:ar?"الإعدادات":"Settings"};
 const descriptions={services:ar?"اكتشاف الخدمات يعتمد على مدير التشغيل الموجود في توزيعة Linux.":"Service discovery depends on the init system available in the Linux distro.",storage:ar?"أنظمة الملفات ونقاط الربط التي يراها LinuxCore.":"Filesystems and mount points visible to LinuxCore.",containers:ar?"لن نفترض وجود Docker أو Podman قبل فحص البيئة الفعلية.":"Docker or Podman availability will not be assumed before checking the target environment.",terminal:ar?"الطرفية غير مفعلة حفاظًا على أمان لوحة التحكم.":"The terminal is intentionally disabled to keep the dashboard safe.",security:ar?"حدود الأمان الحالية للمشروع.":"Current security boundaries for this project.",settings:ar?"حالة التكامل والإعدادات المحلية.":"Integration status and local configuration."};
 document.getElementById("moduleTitle").textContent=titles[page]||page;
 document.getElementById("moduleDescription").textContent=descriptions[page]||"";
 const refresh=document.getElementById("moduleRefresh");refresh.textContent=ar?"تحديث":"Refresh";refresh.onclick=()=>renderModule(page);
 if(page==="terminal"){moduleNotice(ar?"الوصول للطرفية غير متاح. لا توجد واجهة لتنفيذ أوامر shell، ولن نضيفها قبل تصميم صلاحيات ومصادقة وعزل مناسب.":"Terminal access is unavailable. No shell execution endpoint exists; it will remain disabled until proper authentication, permissions and isolation are designed.");return}
 if(page==="services"){moduleNotice(ar?"تكامل اكتشاف الخدمات مؤجل لحين معرفة مدير التشغيل الفعلي داخل Linux (systemd أو OpenRC أو غيره).":"Service discovery is pending until the target Linux init system (systemd, OpenRC, or another manager) is identified.");return}
 if(page==="containers"){moduleNotice(ar?"اكتشاف الحاويات مؤجل. لن نفترض أن Docker أو Podman يعملان داخل بيئة Linux بدون Root على الهاتف.":"Container discovery is pending. Docker or Podman will not be assumed to work inside the phone's rootless Linux environment.");return}
 if(page==="security"){
  [["API binding",ar?"127.0.0.1 فقط":"127.0.0.1 only"],["System access",ar?"قراءة فقط":"Read-only"],["AI permissions",ar?"اقتراح وتحليل فقط":"Advisory only"],["Remote pairing",ar?"غير منفذ":"Not implemented"],["Shell execution",ar?"غير متاح":"Unavailable"]].forEach(([k,v])=>{const row=moduleNode("div","module-stat");row.append(moduleNode("b","",k),moduleNode("span","",v));content.append(row)});return;
 }
 if(page==="settings"){
  try{const r=await fetch("http://127.0.0.1:8000/api/v1/ai/status");const d=await r.json();[["AI provider","DeepSeek"],["Model",d.model],["API key",d.configured?(ar?"مُعد":"Configured"):(ar?"غير مُعد":"Not configured")],["AI mode",d.mode]].forEach(([k,v])=>{const row=moduleNode("div","module-stat");row.append(moduleNode("b","",k),moduleNode("span","",String(v)));content.append(row)})}
  catch{moduleNotice(ar?"تعذر الاتصال بالـ Backend المحلي.":"Could not reach the local backend.")}
  moduleNotice(ar?"يُحفظ مفتاح DeepSeek في backend/.env فقط، ولا يوضع في ملفات الواجهة أو GitHub.":"Store the DeepSeek key only in backend/.env, never in frontend files or GitHub.");return;
 }
 const endpoints={storage:"storage",processes:"processes",network:"network"};
 const endpoint=endpoints[page];
 if(!endpoint){moduleNotice(ar?"هذا القسم غير متاح.":"This section is unavailable.");return}
 try{
  const response=await fetch("http://127.0.0.1:8000/api/v1/"+endpoint,{cache:"no-store"});
  if(!response.ok)throw new Error("API");
  const data=await response.json();
  if(page==="storage")content.append(moduleTable([ar?"نقطة الربط":"Mount",ar?"نظام الملفات":"Filesystem",ar?"الإجمالي GB":"Total GB",ar?"المستخدم GB":"Used GB",ar?"المتاح GB":"Free GB",ar?"الاستخدام %":"Usage %"],data.items.map(x=>[x.mountpoint,x.filesystem,x.total_gb,x.used_gb,x.free_gb,x.percent+"%"])));
  if(page==="processes")content.append(moduleTable([ar?"العملية":"Process","PID",ar?"الحالة":"Status",ar?"استهلاك الذاكرة":"Memory %"],data.items.map(x=>[x.name,x.pid,x.status,x.memory_percent+"%"])));
  if(page==="network")content.append(moduleTable([ar?"الواجهة":"Interface",ar?"الحالة":"Link",ar?"استقبال MB":"Received MB",ar?"إرسال MB":"Sent MB",ar?"الحزم المستلمة":"RX packets",ar?"الحزم المرسلة":"TX packets"],data.interfaces.map(x=>[x.name,x.is_up?(ar?"نشط":"Up"):(ar?"متوقف":"Down"),(x.bytes_recv/1048576).toFixed(2),(x.bytes_sent/1048576).toFixed(2),x.packets_recv,x.packets_sent])));
  if(!data.items?.length&&!data.interfaces?.length)moduleNotice(ar?"لا توجد بيانات متاحة في البيئة الحالية.":"No data is available in the current environment.");
 }catch{moduleNotice(ar?"السيرفر غير متصل. شغّل LinuxCore Backend لعرض البيانات الحقيقية.":"Host is not connected. Start the LinuxCore backend to load live data.");}
}
function tick(){document.getElementById("clock").textContent=new Date().toLocaleTimeString(lang==="ar"?"ar-EG":"en-GB")}
applyLanguage();tick();setInterval(tick,1000);
function formatUptime(seconds){const total=Math.max(0,Math.floor(Number(seconds)||0));const days=Math.floor(total/86400),hours=Math.floor((total%86400)/3600),minutes=Math.floor((total%3600)/60);return lang==="ar"?`${days} يوم · ${hours} س · ${minutes} د`:`${days}d ${hours}h ${minutes}m`}
function setMetric(id,value){const n=Math.max(0,Math.min(100,Number(value)||0));document.getElementById(id+"Val").textContent=Math.round(n);document.getElementById(id+"Bar").style.width=n+"%"}
function rate(bytes,oldBytes,seconds){if(oldBytes===null||seconds<=0)return 0;return Math.max(0,(bytes-oldBytes)/seconds/1024/1024)}
async function loadMetrics(showToast=false){
 try{
  const response=await fetch("http://127.0.0.1:8000/api/v1/metrics",{cache:"no-store",signal:AbortSignal.timeout(2500)});
  if(!response.ok)throw new Error("API unavailable");
  const d=await response.json();
  setMetric("cpu",d.cpu_percent);setMetric("ram",d.memory_percent);setMetric("disk",d.disk_percent);
  document.getElementById("cpuMeta").textContent=d.cpu_count+" cores";
  document.getElementById("ramMeta").textContent=d.memory_used_gb+" / "+d.memory_total_gb+" GB";
  document.getElementById("diskMeta").textContent=d.disk_used_gb+" / "+d.disk_total_gb+" GB";
  document.getElementById("hostName").textContent=d.hostname||"Linux host";
  document.getElementById("hostPlatform").textContent=d.platform||"Linux";
  document.getElementById("hostUptime").textContent=formatUptime(d.uptime_seconds);
  const now=Date.now();
  if(previousNetwork){const seconds=(now-previousNetwork.time)/1000;document.getElementById("downVal").innerHTML=rate(d.network_bytes_recv,previousNetwork.recv,seconds).toFixed(2)+' <small>MB/s</small>';document.getElementById("upVal").innerHTML=rate(d.network_bytes_sent,previousNetwork.sent,seconds).toFixed(2)+' <small>MB/s</small>'}
  previousNetwork={time:now,recv:d.network_bytes_recv,sent:d.network_bytes_sent};
  document.querySelector(".notice-status").textContent="LIVE";document.querySelector(".notice-status").style.color="var(--green)";document.querySelector(".notice").style.borderColor="#28694f88";document.querySelector(".notice-icon").textContent="✓";document.querySelector(".notice b").textContent=lang==="ar"?"متصل بالسيرفر":"Host connected";document.querySelector(".notice span:nth-child(2)").lastChild.textContent=lang==="ar"?" المؤشرات مأخوذة من خادم Linux المتصل.":" Live metrics from connected Linux host.";document.querySelector(".pulse").style.background="var(--green)";document.querySelector(".connection b").textContent=lang==="ar"?"متصل":"Connected";document.querySelector(".connection small").textContent=d.hostname;
  if(showToast)toast(lang==="ar"?"تم تحديث بيانات السيرفر":"Host metrics updated");
 }catch(error){document.querySelector(".notice-status").textContent="NOT CONNECTED";document.querySelector(".notice-status").style.color="var(--amber)";document.querySelector(".pulse").style.background="var(--amber)";document.querySelector(".connection b").textContent=lang==="ar"?"وضع تجريبي":"Demo mode";document.querySelector(".connection small").textContent=lang==="ar"?"في انتظار اتصال السيرفر":"Awaiting server connection";document.getElementById("hostName").textContent="—";document.getElementById("hostPlatform").textContent="—";document.getElementById("hostUptime").textContent="—";if(showToast)toast(lang==="ar"?"السيرفر غير متصل؛ البيانات تجريبية":"Host unavailable; showing preview data")}
}
loadMetrics();setInterval(()=>loadMetrics(),10000);
function addMessage(role,text){const node=document.createElement("div");node.className="ai-message "+role;const who=document.createElement("span");who.className="ai-who";who.textContent=role==="user"?(lang==="ar"?"أنت":"YOU"):"LINUXCORE AI";const body=document.createElement("p");body.textContent=text;node.append(who,body);document.getElementById("aiMessages").append(node);document.getElementById("aiMessages").scrollTop=document.getElementById("aiMessages").scrollHeight}
async function checkAIStatus(){const status=document.getElementById("aiStatus");try{const r=await fetch("http://127.0.0.1:8000/api/v1/ai/status",{cache:"no-store"});if(!r.ok)throw new Error();const data=await r.json();aiConfigured=!!data.configured;status.textContent=aiConfigured?t("aiReady"):t("aiOffline");status.className="ai-status "+(aiConfigured?"ready":"offline");document.getElementById("aiSetup").hidden=aiConfigured}catch{aiConfigured=false;status.textContent=t("aiOffline");status.className="ai-status offline";document.getElementById("aiSetup").hidden=false}}
async function sendAI(){if(aiBusy)return;const input=document.getElementById("aiInput");const content=input.value.trim();if(!content){toast(t("aiEmpty"));return}if(!aiConfigured){toast(t("aiUnavailable"));return}input.value="";aiHistory.push({role:"user",content});if(aiHistory.length>20)aiHistory.splice(0,aiHistory.length-20);addMessage("user",content);aiBusy=true;const send=document.getElementById("aiSend");send.disabled=true;send.textContent=t("aiThinking");const waiting=document.createElement("div");waiting.className="ai-message assistant pending";waiting.textContent=t("aiThinking");document.getElementById("aiMessages").append(waiting);try{const response=await fetch("http://127.0.0.1:8000/api/v1/ai/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({messages:aiHistory,include_server_context:document.getElementById("aiIncludeContext").checked}),signal:AbortSignal.timeout(40000)});const data=await response.json();if(!response.ok)throw new Error(data.detail||"AI request failed");waiting.remove();aiHistory.push({role:"assistant",content:data.answer});addMessage("assistant",data.answer)}catch(error){waiting.remove();aiHistory.pop();toast(error.message||t("aiError"))}finally{aiBusy=false;send.disabled=false;send.textContent=t("aiSend");input.focus()}}
document.getElementById("aiSend").addEventListener("click",sendAI);
document.getElementById("aiInput").addEventListener("keydown",event=>{if(event.key==="Enter"&&!event.shiftKey){event.preventDefault();sendAI()}});
