"use strict";

const translations = {
  en: {
    workspace:"WORKSPACE", overview:"Overview", hostName:"HOSTNAME", platform:"PLATFORM", uptime:"UPTIME",
    services:"Services", storage:"Storage", processes:"Processes", networkPage:"Network", containers:"Containers",
    terminal:"Terminal", security:"Security", recovery:"Recovery", ai:"AI Assistant", settings:"Settings",
    demoMode:"Demo mode", awaiting:"Awaiting server connection", systemStandby:"SYSTEM STANDBY", systemLive:"LIVE",
    hostConnected:"Host connected", preview:"Preview environment", previewText:"Live metrics appear when a Linux host is connected. No sample values are shown.",
    notConnected:"NOT CONNECTED", cpuUsage:"CPU USAGE", memory:"MEMORY", processorLoad:"Logical cores",
    memoryUsed:"Memory used", diskUsed:"Disk used", network:"NETWORK", download:"↓ DOWNLOAD", upload:"↑ UPLOAD",
    interface:"Interface", networkAggregate:"All interfaces", controlCenter:"CONTROL CENTER", overviewTitle:"Server overview",
    overviewSub:"Monitor your Linux environment from one command center.", refresh:"Refresh",
    systemHealth:"SYSTEM HEALTH", serviceStatus:"Service status", viewAll:"VIEW ALL ↗", monitoring:"MONITORING",
    recentActivity:"Recent activity", backupCompleted:"Backup completed", serviceRestarted:"Service restarted",
    securityScan:"Security scan finished", noIssues:"No issues detected", demoActivity:"Illustrative activity · not live system events",
    footerNote:"Designed for secure, local-first server administration.", serviceDiscoveryPending:"Service discovery is pending identification of the Linux init system.",
    serviceDescription:"Manage only services owned by your unprivileged systemd user session.",
    containersDescription:"Inspect and control containers only through an accessible rootless Podman or Docker runtime.",
    terminalDisabled:"Run a fixed set of read-only diagnostic commands. Arbitrary shell input is intentionally unavailable.",
    securityDescription:"Current security boundaries for this project.", recoveryDescription:"Check LinuxCore and safely restart only its own local services.", settingsDescription:"Local integration and configuration status.",
    noData:"No data is available in the current environment.", unavailableNetwork:"Network counters are restricted by this Linux environment.",
    moduleRefresh:"Refresh", apiUnavailable:"The local LinuxCore backend is unavailable. Start the backend and try again.",
    aiTitle:"DeepSeek AI Assistant", aiSub:"Ask about Linux, programming, or analyze your connected host.",
    aiReady:"AI READY", aiOffline:"AI NOT CONFIGURED", aiWelcome:"Hello. I can explain Linux, help with programming, and analyze read-only host metrics when you choose to share them.",
    aiPlaceholder:"Ask LinuxCore AI something...", aiSend:"Send", aiContext:"Include aggregate host metrics in this request",
    aiPrivacy:"If enabled, aggregate CPU, memory, disk, uptime, hostname, platform and a limited storage summary are shared. Process command lines, environment variables and secrets are excluded.",
    aiThinking:"Thinking...", aiSetup:"Add DEEPSEEK_API_KEY to the backend environment to enable the assistant.",
    aiError:"The assistant could not answer. Check the backend and API configuration.", aiEmpty:"Write a message first.",
    aiUnavailable:"AI assistant is unavailable until its backend is configured.", cores:"cores", networkNA:"N/A"
  },
  ar: {
    workspace:"مساحة العمل", overview:"نظرة عامة", hostName:"اسم المضيف", platform:"النظام والمنصة", uptime:"مدة التشغيل",
    services:"الخدمات", storage:"التخزين", processes:"العمليات", networkPage:"الشبكة", containers:"الحاويات",
    terminal:"الطرفية", security:"الأمان", recovery:"الاستعادة", ai:"المساعد الذكي", settings:"الإعدادات",
    demoMode:"وضع المعاينة", awaiting:"في انتظار اتصال السيرفر", systemStandby:"النظام في وضع الاستعداد", systemLive:"مباشر",
    hostConnected:"متصل بالسيرفر", preview:"بيئة معاينة", previewText:"ستظهر المؤشرات الحقيقية عند اتصال خادم Linux. لا يتم عرض أرقام تجريبية.",
    notConnected:"غير متصل", cpuUsage:"استخدام المعالج", memory:"الذاكرة", processorLoad:"الأنوية المنطقية",
    memoryUsed:"الذاكرة المستخدمة", diskUsed:"المساحة المستخدمة", network:"الشبكة", download:"↓ تنزيل", upload:"↑ رفع",
    interface:"واجهة الاتصال", networkAggregate:"كل الواجهات", controlCenter:"مركز التحكم", overviewTitle:"نظرة عامة على السيرفر",
    overviewSub:"راقب بيئة Linux من مركز تحكم واحد.", refresh:"تحديث",
    systemHealth:"حالة النظام", serviceStatus:"حالة الخدمات", viewAll:"عرض الكل ↗", monitoring:"المراقبة",
    recentActivity:"النشاط الأخير", backupCompleted:"اكتمل النسخ الاحتياطي", serviceRestarted:"أُعيد تشغيل الخدمة",
    securityScan:"اكتمل فحص الأمان", noIssues:"لم يتم اكتشاف مشكلات", demoActivity:"نشاط توضيحي · ليس أحداثًا مباشرة",
    footerNote:"مصممة لإدارة السيرفرات محليًا وبشكل آمن.", serviceDiscoveryPending:"اكتشاف الخدمات مؤجل لحين تحديد مدير التشغيل داخل Linux.",
    serviceDescription:"إدارة خدمات جلسة systemd الخاصة بالمستخدم فقط، من غير صلاحيات Root.",
    containersDescription:"عرض وإدارة الحاويات من خلال Podman أو Docker بنمط Rootless فقط.",
    terminalDisabled:"تشغيل مجموعة محددة من أوامر التشخيص للقراءة فقط. تنفيذ أوامر Shell عشوائية غير متاح.",
    securityDescription:"حدود الأمان الحالية للمشروع.", recoveryDescription:"فحص LinuxCore وإعادة تشغيل خدماته المحلية فقط بشكل آمن.", settingsDescription:"حالة التكامل والإعدادات المحلية.",
    noData:"لا توجد بيانات متاحة في البيئة الحالية.", unavailableNetwork:"عدادات الشبكة محجوبة بواسطة بيئة Linux الحالية.",
    moduleRefresh:"تحديث", apiUnavailable:"تعذر الاتصال بـ LinuxCore Backend المحلي. شغّل السيرفر وحاول مرة أخرى.",
    aiTitle:"مساعد DeepSeek الذكي", aiSub:"اسأل عن Linux والبرمجة أو اطلب تحليل بيانات السيرفر المتصل.",
    aiReady:"الذكاء الاصطناعي جاهز", aiOffline:"الذكاء الاصطناعي غير مُعد",
    aiWelcome:"أهلًا. أقدر أشرح Linux وأساعدك في البرمجة وأحلل مؤشرات السيرفر للقراءة فقط لما تختار مشاركتها.",
    aiPlaceholder:"اسأل LinuxCore AI...", aiSend:"إرسال", aiContext:"إرفاق مؤشرات السيرفر المجمعة في الطلب ده",
    aiPrivacy:"عند التفعيل، يتم إرسال مؤشرات المعالج والذاكرة والتخزين ومدة التشغيل واسم المضيف والمنصة وملخص محدود للتخزين. لا نرسل سطور أوامر العمليات أو متغيرات البيئة أو الأسرار.",
    aiThinking:"جاري التفكير...", aiSetup:"أضف DEEPSEEK_API_KEY إلى بيئة تشغيل Backend لتفعيل المساعد.",
    aiError:"المساعد لم يتمكن من الرد. راجع إعدادات Backend وAPI.", aiEmpty:"اكتب رسالة الأول.",
    aiUnavailable:"المساعد غير متاح حتى يتم إعداد Backend.", cores:"أنوية", networkNA:"غير متاح"
  }
};

