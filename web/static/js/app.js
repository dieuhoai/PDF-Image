// Alpine component chính. Quy tắc: không inline script (CSP), mọi chuỗi hiển thị đi qua t().
const LS = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* chế độ riêng tư */ } },
};

async function api(path, opts = {}) {
  let r;
  try {
    r = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    // Server đã tắt hoặc máy vừa ngủ dậy — báo bằng câu người dùng hiểu được.
    throw new Error("__offline__");
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : (Array.isArray(d) ? d.map(e => e.msg).join("; ") : r.statusText));
  }
  return data;
}

const GRID_CARD_W = 300;        // bề rộng ô trong lưới xem trước (ô to hơn sẽ thu nhỏ lại)
const GRID_MAX = 200;           // trần số ô vẽ một lần, tránh treo máy
const DEFAULT_SIZES = ["300x250", "336x280", "728x90", "320x50", "160x600", "300x600"];

function app() {
  return {
    lang: LS.get("lang", "vi"),   // tool dùng trong team Việt Nam → mặc định tiếng Việt
    theme: LS.get("theme", matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
    dict: {},
    catalog: { sizes: [], schemes: [], gradients: [], badges: [], languages: [], animations: [], layouts: [],
               group_by: [], cta_presets: {} },
    step: 1,
    error: "",

    // Bước 1
    sets: [],
    draft: { headline: "", description: "", cta: "", lang: "vi", name: "" },
    editing: null,
    ctaBanned: [],
    ctaOk: false,
    csvErrors: [],
    dragging: false,
    suggestion: null,
    showLibrary: false,
    libItems: [],
    libName: "",

    // Bước 2
    sizes: [...DEFAULT_SIZES],
    sizeFilter: "all",
    customSize: "",
    design: { schemes: ["clean_white"], gradient: "none", animation: "fade", badges: [], layout: "auto",
              cta_style: "text", cta_color: "", cta_pulse: true, ad_format: "banner" },
    previewSize: "300x250",
    previewHtml: "",
    previewWarnings: [],
    pvW: 300,
    pvH: 250,

    // Bước 3
    gridFilter: "all",
    gridItems: [],
    gridToken: 0,
    gridDone: 0,
    gridLoading: false,
    sel: { key: null, element: null },
    positions: {},
    scales: {},
    widths: {},
    excluded: [],

    // Bước 4
    outputDir: LS.get("outputDir", ""),
    exportOpt: { html: true, group_by: "set", manifest: true, preview: true, png: false, png_scale: 2,
                 zip_all: true,
                 click_url: "https://www.google.com" },
    job: { status: "idle", done: 0, total: 0, failed: [], warnings: [] },

    /** Mọi tổ hợp sẽ sinh ra, kể cả cái đã bỏ. */
    get totalAll() {
      return this.sets.length * this.sizes.length * this.design.schemes.length *
             Math.max(1, this.design.badges.length);
    },
    /** Số creative thật sự sẽ xuất. */
    get total() {
      const live = new Set(this.everyKey());
      return this.totalAll - this.excluded.filter(k => live.has(k)).length;
    },
    get visibleSizes() {
      const all = this.catalog.sizes || [];
      const extra = this.sizes.filter(k => !all.some(s => s.key === k))
        .map(k => ({ key: k, group: "other" }));
      const list = [...all, ...extra];
      return this.sizeFilter === "all" ? list : list.filter(s => s.group === this.sizeFilter);
    },
    get ctaPresets() { return (this.catalog.cta_presets || {})[this.draft.lang] || []; },

    async init() {
      document.documentElement.dataset.theme = this.theme;
      await this.setLang(this.lang);
      try {
        this.catalog = await api("/api/catalog");
        // Gán lại sau khi <option> đã render, nếu không <select> sẽ nhảy về mục đầu danh sách.
        // Phải đổi giá trị thật (rỗng → thật) thì Alpine mới cập nhật lại DOM.
        const want = this.lang === "vi" ? "vi" : "en";
        this.draft.lang = "";
        await this.$nextTick();
        this.draft.lang = want;
      } catch (e) { this.error = this.msg(e); }
      this.restore();
      this.connect();
      this.refresh();
      // Nhớ tạm trong máy để lỡ đóng tab hay tải lại trang thì không mất công nhập lại.
      this.$watch("sets", () => this.remember());
      this.$watch("sizes", () => this.remember());
      this.$watch("design", () => this.remember());
      this.$watch("positions", () => this.remember());
      this.$watch("scales", () => this.remember());
      this.$watch("widths", () => this.remember());
      this.$watch("excluded", () => this.remember());
      this.$watch("exportOpt", () => this.remember());
    },

    remember() {
      LS.set("project", JSON.stringify({ sets: this.sets, sizes: this.sizes, design: this.design,
                                         positions: this.positions, scales: this.scales,
                                         widths: this.widths, excluded: this.excluded,
                                         exportOpt: this.exportOpt }));
    },

    restore() {
      try {
        const raw = LS.get("project", "");
        if (!raw) return;
        const p = JSON.parse(raw);
        if (Array.isArray(p.sets)) this.sets = p.sets;
        if (Array.isArray(p.sizes) && p.sizes.length) this.sizes = p.sizes;
        if (p.design) this.design = { ...this.design, ...p.design };
        if (p.positions) this.positions = p.positions;
        if (p.scales) this.scales = p.scales;
        if (p.widths) this.widths = p.widths;
        if (Array.isArray(p.excluded)) this.excluded = p.excluded;
        if (p.exportOpt) this.exportOpt = { ...this.exportOpt, ...p.exportOpt };
        if (!this.sizes.includes(this.previewSize)) this.previewSize = this.sizes[0];
      } catch { /* bản nhớ tạm hỏng thì bỏ qua, bắt đầu lại từ đầu */ }
    },

    t(key) { return this.dict[key] ?? key; },

    msg(e) { return e && e.message === "__offline__" ? this.t("err.offline") : (e ? e.message : ""); },

    /** Nghĩa của nút bấm mẫu theo ngôn ngữ giao diện — chỉ hiện khi khác chữ trên nút. */
    gloss(preset) {
      const meaning = preset[this.lang] || preset.en || "";
      return meaning && meaning !== preset.text ? meaning : "";
    },
    langName(code) { return (this.catalog.languages.find(l => l.key === code) || {}).name || code; },

    async setLang(l) {
      this.lang = l; LS.set("lang", l);
      document.documentElement.lang = l;
      this.dict = await (await fetch(`/static/i18n/${l}.json`)).json();
    },

    toggleTheme() {
      this.theme = this.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = this.theme; LS.set("theme", this.theme);
    },

    connect() {
      const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
      ws.onmessage = (m) => {
        const ev = JSON.parse(m.data);
        if (ev.job) this.job = { failed: [], warnings: [], ...ev.job };
      };
      ws.onopen = () => {
        if (this.error === this.t("err.offline")) this.error = "";
        this.refresh();          // nối lại được thì cập nhật luôn bản xem trước
      };
      ws.onclose = () => setTimeout(() => this.connect(), 1500);
    },

    goto(s) {
      if (s < 1 || s > 4) return;
      if (s > 1 && !this.sets.length) { this.error = this.t("err.noSets"); return; }
      if (s > 2 && !this.sizes.length) { this.error = this.t("err.noSizes"); return; }
      this.error = "";
      this.step = s;
      if (s === 2) this.refresh();
      if (s === 3) {
        if (this.gridFilter !== "all" && !this.sizes.includes(this.gridFilter)) this.gridFilter = "all";
        this.loadGrid();
      }
    },

    // ---------- Bước 1 ----------
    /** Đổi ngôn ngữ nội dung: nếu CTA đang là một nút mẫu thì dịch luôn sang ngôn ngữ mới. */
    onLangChange() {
      const cur = this.draft.cta.trim();
      if (cur) {
        let concept = null;
        for (const list of Object.values(this.catalog.cta_presets || {})) {
          const hit = list.find(p => p.text === cur);
          if (hit) { concept = hit.concept; break; }
        }
        if (concept) {
          const match = (this.ctaPresets || []).find(p => p.concept === concept);
          if (match) this.draft.cta = match.text;
        }
      }
      this.checkCta();
    },

    async checkCta() {
      const text = this.draft.cta.trim();
      if (!text) { this.ctaBanned = []; this.ctaOk = false; return; }
      try {
        const r = await api("/api/cta/check", { method: "POST", body: { text } });
        // Người dùng có thể đã xoá/đổi CTA trong lúc chờ — bỏ qua kết quả cũ.
        if (this.draft.cta.trim() !== text) return;
        this.ctaBanned = r.banned; this.ctaOk = r.ok;
      } catch { /* kiểm CTA hỏng thì bỏ qua, không chặn người dùng */ }
    },

    addSet() {
      const d = this.draft;
      if (!d.headline.trim() || !d.cta.trim()) return;
      const item = { id: this.editing !== null ? this.sets[this.editing].id : Math.random().toString(36).slice(2, 10),
                     name: d.name.trim(), headline: d.headline.trim(), description: d.description.trim(),
                     cta: d.cta.trim(), lang: d.lang };
      if (this.editing !== null) this.sets.splice(this.editing, 1, item);
      else this.sets.push(item);
      this.resetDraft();
      this.refresh();
    },

    resetDraft() {
      this.draft = { headline: "", description: "", cta: "", lang: this.draft.lang, name: "" };
      this.editing = null; this.ctaBanned = []; this.ctaOk = false;
    },

    editSet(i) { this.draft = { ...this.sets[i] }; this.editing = i; this.checkCta(); },

    removeSet(i) {
      const id = this.sets[i].id;
      this.sets.splice(i, 1);
      Object.keys(this.positions).forEach(k => { if (k.startsWith(id + "/")) delete this.positions[k]; });
      if (this.editing === i) this.resetDraft();
      this.refresh();
    },

    async pickCsv() {
      this.csvErrors = [];
      try {
        const p = await api("/api/fs/pick", { method: "POST", body: { kind: "file" } });
        if (!p.path) return;
        const r = await api("/api/csv/import", { method: "POST", body: { path: p.path } });
        this.csvErrors = r.errors;
        r.sets.forEach(s => this.sets.push(s));
        this.refresh();
      } catch (e) { this.error = this.msg(e); }
    },

    onDropImage(ev) {
      this.dragging = false;
      const f = (ev.dataTransfer.files || [])[0];
      if (f) this.readImage(f);
    },
    onPickImage(ev) { const f = ev.target.files[0]; if (f) this.readImage(f); },

    readImage(file) {
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          this.suggestion = await api("/api/reference", {
            method: "POST",
            body: { data_url: reader.result, sizes: this.sizes, design: this.design, sets: this.sets },
          });
        } catch (e) { this.error = this.msg(e); }
      };
      reader.readAsDataURL(file);
    },

    /** Mô tả ngắn bố cục đọc được, kiểu "Tiêu đề: trên · trái". */
    blockLabel(b) {
      return `${this.t("el." + b.element)}: ${this.t("pos." + b.vertical)} · ${this.t("pos." + b.align)}`;
    },

    /** Áp màu lấy từ ảnh mẫu. */
    applySuggestion() {
      if (!this.suggestion) return;
      this.design.schemes = [this.suggestion.scheme];
      if (this.suggestion.accent) this.design.cta_color = this.suggestion.accent;
      this.suggestion = null;
      this.refresh();
    },

    /** Áp cả bố cục đọc từ ảnh mẫu: chỗ đặt chữ và cỡ chữ cho mọi kích thước. */
    applyLayout() {
      const plan = this.suggestion && this.suggestion.plan;
      if (!plan) return;
      this.design.schemes = [this.suggestion.scheme];
      if (plan.cta_color) this.design.cta_color = plan.cta_color;
      else if (this.suggestion.accent) this.design.cta_color = this.suggestion.accent;
      if (plan.layout) this.design.layout = plan.layout;
      for (const [sizeKey, pos] of Object.entries(plan.positions)) {
        if (Object.keys(pos).length) this.positions[sizeKey] = pos;
      }
      for (const [sizeKey, sc] of Object.entries(plan.scales)) {
        if (Object.keys(sc).length) this.scales[sizeKey] = sc;
      }
      for (const [sizeKey, wd] of Object.entries(plan.widths)) {
        if (Object.keys(wd).length) this.widths[sizeKey] = wd;
      }
      this.suggestion = null;
      this.refresh();
      if (this.step === 3) this.loadGrid();
    },

    async toggleLibrary() {
      this.showLibrary = !this.showLibrary;
      if (this.showLibrary) await this.loadLibList();
    },
    async loadLibList() {
      try { this.libItems = (await api("/api/library")).items; } catch (e) { this.error = this.msg(e); }
    },
    async saveLib() {
      try {
        await api("/api/library", { method: "PUT", body: { name: this.libName.trim(), project: this.project() } });
        this.libName = ""; await this.loadLibList();
      } catch (e) { this.error = this.msg(e); }
    },
    async loadLib(name) {
      try {
        const p = (await api(`/api/library/${encodeURIComponent(name)}`)).project;
        this.sets = p.sets;
        this.sizes = p.sizes.map(s => `${s.w}x${s.h}`);
        this.design = p.design;
        this.positions = p.positions || {};
        this.scales = p.scales || {};
        this.widths = p.widths || {};
        this.excluded = p.excluded || [];
        this.exportOpt = { ...this.exportOpt, ...p.export };
        this.refresh();
      } catch (e) { this.error = this.msg(e); }
    },
    async delLib(name) {
      try { await api(`/api/library/${encodeURIComponent(name)}`, { method: "DELETE" }); await this.loadLibList(); }
      catch (e) { this.error = this.msg(e); }
    },

    // ---------- Bước 2 ----------
    toggleSize(key) {
      const i = this.sizes.indexOf(key);
      if (i >= 0) this.sizes.splice(i, 1); else this.sizes.push(key);
      if (!this.sizes.includes(this.previewSize)) this.previewSize = this.sizes[0] || "300x250";
      this.refresh();
    },
    selectAllSizes(on) {
      this.sizes = on ? this.visibleSizes.map(s => s.key) : [];
      if (this.sizes.length) this.previewSize = this.sizes[0];
      this.refresh();
    },
    addCustomSize() {
      const v = this.customSize.trim().replace(/\s|×/g, m => (m === "×" ? "x" : ""));
      if (!/^\d{2,4}x\d{2,4}$/.test(v)) { this.error = this.t("err.badSize"); return; }
      if (!this.sizes.includes(v)) this.sizes.push(v);
      this.customSize = ""; this.error = ""; this.refresh();
    },
    toggleScheme(key) {
      const i = this.design.schemes.indexOf(key);
      if (i >= 0) { if (this.design.schemes.length > 1) this.design.schemes.splice(i, 1); }
      else this.design.schemes.push(key);
      this.refresh();
    },
    toggleBadge(key) {
      const i = this.design.badges.indexOf(key);
      if (i >= 0) this.design.badges.splice(i, 1); else this.design.badges.push(key);
      this.refresh();
    },

    firstContent() {
      return this.sets[0] || { id: "demo", name: "", headline: this.t("d.sampleHeadline"),
                               description: this.t("d.sampleDesc"), cta: this.t("d.sampleCta"),
                               lang: this.draft.lang };
    },

    async refresh() {
      if (!this.sizes.includes(this.previewSize)) this.previewSize = this.sizes[0] || "300x250";
      const body = {
        content: this.firstContent(),
        size: this.previewSize,
        scheme: this.design.schemes[0],
        badge: this.design.badges[0] || null,
        design: this.design,
        positions: this.posFor(this.firstContent().id, this.previewSize),
        scales: this.scaleFor(this.firstContent().id, this.previewSize),
        widths: this.widthFor(this.firstContent().id, this.previewSize),
      };
      try {
        const r = await api("/api/preview", { method: "POST", body });
        this.previewHtml = r.html;
        this.previewWarnings = r.warnings;
        this.pvW = r.size.w; this.pvH = r.size.h;
      } catch (e) { this.previewWarnings = [this.msg(e)]; }
    },

    posFor(setId, sizeKey) {
      return { ...(this.positions[sizeKey] || {}), ...(this.positions[`${setId}/${sizeKey}`] || {}) };
    },

    scaleFor(setId, sizeKey) {
      return { ...(this.scales[sizeKey] || {}), ...(this.scales[`${setId}/${sizeKey}`] || {}) };
    },

    // ---------- Bước 3: xem trước tất cả, chỉnh thẳng trên từng ô ----------
    /** Khoá của mọi tổ hợp đang có (dùng để đếm và dọn danh sách đã bỏ). */
    everyKey() {
      const badges = this.design.badges.length ? this.design.badges : [null];
      const out = [];
      for (const s of this.sets) {
        for (const size of this.sizes) {
          for (const scheme of this.design.schemes) {
            for (const badge of badges) out.push(`${s.id}|${size}|${scheme}|${badge || "-"}`);
          }
        }
      }
      return out;
    },

    kept(c) { return !this.excluded.includes(c.key); },

    /** Ảnh PNG sẽ ra bao nhiêu pixel thật, để người dùng biết nét tới đâu. */
    pngPixels(sizeKey) {
      const k = this.exportOpt.png_scale || 1;
      const [w, h] = sizeKey.split("x");
      return `${w * k}×${h * k} px`;
    },

    /** Bỏ hoặc giữ lại một creative — không xoá nội dung, chỉ không xuất nó. */
    toggleKeep(c) {
      const i = this.excluded.indexOf(c.key);
      if (i >= 0) this.excluded.splice(i, 1);
      else this.excluded.push(c.key);
    },

    /** Giữ hết, hoặc bỏ hết những ô đang hiện trên lưới. */
    keepAll(on) {
      if (on) {
        const shown = new Set(this.gridItems.map(c => c.key));
        this.excluded = this.excluded.filter(k => !shown.has(k));
      } else {
        for (const c of this.gridItems) {
          if (!this.excluded.includes(c.key)) this.excluded.push(c.key);
        }
      }
    },

    /** Mọi creative sẽ xuất ra, theo bộ lọc kích thước đang chọn. */
    allCreatives() {
      const badges = this.design.badges.length ? this.design.badges : [null];
      const sizes = this.gridFilter === "all" ? this.sizes : [this.gridFilter];
      const out = [];
      for (const s of this.sets) {
        for (const size of sizes) {
          for (const scheme of this.design.schemes) {
            for (const badge of badges) {
              out.push({ key: `${s.id}|${size}|${scheme}|${badge || "-"}`, set: s, size, scheme, badge });
            }
          }
        }
      }
      return out;
    },

    /** Vẽ lần lượt từng ô, hiện dần để không phải chờ cả lô. */
    async loadGrid() {
      const token = ++this.gridToken;
      const items = this.allCreatives().slice(0, GRID_MAX);
      this.gridItems = items.map(it => ({
        ...it, boxes: [], colors: {}, ctaStyle: this.design.cta_style,
        w: +it.size.split("x")[0], h: +it.size.split("x")[1],
        label: `${it.set.name || it.set.headline} · ${it.size}`,
      }));
      this.gridDone = 0;
      this.gridLoading = this.gridItems.length > 0;
      for (const item of this.gridItems) {
        if (token !== this.gridToken) return;        // đổi bộ lọc giữa chừng → bỏ lượt vẽ cũ
        await this.drawCard(item);
        if (token !== this.gridToken) return;
        this.gridDone += 1;
      }
      this.gridLoading = false;
      if (this.sel.key && !this.gridItems.some(c => c.key === this.sel.key)) this.sel = { key: null, element: null };
    },

    /** Hỏi tool chỗ đặt từng khối chữ rồi vẽ lại một ô. */
    async drawCard(item) {
      try {
        const r = await api("/api/preview", {
          method: "POST",
          body: { content: item.set, size: item.size, scheme: item.scheme, badge: item.badge,
                  design: this.design, positions: this.posFor(item.set.id, item.size),
                  scales: this.scaleFor(item.set.id, item.size),
                  widths: this.widthFor(item.set.id, item.size), animate: false },
        });
        item.boxes = r.boxes;
        item.colors = r.colors;
        item.ctaStyle = r.cta_style;
        item.w = r.size.w;
        item.h = r.size.h;
        item.warnings = r.warnings;
      } catch (e) { this.error = this.msg(e); }
    },

    /** Tỉ lệ thu nhỏ để ô vừa khung lưới (khổ 970 px vẫn nhìn được). */
    gridScale(c) { return Math.min(1, GRID_CARD_W / Math.max(1, c.w)); },

    bgStyle(c) {
      const bg = c.colors.bg || "#fff";
      const border = c.colors.border || "#e0e0e0";
      return `background:${bg};border:1px solid ${border}`;
    },

    /** Vẽ một khối chữ đúng như bản sẽ xuất ra. */
    boxStyle(c, b) {
      const col = c.colors;
      let extra = "";
      if (b.element === "badge") {
        const badge = (this.catalog.badges || []).find(x => x.key === c.badge) || {};
        extra = `background:${badge.bg};color:${badge.text};border-radius:${(b.h / 2).toFixed(1)}px;` +
                "display:flex;align-items:center;justify-content:center";
      } else if (b.element === "cta") {
        extra = c.ctaStyle === "button"
          ? `background:${col.cta_bg};color:${col.cta_text};border-radius:${Math.min(6, b.h / 4).toFixed(1)}px;` +
            "display:flex;align-items:center;justify-content:center"
          : `color:${col.cta_bg};display:flex;align-items:center;justify-content:center`;
      } else {
        extra = `color:${b.element === "headline" ? col.text : col.sub}`;
      }
      const weight = b.element === "description" ? 400 : 700;
      return `left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px;font-size:${b.font_size}px;` +
             `line-height:${(b.font_size * 1.25).toFixed(2)}px;text-align:${b.align};font-weight:${weight};${extra}`;
    },

    select(c, element) { this.sel = { key: c.key, element }; },

    /** Khoá lưu của một creative: chỉnh ô nào chỉ ảnh hưởng ô đó. */
    keyOf(c) { return `${c.set.id}/${c.size}`; },

    hasOverride(c) {
      const k = this.keyOf(c);
      return [this.positions, this.scales, this.widths].some(store => store[k] || store[c.size]);
    },

    scaleOf(c, element) { return this.scaleFor(c.set.id, c.size)[element] || 1; },

    widthFor(setId, sizeKey) {
      return { ...(this.widths[sizeKey] || {}), ...(this.widths[`${setId}/${sizeKey}`] || {}) };
    },

    /** Kéo tay nắm: cạnh phải đổi bề rộng ô chữ, góc dưới đổi cỡ chữ. Vẽ lại liên tục khi kéo. */
    startResize(ev, c, b, what) {
      ev.preventDefault();
      this.select(c, b.element);
      const k = this.gridScale(c);
      const key = this.keyOf(c);
      const startX = ev.clientX;
      const startY = ev.clientY;
      const avail = Math.max(1, c.w - 2 * Math.max(3, Math.round(Math.min(c.w, c.h) * 0.07)));
      const baseWidth = this.widthFor(c.set.id, c.size)[b.element] || Math.min(1, b.w / avail);
      const baseScale = this.scaleOf(c, b.element);
      const baseDiag = Math.max(12, Math.hypot(b.w, b.h));
      const [wmin, wmax] = this.catalog.width_range || [0.15, 1];
      const [smin, smax] = this.catalog.scale_range || [0.4, 3];

      const move = (e) => {
        if (what === "width") {
          const next = baseWidth + (e.clientX - startX) / k / avail;
          this.widths[key] = { ...this.widthFor(c.set.id, c.size),
                               [b.element]: +Math.min(wmax, Math.max(wmin, next)).toFixed(3) };
        } else {
          const grow = (baseDiag + ((e.clientX - startX) + (e.clientY - startY)) / k / 1.4) / baseDiag;
          this.scales[key] = { ...this.scaleFor(c.set.id, c.size),
                               [b.element]: +Math.min(smax, Math.max(smin, baseScale * grow)).toFixed(2) };
        }
        this.queueDraw(c);
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        if (!this.positions[key]) this.savePos(c);     // giữ nguyên chỗ đang đứng
        this.drawCard(c).then(() => { if (c.size === this.previewSize) this.refresh(); });
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    },

    /** Vẽ lại ô nhưng không chồng chéo: đang vẽ thì xếp hàng lượt mới nhất. */
    queueDraw(c) {
      if (this._drawing) { this._queued = c; return; }
      this._drawing = true;
      this.drawCard(c).finally(() => {
        this._drawing = false;
        const next = this._queued;
        this._queued = null;
        if (next) this.queueDraw(next);
      });
    },

    /** Kéo thả ngay trên ảnh; thả tay ra là lưu luôn, không cần bấm nút nào. */
    startDrag(ev, c, b) {
      ev.preventDefault();
      this.select(c, b.element);
      const k = this.gridScale(c);
      const canvas = ev.currentTarget.parentElement;
      const rect = canvas.getBoundingClientRect();
      const offX = (ev.clientX - rect.left) / k - b.x;
      const offY = (ev.clientY - rect.top) / k - b.y;
      const move = (e) => {
        b.x = Math.max(0, Math.min(c.w - b.w, (e.clientX - rect.left) / k - offX));
        b.y = Math.max(0, Math.min(c.h - b.h, (e.clientY - rect.top) / k - offY));
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        this.savePos(c);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    },

    onKey(ev, c, b) {
      if (ev.key === "+" || ev.key === "=") { ev.preventDefault(); this.select(c, b.element); this.bump(c, 0.1); return; }
      if (ev.key === "-" || ev.key === "_") { ev.preventDefault(); this.select(c, b.element); this.bump(c, -0.1); return; }
      const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
      if (!d) return;
      ev.preventDefault();
      this.select(c, b.element);
      const step = ev.shiftKey ? 10 : 1;
      b.x = Math.max(0, Math.min(c.w - b.w, b.x + d[0] * step));
      b.y = Math.max(0, Math.min(c.h - b.h, b.y + d[1] * step));
      this.savePos(c);
    },

    /** Lưu vị trí hiện tại của riêng creative này (tự động, không cần bấm Áp dụng). */
    savePos(c) {
      const pos = {};
      c.boxes.forEach(b => { pos[b.element] = { x: +(b.x / c.w).toFixed(4), y: +(b.y / c.h).toFixed(4) }; });
      this.positions[this.keyOf(c)] = pos;
      if (c.size === this.previewSize) this.refresh();
    },

    /** Đổi cỡ chữ một khối: lưu ngay rồi vẽ lại ô đó (chữ có thể xuống dòng khác đi). */
    async bump(c, delta) {
      if (this.sel.key !== c.key || !this.sel.element) return;
      const [min, max] = this.catalog.scale_range || [0.4, 3];
      const k = this.keyOf(c);
      const cur = { ...this.scaleFor(c.set.id, c.size) };
      cur[this.sel.element] = Math.min(max, Math.max(min, +((cur[this.sel.element] || 1) + delta).toFixed(2)));
      this.scales[k] = cur;
      if (!this.positions[k]) this.savePos(c);          // giữ nguyên chỗ đang đứng khi chữ đổi cỡ
      await this.drawCard(c);
      if (c.size === this.previewSize) this.refresh();
    },

    /** Chép cách chỉnh của ô này sang mọi bộ cùng kích thước. */
    async copyToSize(c) {
      this.positions[c.size] = { ...(this.positions[this.keyOf(c)] || {}) };
      this.scales[c.size] = { ...(this.scales[this.keyOf(c)] || {}) };
      this.widths[c.size] = { ...(this.widths[this.keyOf(c)] || {}) };
      for (const item of this.gridItems) {
        if (item.size === c.size) await this.drawCard(item);
      }
      this.refresh();
    },

    /** Trả ô này về bố cục tự động. */
    async resetCreative(c) {
      for (const store of [this.positions, this.scales, this.widths]) {
        delete store[this.keyOf(c)];
        delete store[c.size];
      }
      this.sel = { key: null, element: null };
      for (const item of this.gridItems) {
        if (item.size === c.size) await this.drawCard(item);
      }
      this.refresh();
    },

    /** Từ bước 2 nhảy sang lưới, lọc sẵn kích thước đang xem. */
    async tune() {
      this.gridFilter = this.previewSize;
      this.step = 3;
      await this.loadGrid();
    },

    // ---------- Bước 4 ----------
    project() {
      return {
        sets: this.sets,
        scales: this.scales,
        widths: this.widths,
        excluded: this.excluded,
        sizes: this.sizes.map(k => ({ w: +k.split("x")[0], h: +k.split("x")[1] })),
        design: this.design,
        positions: this.positions,
        export: this.exportOpt,
      };
    },

    async pickDir() {
      try {
        const r = await api("/api/fs/pick", { method: "POST", body: { kind: "dir", initial: this.outputDir } });
        if (r.path) { this.outputDir = r.path; LS.set("outputDir", r.path); }
      } catch (e) { this.error = this.msg(e); }
    },

    async run() {
      this.error = "";
      LS.set("outputDir", this.outputDir);
      try {
        await api("/api/jobs", { method: "POST",
                                 body: { project: this.project(), output_dir: this.outputDir } });
      } catch (e) { this.error = this.msg(e); }
    },

    async stop() { try { await api("/api/jobs/stop", { method: "POST" }); } catch (e) { this.error = this.msg(e); } },

    async reveal(path) {
      try { await api("/api/library/reveal", { method: "POST", body: { path } }); }
      catch (e) { this.error = this.msg(e); }
    },
  };
}
