const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "EVA Tail Risk Strategy Pitch Deck";

const NAVY  = "0D1B2A";
const TEAL  = "00C9A7";
const RED   = "FF6B6B";
const WHITE = "FFFFFF";
const LGRAY = "94A3B8";
const CARD  = "152030";
const DCARD = "0A1520";
const GOLD  = "FFD54F";
const BLUE  = "4FC3F7";

const makeShadow = () => ({ type:"outer", blur:8, offset:3, angle:135, color:"000000", opacity:0.2 });

function accentCard(sl, x, y, w, h, color) {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w:0.07, h, fill:{color:color}, line:{color:color} });
}

function bigNumber(sl, x, y, num, label, color) {
  const w = 2.85;
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h:2.5, fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h:0.06, fill:{color:color}, line:{color:color} });
  sl.addText(num,   { x, y:y+0.18, w, h:1.1, fontSize:40, bold:true, color, align:"center", valign:"middle", margin:0 });
  sl.addText(label, { x:x+0.15, y:y+1.35, w:w-0.3, h:1.0, fontSize:11, color:LGRAY, align:"center", valign:"top", margin:0 });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 1 — Title
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.18, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });
  sl.addImage({
    path:"/Users/haitin/Coding/SimicX internship project/Image_wm9l2rwm9l2rwm9l.png",
    x:5.0, y:0, w:5.0, h:5.625, sizing:{type:"cover", w:5.0, h:5.625}
  });
  sl.addShape(pres.shapes.RECTANGLE, {
    x:4.8, y:0, w:0.5, h:5.625,
    fill:{type:"gradient", stops:[{position:0,color:NAVY,transparency:0},{position:100,color:NAVY,transparency:100}], angle:0},
    line:{color:NAVY}
  });
  sl.addText("当市场崩盘时", { x:0.55, y:0.85, w:5.0, h:0.65, fontSize:22, color:TEAL, align:"left", margin:0 });
  sl.addText("我们早已撤退", { x:0.55, y:1.48, w:5.0, h:1.35, fontSize:52, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addShape(pres.shapes.RECTANGLE, { x:0.55, y:3.0, w:3.8, h:0.04, fill:{color:TEAL}, line:{color:TEAL} });
  sl.addText(
    "一个专门为加密市场\n「先保命、再赚钱」设计的量化策略",
    { x:0.55, y:3.15, w:4.3, h:1.0, fontSize:15, color:LGRAY, align:"left", margin:0 }
  );
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 2 — Problem
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("加密货币最难的", { x:0.5, y:0.28, w:9, h:0.58, fontSize:32, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addText("不是赚不到钱，而是活不过崩盘", { x:0.5, y:0.88, w:9, h:0.42, fontSize:18, color:TEAL, align:"left", margin:0 });

  const cards = [
    { x:0.35, year:"2022年", sub:"全年", pct:"-71%", desc:"BTC从 69K 跌至 16K\n多数投资者在恐慌中离场" },
    { x:3.55, year:"2020年", sub:"3月，两周内", pct:"-61%", desc:"COVID 恐慌引发流动性危机\n两周内市场快速腰斩" },
    { x:6.75, year:"2018年", sub:"全年", pct:"-83%", desc:"ICO 泡沫破裂\n大量山寨币接近归零" },
  ];
  cards.forEach(c => {
    const w = 3.0;
    sl.addShape(pres.shapes.RECTANGLE, { x:c.x, y:1.48, w, h:3.6, fill:{color:DCARD}, line:{color:DCARD}, shadow:makeShadow() });
    sl.addShape(pres.shapes.RECTANGLE, { x:c.x, y:1.48, w, h:0.06, fill:{color:RED}, line:{color:RED} });
    sl.addText(c.year, { x:c.x, y:1.6, w, h:0.35, fontSize:13, bold:true, color:WHITE, align:"center", margin:0 });
    sl.addText(c.sub,  { x:c.x, y:1.94, w, h:0.3, fontSize:11, color:LGRAY, align:"center", margin:0 });
    sl.addText(c.pct,  { x:c.x, y:2.28, w, h:1.1, fontSize:62, bold:true, color:RED, align:"center", valign:"middle", margin:0 });
    sl.addText(c.desc, { x:c.x+0.15, y:3.48, w:w-0.3, h:1.45, fontSize:11.5, color:LGRAY, align:"left", valign:"top", margin:0 });
  });

  sl.addShape(pres.shapes.RECTANGLE, { x:0.5, y:5.08, w:9, h:0.38, fill:{color:CARD}, line:{color:CARD} });
  sl.addText(
    "真正的问题不是「什么时候涨」，而是「什么时候必须先撤」",
    { x:0.5, y:5.08, w:9, h:0.38, fontSize:13, bold:true, color:TEAL, align:"center", valign:"middle", margin:0 }
  );
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 3 — Why Traditional Methods Fail
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("为什么传统风险模型", { x:0.5, y:0.28, w:9, h:0.55, fontSize:32, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addText("在加密市场经常失灵", { x:0.5, y:0.82, w:9, h:0.48, fontSize:22, color:RED, align:"left", margin:0 });

  const problems = [
    {
      num:"①", color:RED,
      title:"它假设资产是「分散」的",
      body:"你买了10种币，看似分散；但崩盘时，它们往往一起跌。",
      quote:"分散投资在加密里，有时只是错觉。"
    },
    {
      num:"②", color:GOLD,
      title:"它假设「危险程度」比较稳定",
      body:"平时的「极端」与熊市里的「极端」，根本不是一个量级。",
      quote:"用同一把尺子量晴天和台风，注定会出错。"
    },
    {
      num:"③", color:BLUE,
      title:"它假设极端事件是「偶发」的",
      body:"一次暴跌之后，往往不是结束，而是下一轮风险的开始。",
      quote:"不是一场风暴，而是一串风暴。"
    },
  ];

  problems.forEach((p, i) => {
    const y = 1.52 + i * 1.3;
    sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:9.2, h:1.15, fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
    sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:0.07, h:1.15, fill:{color:p.color}, line:{color:p.color} });
    sl.addText(p.num+" "+p.title, { x:0.65, y:y+0.1, w:3.5, h:0.38, fontSize:13, bold:true, color:WHITE, margin:0 });
    sl.addText(p.body,  { x:0.65, y:y+0.5, w:5.5, h:0.58, fontSize:11, color:LGRAY, align:"left", valign:"top", margin:0 });
    sl.addText(p.quote, { x:6.4,  y:y+0.25, w:3.0, h:0.65, fontSize:12, color:p.color, align:"center", valign:"middle", italic:true, margin:0 });
  });

  sl.addText("这三个问题，都需要一套不同的方法来解决。", {
    x:0.5, y:5.32, w:9, h:0.22, fontSize:11, color:LGRAY, align:"center", italic:true, margin:0
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 4 — Core Insight
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("我们的核心洞察", { x:0.5, y:0.28, w:9, h:0.55, fontSize:32, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addText("市场里不同的「风险来源」，危险程度并不一样", { x:0.5, y:0.87, w:9, h:0.4, fontSize:16, color:TEAL, align:"left", margin:0 });

  // Analogy box
  sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y:1.42, w:9.2, h:1.05, fill:{color:DCARD}, line:{color:DCARD} });
  sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y:1.42, w:0.07, h:1.05, fill:{color:TEAL}, line:{color:TEAL} });
  sl.addText([
    { text:"类比：", options:{color:TEAL, bold:true} },
    { text:"一首交响乐听起来是一团声音，但录音师可以把它拆成不同声道分别处理。我们对加密市场做的，就是同样的事。", options:{color:WHITE} }
  ], { x:0.65, y:1.5, w:8.8, h:0.85, fontSize:14, align:"left", valign:"middle", margin:0 });

  // Three insight cards
  const insights = [
    { x:0.35, color:TEAL,  icon:"🎵", title:"第一步：拆解",
      body:"把10个高度相关的加密货币，拆成几个相互独立的市场驱动力。\n\n比如：整体市场风险、局部币种风险。" },
    { x:3.55, color:GOLD,  icon:"🌡", title:"第二步：测温",
      body:"对每个驱动力，单独测量它「出大事的概率有多高」。\n\n这个「危险温度」在危机前往往会上升。" },
    { x:6.75, color:BLUE,  icon:"⚡", title:"关键发现",
      body:"不同驱动力的危险温度并不一样。\n\n整体市场温度升高 = 系统性风险\n局部温度升高 = 局部风险，可规避" },
  ];
  insights.forEach(p => {
    const w = 3.0;
    sl.addShape(pres.shapes.RECTANGLE, { x:p.x, y:2.65, w, h:2.78, fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
    sl.addShape(pres.shapes.RECTANGLE, { x:p.x, y:2.65, w, h:0.06, fill:{color:p.color}, line:{color:p.color} });
    sl.addText(p.icon+" "+p.title, { x:p.x+0.15, y:2.75, w:w-0.25, h:0.42, fontSize:14, bold:true, color:p.color, margin:0 });
    sl.addText(p.body, { x:p.x+0.15, y:3.2, w:w-0.25, h:2.1, fontSize:11.5, color:LGRAY, align:"left", valign:"top", margin:0 });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 5 — How It Works
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("策略如何运作", { x:0.5, y:0.28, w:9, h:0.55, fontSize:32, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addText("三步完成：风险识别 → 资产评级 → 仓位切换", { x:0.5, y:0.87, w:9, h:0.4, fontSize:15, color:LGRAY, align:"left", margin:0 });

  const steps = [
    {
      num:"1", color:TEAL, x:0.3,
      title:"拆解市场",
      what:"",
      how:"把混在一起的市场波动，拆成几个独立的风险来源。\n这样可以更清楚地看到风险真正来自哪里。",
      why:""
    },
    {
      num:"2", color:GOLD, x:3.55,
      title:"测量危险程度",
      what:"",
      how:"持续监测哪些风险来源正在变得更危险。\n我们不看「平均波动」，只关注真正可能造成大伤害的部分。",
      why:""
    },
    {
      num:"3", color:RED, x:6.8,
      title:"动态调整仓位",
      what:"",
      how:"根据每个资产对危险风险来源的暴露程度进行排序。\n正常市场参与收益，压力升高时自动转入防御。",
      why:""
    },
  ];

  steps.forEach(s => {
    const w = 3.05;
    sl.addShape(pres.shapes.RECTANGLE, { x:s.x, y:1.45, w, h:3.95, fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
    sl.addShape(pres.shapes.RECTANGLE, { x:s.x, y:1.45, w, h:0.06, fill:{color:s.color}, line:{color:s.color} });
    sl.addShape(pres.shapes.OVAL, { x:s.x+1.18, y:1.62, w:0.65, h:0.65, fill:{color:s.color}, line:{color:s.color} });
    sl.addText(s.num, { x:s.x+1.18, y:1.62, w:0.65, h:0.65, fontSize:22, bold:true, color:NAVY, align:"center", valign:"middle", margin:0 });
    sl.addText(s.title, { x:s.x+0.12, y:2.45, w:w-0.22, h:0.42, fontSize:15, bold:true, color:WHITE, align:"center", margin:0 });
    sl.addText(s.what,  { x:s.x+0.15, y:2.95, w:w-0.28, h:0.38, fontSize:10.5, color:s.color, align:"left", italic:true, margin:0 });
    sl.addText(s.how,   { x:s.x+0.15, y:3.35, w:w-0.28, h:1.1, fontSize:11, color:LGRAY, align:"left", valign:"top", margin:0 });
    sl.addShape(pres.shapes.RECTANGLE, { x:s.x+0.15, y:4.5, w:w-0.3, h:0.03, fill:{color:"1E3040"}, line:{color:"1E3040"} });
    sl.addText(s.why,   { x:s.x+0.15, y:4.57, w:w-0.28, h:0.65, fontSize:10.5, color:s.color, align:"left", valign:"top", margin:0 });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 6 — Why This Matters for Investors (NEW)
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("这不是在预测价格", { x:0.5, y:0.28, w:9, h:0.55, fontSize:32, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addText("而是提前识别「什么时候不该硬扛」", { x:0.5, y:0.87, w:9, h:0.4, fontSize:18, color:TEAL, align:"left", margin:0 });

  const points = [
    {
      color:TEAL, icon:"✦",
      title:"它不追求天天预测涨跌",
      body:"市场短期走势没有人能稳定预测。\n我们只回答一个更重要的问题：\n现在的风险，是否已经高到不值得继续扛？",
      note:"这个问题，是可以用数据回答的。"
    },
    {
      color:GOLD, icon:"✦",
      title:"它不是为了牛市跑得最快",
      body:"牛市里我们会参与收益，但不会全力追涨。\n这个策略的目标，是在最危险的时候让资产少受伤。",
      note:"一次 -80% 的亏损，需要 +400% 才能回本。"
    },
    {
      color:RED, icon:"✦",
      title:"它的价值，在关键几次大崩盘时体现",
      body:"大多数时间，它和别的策略差距不大。\n真正拉开差距的，是极端市场来临的那几次。",
      note:"穿越崩盘的能力，是最稀缺的投资能力。"
    },
  ];

  points.forEach((p, i) => {
    const y = 1.42 + i * 1.32;
    sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:9.2, h:1.18, fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
    sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:0.07, h:1.18, fill:{color:p.color}, line:{color:p.color} });
    sl.addText(p.icon+" "+p.title, { x:0.65, y:y+0.1, w:3.8, h:0.38, fontSize:13, bold:true, color:p.color, margin:0 });
    sl.addText(p.body,  { x:0.65, y:y+0.5, w:6.0, h:0.62, fontSize:10.5, color:LGRAY, align:"left", valign:"top", margin:0 });
    sl.addShape(pres.shapes.RECTANGLE, { x:6.85, y:y+0.22, w:2.55, h:0.75, fill:{color:DCARD}, line:{color:DCARD} });
    sl.addText(p.note, { x:6.85, y:y+0.22, w:2.55, h:0.75, fontSize:11, color:p.color, align:"center", valign:"middle", italic:true, margin:0 });
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 7 — Results
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("结果很简单", { x:0.5, y:0.28, w:9, h:0.55, fontSize:32, bold:true, color:WHITE, align:"left", margin:0 });
  sl.addText("牛市不一定最快，但熊市明显更能保命", { x:0.5, y:0.87, w:9, h:0.4, fontSize:16, color:TEAL, align:"left", margin:0 });

  // Three big numbers only — no chart here
  bigNumber(sl, 0.35, 1.55, "+4.0%",  "2022年全年熊市收益\nBTC同期 -71.1%",   TEAL);
  bigNumber(sl, 3.55, 1.55, "-33%",   "全周期最大回撤\nBTC历史最大 -84%",     GOLD);
  bigNumber(sl, 6.75, 1.55, "1.11",   "Sharpe比率\n等权基准仅 0.36",          BLUE);

  sl.addText("同一套规则，同一段历史，没有事后挑选案例。", {
    x:0.5, y:4.25, w:9, h:0.38, fontSize:13, color:LGRAY, align:"center", italic:true, margin:0
  });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 8 — Chart + Closing
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: DCARD };
  sl.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:10, h:0.1, fill:{color:TEAL}, line:{color:TEAL} });

  sl.addText("这是8年的真实记录", { x:0.5, y:0.2, w:9, h:0.52, fontSize:26, bold:true, color:WHITE, align:"center", margin:0 });
  sl.addText("绿线 = 策略  ·  灰线 = BTC  ·  虚线 = 等权10币  ·  红色阴影 = 机械定义熊市区间（BTC回撤>40%）", {
    x:0.5, y:0.72, w:9, h:0.3, fontSize:10, color:LGRAY, align:"center", margin:0
  });

  // Chart — large, centered
  sl.addImage({
    path:"/Users/haitin/Coding/SimicX internship project/defensive_strategy.png",
    x:0.3, y:1.1, w:9.4, h:3.8,
    sizing:{type:"contain", w:9.4, h:3.8}
  });

  sl.addShape(pres.shapes.RECTANGLE, { x:1.5, y:5.0, w:7, h:0.03, fill:{color:"1E3040"}, line:{color:"1E3040"} });
  sl.addText([
    { text:"\u201c", options:{color:TEAL, bold:true} },
    { text:"在最危险的时候少亏，往往比在最热闹的时候多赚，更重要。", options:{color:WHITE} },
    { text:"\u201d", options:{color:TEAL, bold:true} }
  ], { x:0.8, y:5.08, w:8.4, h:0.42, fontSize:14, align:"center", valign:"middle", italic:true, margin:0 });
}

// ══════════════════════════════════════════════════════════════════════
// SLIDE 9 — Stress Regime Breakdown
// ══════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  sl.background = { color: NAVY };
  sl.addText("当市场真正崩盘时，差距有多大？", {
    x:0.5, y:0.28, w:9, h:0.55, fontSize:28, bold:true, color:WHITE, align:"left", margin:0
  });
  sl.addText("同一套策略，在熊市和正常市场各自表现如何", {
    x:0.5, y:0.87, w:9, h:0.38, fontSize:15, color:TEAL, align:"left", margin:0
  });

  // ── Column headers ──────────────────────────────────────────────────
  const COL = { label:0.4, stress:4.2, normal:7.05 };
  const HDR_Y = 1.42;

  sl.addShape(pres.shapes.RECTANGLE, { x:4.1, y:HDR_Y, w:2.75, h:0.52,
    fill:{color:"3D1A1A"}, line:{color:RED} });
  sl.addText("🔴  熊市压力期", { x:4.1, y:HDR_Y, w:2.75, h:0.52,
    fontSize:12, bold:true, color:RED, align:"center", valign:"middle", margin:0 });

  sl.addShape(pres.shapes.RECTANGLE, { x:6.95, y:HDR_Y, w:2.75, h:0.52,
    fill:{color:"0D2D1A"}, line:{color:TEAL} });
  sl.addText("🟢  正常市场", { x:6.95, y:HDR_Y, w:2.75, h:0.52,
    fontSize:12, bold:true, color:TEAL, align:"center", valign:"middle", margin:0 });

  sl.addText("机械定义：BTC 从 180 日高点回撤 > 40%", {
    x:0.4, y:HDR_Y+0.1, w:3.6, h:0.35, fontSize:10, color:LGRAY, align:"left",
    italic:true, margin:0
  });

  // ── Row data ─────────────────────────────────────────────────────────
  const rows = [
    {
      label:"EVA 策略",
      stressRet:"+35%", stressDD:"-14%", stressColor:TEAL,
      normalRet:"+30%", normalDD:"-35%", normalColor:LGRAY,
    },
    {
      label:"BTC 买入持有",
      stressRet:"极度亏损", stressDD:"-95%", stressColor:RED,
      normalRet:"+95%", normalDD:"-45%", normalColor:LGRAY,
    },
  ];

  rows.forEach((row, i) => {
    const y = 2.12 + i * 1.38;
    const H = 1.22;

    // row label
    sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:3.6, h:H,
      fill:{color:CARD}, line:{color:CARD}, shadow:makeShadow() });
    sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:0.06, h:H,
      fill:{color: i===0 ? TEAL : RED}, line:{color: i===0 ? TEAL : RED} });
    sl.addText(row.label, { x:0.6, y:y+0.15, w:3.3, h:0.45,
      fontSize:14, bold:true, color:WHITE, margin:0 });
    sl.addText(i===0 ? "集成策略（EVA 优化 + EVT 混合）" : "单纯持有比特币，不做任何风控", {
      x:0.6, y:y+0.6, w:3.3, h:0.45, fontSize:10, color:LGRAY, margin:0
    });

    // stress cell
    sl.addShape(pres.shapes.RECTANGLE, { x:4.1, y, w:2.75, h:H,
      fill:{color:"1A0D0D"}, line:{color:"3D1A1A"}, shadow:makeShadow() });
    sl.addText(row.stressRet, { x:4.1, y:y+0.1, w:2.75, h:0.52,
      fontSize:24, bold:true, color:row.stressColor, align:"center", margin:0 });
    sl.addText("最大回撤 " + row.stressDD, { x:4.1, y:y+0.65, w:2.75, h:0.38,
      fontSize:12, color:row.stressColor, align:"center", margin:0 });

    // normal cell
    sl.addShape(pres.shapes.RECTANGLE, { x:6.95, y, w:2.75, h:H,
      fill:{color:"0A1A12"}, line:{color:"1A3D27"}, shadow:makeShadow() });
    sl.addText(row.normalRet, { x:6.95, y:y+0.1, w:2.75, h:0.52,
      fontSize:24, bold:true, color:row.normalColor, align:"center", margin:0 });
    sl.addText("最大回撤 " + row.normalDD, { x:6.95, y:y+0.65, w:2.75, h:0.38,
      fontSize:12, color:row.normalColor, align:"center", margin:0 });
  });

  // ── Key insight box ───────────────────────────────────────────────
  sl.addShape(pres.shapes.RECTANGLE, { x:0.4, y:4.98, w:9.2, h:0.52,
    fill:{color:CARD}, line:{color:TEAL} });
  sl.addText([
    { text:"关键结论：", options:{color:TEAL, bold:true} },
    { text:"在最难熬的时候，策略最大回撤仅 -14%，而 BTC 最深跌至 -95%。少亏这一步，决定了能否活到下一个牛市。", options:{color:WHITE} }
  ], { x:0.55, y:4.98, w:9.0, h:0.52, fontSize:12, valign:"middle", margin:0 });
}

// ── Write ──────────────────────────────────────────────────────────────
pres.writeFile({ fileName:"EVA_Pitch_Deck.pptx" })
  .then(() => console.log("生成成功 → EVA_Pitch_Deck.pptx (9张幻灯片)"))
  .catch(e => { console.error(e); process.exit(1); });