let lang = "en";
try {
  const saved = localStorage.getItem("linuxcore-lang");
  if (saved === "ar" || saved === "en") lang = saved;
} catch (_) {}

let currentPage = "overview";
let hostConnected = false;
let metricsRequestId = 0;
let moduleRequestId = 0;
let previousNetwork = null;
let aiConfigured = false;
let aiBusy = false;
const aiHistory = [];

function t(key) {
  return (translations[lang] && translations[lang][key]) || key;
}

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const element = byId(id);
  if (element) element.textContent = value;
}

function toast(message) {
  const element = byId("toast");
  if (!element) return;
  element.textContent = message;
  element.classList.add("show");
  window.setTimeout(() => element.classList.remove("show"), 2400);
}

function applyLanguage() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (translations[lang][key]) element.textContent = t(key);
  });
  setText("langBtn", lang === "en" ? "عربي" : "English");
  if (byId("langBtn")) byId("langBtn").setAttribute("aria-label", lang === "en" ? "Switch language" : "تغيير اللغة");
  setText("systemStatus", hostConnected ? t("systemLive") : t("systemStandby"));
  setText("pageTitle", currentPage === "ai" ? t("ai") : (translations[lang][currentPage] || currentPage));
  if (byId("aiInput")) byId("aiInput").placeholder = t("aiPlaceholder");
  setText("aiSend", t("aiSend"));
  setText("aiContextLabel", t("aiContext"));
  setText("aiPrivacy", t("aiPrivacy"));
  setText("aiTitle", t("aiTitle"));
  setText("aiSub", t("aiSub"));
  if (currentPage !== "overview" && currentPage !== "ai") renderModule(currentPage);
}

function setConnectionState(connected) {
  hostConnected = connected;
  const status = byId("noticeStatus");
  const notice = document.querySelector(".notice");
  const icon = byId("noticeIcon");
  const title = byId("noticeTitle");
  const message = byId("noticeMessage");
  const live = byId("systemStatus");
  const pulse = document.querySelector(".pulse");
  const liveDot = document.querySelector(".live-tag i");
  const connectionTitle = document.querySelector(".connection b");
  const connectionDetail = document.querySelector(".connection small");

  if (status) {
    status.textContent = connected ? "LIVE" : t("notConnected");
    status.style.color = connected ? "var(--green)" : "var(--amber)";
  }
  if (notice) notice.style.borderColor = connected ? "#28694f88" : "";
  if (icon) icon.textContent = connected ? "✓" : "i";
  if (title) title.textContent = connected ? t("hostConnected") : t("preview");
  if (message) message.textContent = connected
    ? (lang === "ar" ? "المؤشرات مأخوذة من خادم Linux المتصل." : "Live metrics from the connected Linux host.")
    : t("previewText");
  if (live) {
    live.textContent = connected ? t("systemLive") : t("systemStandby");
    live.dataset.state = connected ? "connected" : "disconnected";
  }
  if (pulse) pulse.style.background = connected ? "var(--green)" : "var(--amber)";
  if (liveDot) liveDot.style.background = connected ? "var(--green)" : "var(--amber)";
  if (connectionTitle) connectionTitle.textContent = connected
    ? (lang === "ar" ? "متصل" : "Connected") : t("demoMode");
  if (connectionDetail) connectionDetail.textContent = connected
    ? (byId("hostName") ? byId("hostName").textContent : "Linux host") : t("awaiting");
}

function setMetric(id, value) {
  const numeric = Number(value);
  const valid = value !== null && value !== undefined && value !== "" && Number.isFinite(numeric) && numeric >= 0 && numeric <= 100;
  const valueElement = byId(id + "Val");
  const barElement = byId(id + "Bar");
  if (valueElement) valueElement.textContent = valid ? String(Math.round(numeric)) : "—";
  if (barElement) barElement.style.width = valid ? numeric + "%" : "0%";
  return valid;
}

function formatUptime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return lang === "ar"
    ? days + " يوم · " + hours + " س · " + minutes + " د"
    : days + "d " + hours + "h " + minutes + "m";
}

function rate(bytes, oldBytes, seconds) {
  if (!Number.isFinite(bytes) || !Number.isFinite(oldBytes) || seconds <= 0) return 0;
  return Math.max(0, (bytes - oldBytes) / seconds / 1048576);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options || {});
  if (!response.ok) throw new Error("HTTP " + response.status);
  return response.json();
}

async function loadMetrics(showToast) {
  const requestId = ++metricsRequestId;
  try {
    const data = await fetchJson("http://127.0.0.1:8000/api/v1/metrics", {
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });
    if (requestId !== metricsRequestId) return;

    setMetric("cpu", data.cpu_percent);
    setMetric("ram", data.memory_percent);
    setMetric("disk", data.disk_percent);

    const cpuCount = Number(data.cpu_count);
    setText("cpuMeta", Number.isInteger(cpuCount) && cpuCount > 0
      ? cpuCount + " " + t("cores") : "—");
    setText("ramMeta", Number.isFinite(Number(data.memory_used_gb)) && Number.isFinite(Number(data.memory_total_gb))
      ? Number(data.memory_used_gb).toFixed(2) + " / " + Number(data.memory_total_gb).toFixed(2) + " GB" : "—");
    setText("diskMeta", Number.isFinite(Number(data.disk_used_gb)) && Number.isFinite(Number(data.disk_total_gb))
      ? Number(data.disk_used_gb).toFixed(2) + " / " + Number(data.disk_total_gb).toFixed(2) + " GB" : "—");
    setText("hostName", data.hostname || "Linux host");
    setText("hostPlatform", data.platform || "Linux");
    setText("hostUptime", formatUptime(data.uptime_seconds));

    const now = Date.now();
    if (data.network_available === true &&
        Number.isFinite(data.network_bytes_recv) &&
        Number.isFinite(data.network_bytes_sent)) {
      if (previousNetwork) {
        const seconds = (now - previousNetwork.time) / 1000;
        setText("downVal", rate(data.network_bytes_recv, previousNetwork.recv, seconds).toFixed(2) + " MB/s");
        setText("upVal", rate(data.network_bytes_sent, previousNetwork.sent, seconds).toFixed(2) + " MB/s");
      } else {
        setText("downVal", "—");
        setText("upVal", "—");
      }
      previousNetwork = {
        time: now,
        recv: data.network_bytes_recv,
        sent: data.network_bytes_sent
      };
    } else {
      previousNetwork = null;
      setText("downVal", t("networkNA"));
      setText("upVal", t("networkNA"));
    }

    setText("networkInterface", data.network_available ? (data.network_interface === "aggregate" ? t("networkAggregate") : (data.network_interface || "—")) : t("networkNA"));
    setConnectionState(true);
    if (showToast) toast(lang === "ar" ? "تم تحديث بيانات السيرفر" : "Host metrics updated");
  } catch (error) {
    if (requestId !== metricsRequestId) return;
    previousNetwork = null;
    ["cpu", "ram", "disk"].forEach((id) => setMetric(id, null));
    ["cpuMeta", "ramMeta", "diskMeta", "hostName", "hostPlatform", "hostUptime"].forEach((id) => setText(id, "—"));
    setText("downVal", t("networkNA"));
    setText("upVal", t("networkNA"));
    setText("networkInterface", t("networkNA"));
    setConnectionState(false);
    if (showToast) toast(t("apiUnavailable"));
  }
}

function moduleNode(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = String(content);
  return element;
}

function moduleTable(headers, rows) {
  const table = moduleNode("table", "module-table");
  const head = moduleNode("thead");
  const headRow = moduleNode("tr");
  headers.forEach((header) => headRow.append(moduleNode("th", "", header)));
  head.append(headRow);
  table.append(head);

  const body = moduleNode("tbody");
  rows.forEach((row) => {
    const line = moduleNode("tr");
    row.forEach((value) => line.append(moduleNode("td", "", value == null ? "—" : value)));
    body.append(line);
  });
  table.append(body);
  return table;
}

function moduleNotice(message) {
  const content = byId("moduleContent");
  if (content) content.append(moduleNode("div", "module-notice", message));
}

function navigate(page, button) {
  currentPage = page;
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.remove("active");
    item.removeAttribute("aria-current");
  });
  if (button) {
    button.classList.add("active");
    button.setAttribute("aria-current", "page");
  }

  const isAI = page === "ai";
  const isModule = page !== "overview" && !isAI;
  if (byId("aiWorkspace")) byId("aiWorkspace").hidden = !isAI;
  if (byId("moduleWorkspace")) byId("moduleWorkspace").hidden = !isModule;
  [".page-head", ".notice", ".metric-grid", ".system-facts", ".content-grid"].forEach((selector) => {
    document.querySelectorAll(selector).forEach((element) => { element.hidden = isAI || isModule; });
  });
  const footer = document.querySelector(".footer");
  if (footer) footer.hidden = isAI;
  setText("pageTitle", isAI ? t("ai") : (translations[lang][page] || page));

  if (isAI) checkAIStatus();
  else if (isModule) renderModule(page);
  else loadMetrics(false);
}

function moduleActionButton(label, callback) {
  const button = moduleNode("button", "outline-btn", label);
  button.type = "button";
  button.addEventListener("click", callback);
  return button;
}

async function postJson(url, body, timeoutMs) {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs || 12000)
  });
}

async function renderModule(page) {
  const requestId = ++moduleRequestId;
  const isArabic = lang === "ar";
  const content = byId("moduleContent");
  if (!content) return;
  content.replaceChildren();

  const titles = {
    services: t("services"), storage: t("storage"), processes: t("processes"),
    network: t("networkPage"), containers: t("containers"), terminal: t("terminal"),
    security: t("security"), recovery: t("recovery"), settings: t("settings")
  };
  const descriptions = {
    services: t("serviceDescription"), containers: t("containersDescription"),
    terminal: t("terminalDisabled"), security: t("securityDescription"),
    recovery: t("recoveryDescription"), settings: t("settingsDescription")
  };
  setText("moduleTitle", titles[page] || page);
  setText("moduleDescription", descriptions[page] || "");
  const refresh = byId("moduleRefresh");
  if (refresh) {
    refresh.textContent = "↻ " + t("moduleRefresh");
    refresh.onclick = () => renderModule(page);
  }

  if (page === "security") {
    const rows = [
      ["API binding", "127.0.0.1 only"],
      ["Service control", "systemd --user only"],
      ["Container control", "Rootless runtime only"],
      ["Terminal", "Allowlisted read-only diagnostics"],
      ["AI permissions", "Advisory only"],
      ["Android / system root", "No access"]
    ];
    rows.forEach(([key, value]) => {
      const row = moduleNode("div", "module-stat");
      row.append(moduleNode("b", "", key), moduleNode("span", "", value));
      content.append(row);
    });
    return;
  }

  try {
    if (page === "services") {
      const data = await fetchJson("http://127.0.0.1:8000/api/v1/services", {
        cache: "no-store", signal: AbortSignal.timeout(10000)
      });
      if (requestId !== moduleRequestId || currentPage !== page) return;
      if (!data.available) { moduleNotice(data.reason || t("noData")); return; }
      const items = Array.isArray(data.items) ? data.items : [];
      moduleNotice((isArabic ? "مدير الخدمات: " : "Service manager: ") + data.manager);
      if (!items.length) { moduleNotice(t("noData")); return; }
      items.forEach((item) => {
        const row = moduleNode("div", "operation-row");
        const details = moduleNode("div", "operation-details");
        details.append(moduleNode("b", "", item.unit),
          moduleNode("small", "", [item.active, item.sub, item.description].filter(Boolean).join(" · ")));
        const controls = moduleNode("div", "operation-actions");
        ["start", "stop", "restart"].forEach((action) => {
          controls.append(moduleActionButton(
            isArabic ? ({start:"تشغيل",stop:"إيقاف",restart:"إعادة تشغيل"}[action]) : action,
            async () => {
              try {
                await postJson("http://127.0.0.1:8000/api/v1/services/" +
                  encodeURIComponent(item.unit) + "/action", {action}, 25000);
                toast(isArabic ? "تم إرسال الإجراء للخدمة" : "Service action completed");
                renderModule("services");
              } catch (error) { toast(error.message || t("apiUnavailable")); }
            }
          ));
        });
        row.append(details, controls);
        content.append(row);
      });
      return;
    }

    if (page === "containers") {
      const data = await fetchJson("http://127.0.0.1:8000/api/v1/containers", {
        cache: "no-store", signal: AbortSignal.timeout(12000)
      });
      if (requestId !== moduleRequestId || currentPage !== page) return;
      if (!data.available) { moduleNotice(data.reason || t("noData")); return; }
      moduleNotice((isArabic ? "بيئة الحاويات: " : "Container runtime: ") + data.runtime);
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) { moduleNotice(t("noData")); return; }
      items.forEach((item) => {
        const row = moduleNode("div", "operation-row");
        const details = moduleNode("div", "operation-details");
        details.append(moduleNode("b", "", item.name || item.id),
          moduleNode("small", "", [item.image, item.state, item.status].filter(Boolean).join(" · ")));
        const controls = moduleNode("div", "operation-actions");
        ["start", "stop", "restart"].forEach((action) => {
          controls.append(moduleActionButton(isArabic
            ? ({start:"تشغيل",stop:"إيقاف",restart:"إعادة تشغيل"}[action]) : action,
          async () => {
            try {
              await postJson("http://127.0.0.1:8000/api/v1/containers/" +
                encodeURIComponent(item.id || item.name) + "/action", {action}, 35000);
              toast(isArabic ? "تم تنفيذ الإجراء" : "Container action completed");
              renderModule("containers");
            } catch (error) { toast(error.message || t("apiUnavailable")); }
          }));
        });
        row.append(details, controls);
        content.append(row);
      });
      return;
    }

    if (page === "terminal") {
      moduleNotice(t("terminalDisabled"));
      const output = moduleNode("pre", "terminal-output",
        isArabic ? "اختار أمر تشخيص من الأزرار لعرض النتيجة هنا." : "Choose a diagnostic preset to view its output here.");
      const actions = moduleNode("div", "terminal-actions");
      const labels = {
        pwd: isArabic ? "المسار الحالي" : "Working directory",
        system: isArabic ? "معلومات النظام" : "System info",
        storage: isArabic ? "التخزين" : "Storage",
        memory: isArabic ? "الذاكرة" : "Memory",
        uptime: isArabic ? "مدة التشغيل" : "Uptime",
        processes: isArabic ? "العمليات" : "Processes"
      };
      Object.keys(labels).forEach((command) => {
        actions.append(moduleActionButton(labels[command], async () => {
          output.textContent = isArabic ? "جاري التنفيذ..." : "Running diagnostic...";
          try {
            const data = await postJson("http://127.0.0.1:8000/api/v1/terminal/run", {command}, 12000);
            output.textContent = data.output || (isArabic ? "لا يوجد ناتج." : "No output.");
          } catch (error) { output.textContent = error.message || t("apiUnavailable"); }
        }));
      });
      content.append(actions, output);
      return;
    }

    if (page === "recovery") {
      const data = await fetchJson("http://127.0.0.1:8000/api/v1/recovery/check", {
        cache: "no-store", signal: AbortSignal.timeout(10000)
      });
      if (requestId !== moduleRequestId || currentPage !== page) return;
      const summary = moduleNode("div", "module-stat");
      summary.append(moduleNode("b", "", isArabic ? "نتيجة الفحص" : "Health check"),
        moduleNode("span", "", data.healthy ? (isArabic ? "سليم" : "Healthy") : (isArabic ? "يحتاج مراجعة" : "Needs attention")));
      content.append(summary);
      (data.files || []).forEach((item) => {
        const row = moduleNode("div", "module-stat");
        row.append(moduleNode("b", "", item.path),
          moduleNode("span", "", item.present ? "OK" : "MISSING"));
        content.append(row);
      });
      const deps = moduleNode("div", "module-stat");
      deps.append(moduleNode("b", "", isArabic ? "اعتماديات Python" : "Python dependencies"),
        moduleNode("span", "", data.dependencies ? "OK" : "MISSING"));
      content.append(deps);
      moduleNotice(isArabic
        ? "الاستعادة تحفظ نسخة من backend/.env ثم تتحقق من ملفات المشروع وتشغّل خدمات LinuxCore المحلية فقط. لا تغيّر إعدادات Android أو خدمات النظام."
        : "Recovery backs up backend/.env, validates project files, and starts only LinuxCore local services. It does not change Android or system settings.");
      content.append(moduleActionButton(isArabic ? "ابدأ الفحص والاستعادة" : "Run safe recovery", async (event) => {
        const button = event.currentTarget;
        button.disabled = true;
        try {
          const result = await postJson("http://127.0.0.1:8000/api/v1/recovery/run", {}, 70000);
          moduleNotice(result.output || (isArabic ? "اكتملت الاستعادة." : "Recovery completed."));
          toast(isArabic ? "اكتملت الاستعادة" : "Recovery completed");
        } catch (error) {
          moduleNotice(error.message || t("apiUnavailable"));
        } finally { button.disabled = false; }
      }));
      return;
    }

    if (page === "settings") {
      const data = await fetchJson("http://127.0.0.1:8000/api/v1/ai/status", {
        cache: "no-store", signal: AbortSignal.timeout(8000)
      });
      if (requestId !== moduleRequestId || currentPage !== page) return;
      [
        ["AI provider", data.provider || "DeepSeek"],
        ["Model", data.model || "—"],
        ["API key", data.configured ? (isArabic ? "مُعد" : "Configured") : (isArabic ? "غير مُعد" : "Not configured")],
        ["AI mode", data.mode || "—"]
      ].forEach(([key, value]) => {
        const row = moduleNode("div", "module-stat");
        row.append(moduleNode("b", "", key), moduleNode("span", "", value));
        content.append(row);
      });
      moduleNotice(isArabic
        ? "يُحفظ مفتاح DeepSeek في backend/.env فقط، ولا يوضع في ملفات الواجهة أو GitHub."
        : "Store the DeepSeek key only in backend/.env, never in frontend files or GitHub.");
      return;
    }

    const endpoints = { storage: "storage", processes: "processes", network: "network" };
    const endpoint = endpoints[page];
    if (!endpoint) { moduleNotice(t("noData")); return; }
    const data = await fetchJson("http://127.0.0.1:8000/api/v1/" + endpoint, {
      cache: "no-store", signal: AbortSignal.timeout(8000)
    });
    if (requestId !== moduleRequestId || currentPage !== page) return;
    if (page === "network" && data.available === false) {
      moduleNotice(data.reason || t("unavailableNetwork")); return;
    }
    if (page === "storage") {
      const items = Array.isArray(data.items) ? data.items : [];
      content.append(moduleTable(
        [isArabic ? "نقطة الربط" : "Mount", isArabic ? "نظام الملفات" : "Filesystem",
          "Total GB", "Used GB", "Free GB", "Usage %"],
        items.map((item) => [item.mountpoint, item.filesystem, item.total_gb, item.used_gb, item.free_gb, item.percent + "%"])
      ));
      if (items.length === 0) moduleNotice(t("noData"));
    } else if (page === "processes") {
      const items = Array.isArray(data.items) ? data.items : [];
      content.append(moduleTable(
        [isArabic ? "العملية" : "Process", "PID", isArabic ? "الحالة" : "Status", "Memory %"],
        items.map((item) => [item.name, item.pid, item.status, item.memory_percent + "%"])
      ));
      if (items.length === 0) moduleNotice(t("noData"));
    } else if (page === "network") {
      const interfaces = Array.isArray(data.interfaces) ? data.interfaces : [];
      content.append(moduleTable(
        [isArabic ? "الواجهة" : "Interface", isArabic ? "الحالة" : "Link", "Received MB", "Sent MB", "RX packets", "TX packets"],
        interfaces.map((item) => [
          item.name, item.is_up ? (isArabic ? "نشط" : "Up") : (isArabic ? "متوقف" : "Down"),
          (Number(item.bytes_recv || 0) / 1048576).toFixed(2),
          (Number(item.bytes_sent || 0) / 1048576).toFixed(2),
          item.packets_recv, item.packets_sent
        ])
      ));
      if (interfaces.length === 0) moduleNotice(t("noData"));
    }
  } catch (error) {
    if (requestId === moduleRequestId && currentPage === page) moduleNotice(error.message || t("apiUnavailable"));
  }
}

function addMessage(role, message) {
  const node = moduleNode("div", "ai-message " + role);
  const who = moduleNode("span", "ai-who", role === "user" ? (lang === "ar" ? "أنت" : "YOU") : "LINUXCORE AI");
  const body = moduleNode("p", "", message);
  node.append(who, body);
  const messages = byId("aiMessages");
  if (!messages) return;
  messages.append(node);
  messages.scrollTop = messages.scrollHeight;
}

async function checkAIStatus() {
  const status = byId("aiStatus");
  const setup = byId("aiSetup");
  if (!status || !setup) return;
  try {
    const data = await fetchJson("http://127.0.0.1:8000/api/v1/ai/status", {
      cache: "no-store", signal: AbortSignal.timeout(8000)
    });
    aiConfigured = data.configured === true;
    status.textContent = aiConfigured ? t("aiReady") : t("aiOffline");
    status.className = "ai-status " + (aiConfigured ? "ready" : "offline");
    setup.hidden = aiConfigured;
  } catch (_) {
    aiConfigured = false;
    status.textContent = t("aiOffline");
    status.className = "ai-status offline";
    setup.hidden = false;
  }
}

async function sendAI() {
  if (aiBusy) return;
  const input = byId("aiInput");
  const send = byId("aiSend");
  const messages = byId("aiMessages");
  if (!input || !send || !messages) return;

  const content = input.value.trim();
  if (!content) {
    toast(t("aiEmpty"));
    return;
  }
  if (!aiConfigured) {
    toast(t("aiUnavailable"));
    return;
  }

  const userMessage = { role: "user", content: content };
  aiHistory.push(userMessage);
  while (aiHistory.length > 20) aiHistory.shift();
  const requestMessages = aiHistory.map((item) => ({ role: item.role, content: item.content }));
  input.value = "";
  addMessage("user", content);
  aiBusy = true;
  send.disabled = true;
  send.textContent = t("aiThinking");

  const waiting = moduleNode("div", "ai-message assistant pending", t("aiThinking"));
  messages.append(waiting);

  try {
    const response = await fetch("http://127.0.0.1:8000/api/v1/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: requestMessages,
        include_server_context: !!(byId("aiIncludeContext") && byId("aiIncludeContext").checked)
      }),
      signal: AbortSignal.timeout(40000)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "AI request failed");
    if (typeof data.answer !== "string" || !data.answer.trim()) throw new Error("AI returned an empty response");
    waiting.remove();
    aiHistory.push({ role: "assistant", content: data.answer });
    while (aiHistory.length > 20) aiHistory.shift();
    addMessage("assistant", data.answer);
  } catch (error) {
    waiting.remove();
    const index = aiHistory.lastIndexOf(userMessage);
    if (index !== -1) aiHistory.splice(index, 1);
    toast(error && error.message ? error.message : t("aiError"));
  } finally {
    aiBusy = false;
    send.disabled = false;
    send.textContent = t("aiSend");
    input.focus();
  }
}

byId("langBtn").addEventListener("click", () => {
  lang = lang === "en" ? "ar" : "en";
  try { localStorage.setItem("linuxcore-lang", lang); } catch (_) {}
  applyLanguage();
  if (currentPage === "overview") loadMetrics(false);
});
byId("refreshBtn").addEventListener("click", () => loadMetrics(true));
document.querySelectorAll(".nav-item[data-page]").forEach((button) => {
  button.addEventListener("click", () => navigate(button.dataset.page, button));
});
document.querySelectorAll("[data-go]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    navigate("services", document.querySelector('[data-page="services"]'));
  });
});
byId("aiSend").addEventListener("click", sendAI);
byId("aiInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendAI();
  }
});

function tick() {
  setText("clock", new Date().toLocaleTimeString(lang === "ar" ? "ar-EG" : "en-GB"));
}

applyLanguage();
tick();
loadMetrics(false);
window.setInterval(tick, 1000);
window.setInterval(() => {
  if (currentPage === "overview") loadMetrics(false);
}, 10000);
