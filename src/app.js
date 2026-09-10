/* 真假CP鉴定器 — 界面逻辑（经典脚本 / ES2017 上限 / 纯本地无网络）
 * 依赖：engine.js（window.LiuYao）、readings.js（window.Readings）
 * JSBridge 均为能力检测可选增强，不挡基础功能
 * 玩法：选问题 → 选CP状态 → 填CP名（可选生年）→ 缓冲推演 → 档位结论+大字报+卦图鉴+嗑学家称号
 */
(function () {
  'use strict';
  var LY = window.LiuYao;
  var RD = window.Readings;

  function $(s) { return document.querySelector(s); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  function show(node) { node.classList.remove('hidden'); }
  function hide(node) { node.classList.add('hidden'); }

  /* 五十一轮（lyvia 真机抓：v45 toast「可截图分享」＝脚本载入那一刻桥还没来）：
   * 桥不能在载入时快照——容器很可能在页面就绪后才注入 window.xhs.miniTool，
   * 快照一次就永远 false（这正是「存不了只能截图」的头号嫌疑）。
   * 改为点击时现查；查不到时把缺在哪层报进 toast（xhs/miniTool/接口名），远程可诊断。 */
  function mt() {
    /* 五十三轮（官方《容器能力清单》实锤：入口=window.xhs.miniTool.*，签名与我们一致；
     * 且官方原文自认「调用前判空，为未注入的环境准备降级路径」→ 未注入是官方承认的环境态）。
     * 保险焊死：不赌注入名字——先查官方入口，再全窗口扫任何同时带存图+发笔记方法的对象。 */
    if (typeof window.xhs !== 'undefined' && window.xhs && window.xhs.miniTool) return window.xhs.miniTool;
    for (var k in window) {
      try {
        var o = window[k];
        if (o && typeof o === 'object' &&
            typeof o.saveImageToPhotosAlbum === 'function' &&
            typeof o.postNote === 'function') return o;
      } catch (e) {}
    }
    return null;
  }
  function hasSave() { var b = mt(); return !!(b && typeof b.saveImageToPhotosAlbum === 'function'); }
  function hasPost() { var b = mt(); return !!(b && typeof b.postNote === 'function'); }

  var HISTORY_KEY = 'doubu_lite_history_v1';
  var DEX_KEY = 'doubu_lite_dex_v1';
  var CP_KEY = 'doubu_lite_cp_v2';
  var state = {
    cat: null, cpState: '', cpName: '', numStr: '', castSource: '',
    cast: null, yq: [], reading: null, cardUri: '', posterUri: '', previewUri: '',
    dexNew: false, cpCount: 0,
    manual: null, manualCast: null // 五十五轮：手动起卦（豆卜迁移）
  };

  // ── 视图切换 ──
  var VIEWS = ['viewChoose', 'viewOther', 'viewState', 'viewInput', 'viewManual', 'viewCast', 'viewBuf', 'viewResult', 'viewHistory'];
  function goto(name) {
    for (var i = 0; i < VIEWS.length; i++) {
      var v = document.getElementById(VIEWS[i]);
      if (VIEWS[i] === name) show(v); else hide(v);
    }
    window.scrollTo(0, 0);
  }

  // ── toast ──
  var toastTimer = null;
  function toast(msg, ms) {
    var t = $('#toast');
    t.textContent = msg;
    show(t);
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { hide(t); }, ms || 2400);
  }

  // ── 今天（本地时区, Y/M/D 构造, 禁字符串解析）──
  function todayYMD() {
    var d = new Date();
    return [d.getFullYear(), d.getMonth() + 1, d.getDate()];
  }

  // ── 首页（CP 主路径）＋ 问点别的（纯广告：只展示问法，不可算，答案在 Idolship豆卜免费版）──
  function buildOtherList() {
    var box = $('#otherList');
    box.textContent = '';
    // 二十五轮（lyvia）：阉割版标题改口＋追加追星以外的示例（游戏抽卡/健康状况/偏财运）
    var rows = [
      { name: '抢票成行', desc: '演唱会、签售、票，能不能成行' },
      { name: '本命缘分', desc: '你和本命的缘分走向' },
      { name: '粉圈人际', desc: '粉圈人际、同好、组圈那些事' },
      { name: '追星心情', desc: '不为什么，就是想问问追星的心情' },
      { name: '游戏抽卡', desc: '抽卡、开箱、出金，今天手气如何' },
      { name: '健康状况', desc: '身体与作息的起伏走势，娱乐参详' },
      { name: '偏财运', desc: '小财进出的走势，随手一占' }
    ];
    for (var i = 0; i < rows.length; i++) {
      var b = el('div', 'cat-row');
      b.appendChild(el('span', 'cat-name', rows[i].name));
      b.appendChild(el('span', 'cat-desc', rows[i].desc));
      box.appendChild(b);
    }
  }

  function pickCat(k) {
    state.cat = k;
    if (k === 'career') {
      buildStateList();
      goto('viewState');
      return;
    }
    state.cpState = '';
    $('#castCat').textContent = '所问：' + LY.CATEGORIES[k].label;
    resetCoins();
    goto('viewCast');
  }

  // ── CP状态选择（仅CP契合）──
  var CP_STATES = [
    { key: 'hot', name: '就差结婚了', desc: '看未来发展趋势' },
    { key: 'rumor', name: '难以分辨', desc: '他俩到底什么情况' },
    { key: 'be', name: '已经BE', desc: '死灰复燃的可能性还有吗' }
  ];
  function buildStateList() {
    var box = $('#stateList');
    box.textContent = '';
    for (var i = 0; i < CP_STATES.length; i++) {
      (function (st) {
        var b = el('button', 'cat-btn');
        b.setAttribute('type', 'button');
        b.appendChild(el('span', 'cat-name', st.name));
        b.appendChild(el('span', 'cat-desc', st.desc));
        b.appendChild(el('span', 'cat-next', '›'));
        b.addEventListener('click', function () { pickState(st.key); });
        box.appendChild(b);
      })(CP_STATES[i]);
    }
  }
  function gotoInput() {
    $('#inputTitle').textContent = '假亦真时真亦假';
    $('#inputHint').textContent = '我家CP到底是真是假';
    $('#cpNameInput').value = state.cpName || '';
    $('#castNumInput').value = state.numStr || '';
    goto('viewInput');
    try { $('#cpNameInput').focus(); } catch (e) { /* headless 无焦点 */ }
  }
  function pickState(sk) {
    state.cpState = sk;
    gotoInput();
  }

  // ── CP名/神秘数字输入 ──
  function submitInput() {
    var name = ($('#cpNameInput').value || '').replace(/^\s+|\s+$/g, '').slice(0, 24);
    if (!name) { toast('先填一下鉴定对象'); return; }
    state.cpName = name;
    state.numStr = ($('#castNumInput').value || '').replace(/[^0-9]/g, '').slice(0, 32);
    startBuffer();
  }

  // ── 缓冲推演（豆卜式步骤文案，纯本地计时）──
  var BUF_STEPS = ['净手起卦', '装卦纳甲', '配六亲', '定用神', '断旺衰', '推应期'];
  var bufTimer = null;
  function startBuffer() {
    resetCoins();
    var cast = rollNow();
    if (!cast) return;
    goto('viewBuf');
    var step = 0;
    $('#bufText').textContent = BUF_STEPS[0] + '…';
    if (bufTimer) clearInterval(bufTimer);
    bufTimer = setInterval(function () {
      step++;
      if (step < BUF_STEPS.length) {
        $('#bufText').textContent = BUF_STEPS[step] + '…';
      } else {
        clearInterval(bufTimer);
        bufTimer = null;
        renderResult();
        goto('viewResult');
      }
    }, 420);
  }
  /* ── 数字起卦（梅花端法）：神秘数字定卦，起卦时间取真实当下→旺衰冲合随时辰变 ──
   * 前半段数字和%8定上卦、后半段和%8定下卦（乾1兑2离3震4巽5坎6艮7坤8，0作8），
   * 总和%6定动爻（0作6）。同数字同日同卦，不同时刻旺衰不同——同时起卦也不撞。
   */
  var TRI_LINES = { 1: [1, 1, 1], 2: [1, 1, 0], 3: [1, 0, 1], 4: [1, 0, 0], 5: [0, 1, 1], 6: [0, 1, 0], 7: [0, 0, 1], 8: [0, 0, 0] };
  function digitSum(str) {
    var t = 0;
    for (var i = 0; i < str.length; i++) t += Number(str.charAt(i));
    return t;
  }
  function triOf(str) {
    var n = digitSum(str) % 8;
    if (n === 0) n = 8;
    return TRI_LINES[n];
  }
  function numberCast(digitStr) {
    var d = digitStr;
    if (!d) return null;
    var half = Math.ceil(d.length / 2);
    var up = triOf(d.slice(0, half));
    var low = triOf(d.slice(half));
    var moving = digitSum(d) % 6;
    if (moving === 0) moving = 6;
    return { lines: low.concat(up), moving: moving };
  }

  function rollNow() {
    var pre = state.manualCast; // 五十五轮：手动装卦/摇卦直接喂现成 {lines, moving}
    state.manualCast = null;
    var r = pre || (state.numStr ? numberCast(state.numStr) : rollCast());
    state.castSource = pre ? 'manual' : (state.numStr ? 'num' : 'coin');
    var cast = LY.castFromLines(r.lines, r.moving, todayYMD(), state.cat);
    cast.star = RD.yingStar(cast); // 三十一轮（lyvia）：打分切世应——应爻旺衰＋世应生克，覆写引擎用神星
    var yq = LY.yingqiDates(cast);
    state.cast = cast;
    state.yq = yq;
    state.reading = RD.build(cast, yq, state.cpState, '', state.cpCount || 0);
    state.cardUri = '';
    state.posterUri = '';
    state.cardCanvas = null;
    state.posterCanvas = null;
    state.dexNew = dexAdd(cast.ben_gua);
    state.cpCount = cpAdd();
    saveHistory(cast);
    return cast;
  }

  // ── 摇卦（按住-松手；三枚铜钱掷六次，无动爻自动重摇）──
  function coin() { return Math.random() < 0.5 ? 2 : 3; }

  function rollCast() {
    for (var attempt = 0; attempt < 40; attempt++) {
      var lines = [], moving = 0;
      for (var i = 0; i < 6; i++) {
        var s = coin() + coin() + coin(); // 6老阴 7少阳 8少阴 9老阳
        lines.push(s === 7 || s === 9 ? 1 : 0);
        if ((s === 6 || s === 9) && !moving) moving = i + 1;
      }
      if (moving) return { lines: lines, moving: moving };
    }
    return { lines: [1, 1, 0, 0, 1, 0], moving: 3 };
  }

  var shakeTimer = null;
  function resetCoins() {
    if (shakeTimer) { clearInterval(shakeTimer); shakeTimer = null; }
    var coins = document.querySelectorAll('#coinRow .coin');
    for (var i = 0; i < coins.length; i++) {
      coins[i].textContent = '？';
      coins[i].classList.remove('on');
    }
    $('#coinRow').classList.remove('shaking');
    var btn = $('#shakeBtn');
    btn.textContent = '按住摇卦 · 松手落卦';
    btn.classList.remove('holding');
  }

  function startShake(e) {
    if (e && e.cancelable) e.preventDefault();
    if (shakeTimer) return;
    var btn = $('#shakeBtn');
    btn.textContent = '正在摇…松手落卦';
    btn.classList.add('holding');
    $('#coinRow').classList.add('shaking');
    shakeTimer = setInterval(function () {
      var coins = document.querySelectorAll('#coinRow .coin');
      for (var i = 0; i < coins.length; i++) {
        coins[i].textContent = Math.random() < 0.5 ? '字' : '背';
        coins[i].classList.toggle('on', coins[i].textContent === '背');
      }
    }, 90);
  }

  function endShake() {
    if (!shakeTimer) return;
    clearInterval(shakeTimer);
    shakeTimer = null;
    startBuffer(); // 非CP分类走摇卦视图；CP分类在输入视图开始，不经此处
  }

  /* ── 手动起卦（五十五轮，lyvia：豆卜「🎲 手动摇卦 / ✋ 手动装卦」迁移）──
   * 史同/虚拟人物没有生日纪念日可输入，数字起卦无从下手——给她一条亲手起卦的路。
   * 装卦：六行点选，阳→阴→老阳○→老阴✕ 四态轮换；
   * 摇卦：三枚铜钱掷六次，从初爻到上爻，掷出老阳/老阴即动爻。
   * 引擎（castFromLines）只收一个动爻，所以装卦限选一动（后选顶替），摇卦六静则重摇——与自动摇卦同一约束。
   */
  var YAO_NAMES = ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻'];
  var YAO_STATES = [
    { g: '━━━━━', t: '少阳' },
    { g: '━━━ ━━━', t: '少阴' },
    { g: '━━━━━ ○', t: '老阳' },
    { g: '━━━ ━━━ ✕', t: '老阴' }
  ];
  var MANUAL_TIP_FIT = '从最下面的「初爻」开始按顺序填入，最后填「上爻」。\n点中间符号切换「阳爻/阴爻」，点右侧「☆」标记动爻（3枚硬币抛出相同结果时为动爻）'; // 五十九轮（lyvia）：她定稿☆版
  var MANUAL_TIP_SHAKE = '每一爻根据你所触碰的时间点决定，静待觉得合适的时机，点击六次成卦'; // 五十八轮：她定稿
  var MANUAL_SUB_FIT = '☆ 标出的那一爻就是动爻——卦因它而变'; // 五十九轮：子说明随模式切换
  var MANUAL_SUB_SHAKE = '老阳○ / 老阴✕ 就是动爻——卦因它而变';

  function manualLinesMoving() {
    var vals = state.manual.vals, lines = [], moving = 0;
    for (var i = 0; i < 6; i++) {
      lines.push(vals[i] === 1 || vals[i] === 3 ? 0 : 1);
      if ((vals[i] === 2 || vals[i] === 3) && !moving) moving = i + 1;
    }
    return { lines: lines, moving: moving };
  }

  function renderManual() {
    if (!state.manual) return;
    var box = $('#yaoPick');
    box.innerHTML = '';
    /* 五十八轮（lyvia）：排盘爻序=上爻在顶、初爻在底（与结果表/卦盘图一致） */
    for (var i = 5; i >= 0; i--) {
      (function (idx) {
        var v = state.manual.vals[idx];
        var fit = state.manual.mode === 'fit';
        var thrown = fit || idx < state.manual.thrown;
        var li = el('li', 'yao-row6' + (fit ? ' pickable' : '') + (thrown ? '' : ' empty'));
        li.appendChild(el('span', 'yao-idx', YAO_NAMES[idx]));
        var mid = el('span', 'yao-mid'); // 五十九轮：符号+小字状态标成组，靠左贴着排
        var g = el('span', 'yao-glyph6', thrown ? YAO_STATES[v].g : '？');
        mid.appendChild(g);
        mid.appendChild(el('span', 'yao-mini' + (thrown && v >= 2 ? ' moving' : ''), thrown ? YAO_STATES[v].t : '未掷'));
        li.appendChild(mid);
        if (fit) {
          /* 五十九轮（lyvia）：照豆卜原版模型——点中间符号切「阳爻/阴爻」，点右侧「☆」标动爻 */
          g.addEventListener('click', function () {
            state.manual.vals[idx] = (state.manual.vals[idx] === 1 || state.manual.vals[idx] === 3) ? 0 : 1;
            renderManual();
          });
          var star = el('span', 'yao-star' + (v >= 2 ? ' on' : ''), v >= 2 ? '★' : '☆');
          star.addEventListener('click', function () {
            if (state.manual.vals[idx] >= 2) { // 已是动爻：摘星退回静爻
              state.manual.vals[idx] = state.manual.vals[idx] === 2 ? 0 : 1;
            } else { // 标动：动爻唯一，后选顶替，旧动爻退回静爻
              state.manual.vals[idx] = state.manual.vals[idx] === 1 ? 3 : 2;
              for (var j = 0; j < 6; j++) {
                if (j !== idx && state.manual.vals[j] >= 2) state.manual.vals[j] = state.manual.vals[j] === 2 ? 0 : 1;
              }
            }
            renderManual();
          });
          li.appendChild(star);
        }
        box.appendChild(li);
      })(i);
    }
    var mm = manualLinesMoving();
    var go = $('#manualGo');
    var roll = $('#manualRollBtn');
    var tip = $('#manualTip');
    if (state.manual.mode === 'fit') {
      roll.classList.add('hidden');
      tip.textContent = MANUAL_TIP_FIT;
      $('.manual-tip-sub').textContent = MANUAL_SUB_FIT;
      go.disabled = !mm.moving;
      go.textContent = mm.moving ? '成卦 · 开始鉴定' : '选一个动爻就能成卦';
    } else {
      roll.classList.remove('hidden');
      tip.textContent = MANUAL_TIP_SHAKE;
      $('.manual-tip-sub').textContent = MANUAL_SUB_SHAKE;
      if (state.manual.thrown >= 6) {
        roll.textContent = mm.moving ? '已成卦 · 换「✋ 直接装卦」可微调' : '六爻皆静 · 再摇一轮';
        go.disabled = !mm.moving;
        go.textContent = mm.moving ? '成卦 · 开始鉴定' : '静卦不收，再摇一轮';
      } else {
        roll.textContent = '掷第 ' + (state.manual.thrown + 1) + ' 爻';
        go.disabled = true;
        go.textContent = '还差 ' + (6 - state.manual.thrown) + ' 爻';
      }
    }
  }

  function setManualMode(m) {
    if (!state.manual) return;
    state.manual.mode = m;
    if (m === 'shake') { // 摇卦重掷；切回装卦保留摇出的卦，可微调（豆卜同款）
      state.manual.thrown = 0;
      state.manual.vals = [0, 0, 0, 0, 0, 0];
    }
    $('#segFit').classList.toggle('on', m === 'fit');
    $('#segShake').classList.toggle('on', m === 'shake');
    renderManual();
  }

  function manualRollOne() {
    if (!state.manual || state.manual.mode !== 'shake') return;
    var mm = manualLinesMoving();
    if (state.manual.thrown >= 6) {
      if (mm.moving) return; // 已成卦，等「成卦」
      state.manual.thrown = 0; // 六静重摇
      state.manual.vals = [0, 0, 0, 0, 0, 0];
      renderManual();
      return;
    }
    var backs = (Math.random() < 0.5 ? 1 : 0) + (Math.random() < 0.5 ? 1 : 0) + (Math.random() < 0.5 ? 1 : 0);
    // 3背=老阳○ 2背=少阳 1背=少阴 0背(3字)=老阴✕
    state.manual.vals[state.manual.thrown] = backs === 3 ? 2 : (backs === 2 ? 0 : (backs === 1 ? 1 : 3));
    state.manual.thrown++;
    renderManual();
  }

  function openManual() {
    /* 五十八轮（lyvia）：进来优先显示即时摇卦 */
    state.manual = { mode: 'shake', vals: [0, 0, 0, 0, 0, 0], thrown: 0 };
    $('#segFit').classList.remove('on');
    $('#segShake').classList.add('on');
    $('#manualTip').textContent = MANUAL_TIP_SHAKE;
    renderManual();
    goto('viewManual');
  }

  function manualGo() {
    var mm = manualLinesMoving();
    if (!mm.moving) { toast('选一个动爻就能成卦'); return; }
    state.numStr = ''; // 手动起卦不吃数字；数字栏下次提交再算
    state.manualCast = mm;
    startBuffer();
  }

  // 五十五轮：起卦方式进头部小字（大字报/分享卡/卦盘卡三处共用）
  function srcSuffix() {
    if (state.castSource === 'num') return ' · 数字起卦';
    if (state.castSource === 'manual') return ' · 手动起卦';
    return '';
  }

  // ── 卦图鉴（收集 64 卦；收集判定按卦名）──
  function dexLoad() {
    try {
      var raw = window.localStorage.getItem(DEX_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Object.prototype.toString.call(arr) === '[object Array]' ? arr : [];
    } catch (e) { return []; }
  }
  function dexAdd(name) {
    try {
      var arr = dexLoad();
      if (arr.indexOf(name) >= 0) return false;
      arr.push(name);
      window.localStorage.setItem(DEX_KEY, JSON.stringify(arr));
      return true;
    } catch (e) { return false; }
  }
  function dexShort(name) {
    if (name.charAt(1) === '为') return name.charAt(0);
    if (name.length === 4) return name.slice(2);
    return name.charAt(0) + name.charAt(2);
  }
  function renderDex() {
    var grid = $('#dexGrid');
    grid.textContent = '';
    var got = dexLoad();
    var names = LY.HEXAGRAM_NAMES;
    var keys = Object.keys(names);
    for (var i = 0; i < keys.length; i++) {
      var nm = names[keys[i]];
      var cell = el('div', 'dex-cell' + (got.indexOf(nm) >= 0 ? ' got' : ''));
      cell.textContent = dexShort(nm);
      grid.appendChild(cell);
    }
    $('#dexProgress').textContent = '已集 ' + got.length + ' / 64 卦' +
      (got.length >= 64 ? ' · 集齐了，嗑学出师' : ' · 还差 ' + (64 - got.length) + ' 卦集齐');
  }

  // ── 嗑学家称号（按磕过的CP对数；玩点=看你能想到多少对）──
  function cpLoad() {
    try {
      var raw = window.localStorage.getItem(CP_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Object.prototype.toString.call(arr) === '[object Array]' ? arr : [];
    } catch (e) { return []; }
  }
  function cpAdd() {
    try {
      var arr = cpLoad();
      arr.unshift({ n: state.cpName || '这对CP', g: (state.cast ? state.cast.ben_gua : ''), v: (state.reading ? state.reading.verdict : ''), t: state.cast ? state.cast.event_date : '' });
      if (arr.length > 200) arr = arr.slice(0, 200);
      window.localStorage.setItem(CP_KEY, JSON.stringify(arr));
      return arr.length;
    } catch (e) { return cpLoad().length + 1; }
  }
  var TITLES = [
    [1, '嗑学新人'], [2, '小嗑怡情'], [4, '嗑得上头'], [7, '磕百家饭'],
    [12, '职业嗑手'], [18, '嗑得饥一顿饱一顿'], [26, '嗑学家（准科学家）'],
    [36, '磕到高血糖'], [48, '嗑到晕饭了'], [64, '嗑学出师']
  ];
  function titleOf(count) {
    var name = '嗑学宗师';
    for (var i = 0; i < TITLES.length; i++) {
      if (count >= TITLES[i][0]) name = TITLES[i][1];
    }
    return name;
  }

  // ── 引导语（保存/分享后引导下一对）──
  var GUIDE = ['你还磕过谁', '你的家产就这点吗', '下一对，想试探谁', '再磕一对，称号就升级了', '嗑学之路，这才刚开始'];
  function guideMsg() {
    return GUIDE[Math.floor(Math.random() * GUIDE.length)];
  }

  // ── 卦史 ──
  function loadHistory() {
    try {
      var raw = window.localStorage.getItem(HISTORY_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Object.prototype.toString.call(arr) === '[object Array]' ? arr : [];
    } catch (e) { return []; }
  }
  function saveHistory(cast) {
    try {
      var arr = loadHistory();
      arr.unshift({
        t: cast.event_date, cat: cast.category_label,
        n: state.cpName || '', ben: cast.ben_gua, bian: cast.bian_gua,
        st: state.cpState || '', v: state.reading ? state.reading.verdict : '',
        star: cast.star, band: state.reading ? state.reading.band.label : ''
      });
      if (arr.length > 30) arr = arr.slice(0, 30);
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(arr));
    } catch (e) { /* 存储不可用时静默 */ }
  }
  function renderHistory() {
    var ul = $('#historyList');
    ul.textContent = '';
    var arr = loadHistory();
    if (!arr.length) {
      ul.appendChild(el('li', 'hist-empty', '还没有卦。摇第一卦吧。'));
      return;
    }
    for (var i = 0; i < arr.length; i++) {
      var h = arr[i];
      var li = el('li', 'hist-item');
      li.appendChild(el('span', 'hist-day', h.t));
      /* 四十一轮（lyvia）：卦史行不再标「· 已BE」——表态是她的输入不是测算结论；档里仍存 st 备用 */
      li.appendChild(el('span', 'hist-cat', (h.n ? h.n + ' · ' : '') + h.cat));
      li.appendChild(el('span', 'hist-gua', h.ben + ' → ' + h.bian));
      li.appendChild(el('span', 'hist-band', h.v + ' ' + '★'.repeat(h.star)));
      ul.appendChild(li);
    }
  }

  // ── 结果视图 ──
  var YAO_END = ['二', '三', '四', '五'];
  function yaoName(i, yang) {
    var yy = yang ? '九' : '六';
    if (i === 0) return '初' + yy;
    if (i === 5) return '上' + yy;
    return yy + YAO_END[i - 1];
  }

  function renderResult() {
    var cast = state.cast, rd = state.reading;

    /* 三十八轮（lyvia）：头部文字与大字报撞车——大字报直接顶到结果页第一位，
     * 头部整排文字（第N对/CP名/日期干支/档位大字/卦名/动爻/星级）全部并入图中，页面不再重复。
     * 画布上的字 e2e 读不到，摘要挂在海报盒 data-* 上供断言。 */
    var pBox = $('#posterBox');
    if (pBox) {
      var pImg = $('#posterInlineImg');
      if (pImg) {
        /* 四十八轮（lyvia 真机抓）：容器拦 data: 图，内嵌大字报只剩空盒——同 0904 弹层兜底，
         * img 挂失败（onerror）就克隆一份画布塞进卡里。克隆而非共用 state.posterCanvas：
         * 弹层 previewCard 会把那个节点搬进弹层，共用会互相掏空。 */
        var oldCv = pBox.querySelector('canvas');
        if (oldCv) oldCv.parentNode.removeChild(oldCv);
        pImg.className = '';
        pImg.setAttribute('alt', (state.cpName || cast.ben_gua) + '·大字报');
        pImg.setAttribute('src', ensurePoster() || ' ');
        pImg.onerror = function () {
          pImg.className = 'hidden';
          if (state.posterCanvas) {
            var cv = document.createElement('canvas');
            cv.width = state.posterCanvas.width;
            cv.height = state.posterCanvas.height;
            cv.getContext('2d').drawImage(state.posterCanvas, 0, 0);
            cv.className = 'poster-inline-canvas';
            pBox.insertBefore(cv, pImg.nextSibling);
          }
          pImg.onerror = null; // 一次 src 只该兜一次；摘掉防异常环境反复触发叠出双画布
        };
        pBox.setAttribute('data-verdict', rd.verdict);
        pBox.setAttribute('data-gua', cast.ben_gua + '→' + cast.bian_gua + '·第' + cast.moving + '爻动');
        pBox.setAttribute('data-star', '★'.repeat(cast.star) + '　' + rd.band.label);
        pBox.setAttribute('data-cat', (state.cat === 'career' ? '第' + state.cpCount + '对 · ' : '') +
          (state.cat === 'career' && state.cpName ? state.cpName : cast.category_label) +
          ' · ' + cast.event_date + '（' + cast.day_gz + '日）' +
          srcSuffix());
        pBox.setAttribute('data-title', state.cat === 'career'
          ? titleOf(state.cpCount) + ' · 嗑过的CP数量：' + state.cpCount + '对'
          : '卦图鉴 ' + dexCount() + '/64' + (state.dexNew ? ' · 新收集！' : ''));
        show(pBox);
      }
    }

    var body = $('#yaoBody');
    body.textContent = '';
    var shiPos = RD.shiPosOf(cast), yingPos = RD.yingPosOf(cast); // 三十一轮：世应角标替换用神
    for (var i = 5; i >= 0; i--) {
      var tr = el('tr', 'yao-row');
      if (i + 1 === shiPos || i + 1 === yingPos) tr.classList.add('ys');
      if (cast.moving === i + 1) tr.classList.add('mv');
      var yang = cast.lines[i] === 1;
      tr.appendChild(el('td', 'yao-name', yaoName(i, yang)));
      tr.appendChild(el('td', 'yao-glyph', yang ? '━━━━━━' : '━━　━'));
      var mid = el('td', 'yao-info', cast.liuqin[i] + ' ' + cast.lines_dz[i] + cast.lines_wx[i] +
        (cast.lines_marks[i] ? '　' + cast.lines_marks[i] : ''));
      tr.appendChild(mid);
      var tail = '';
      if (cast.moving === i + 1) tail += yang ? '○' : '✕';
      if (i + 1 === shiPos) tail += '世';
      if (i + 1 === yingPos) tail += '应';
      tr.appendChild(el('td', 'yao-tail', tail));
      body.appendChild(tr);
    }
    $('#resDay').textContent = '旬空 ' + cast.xunkong + ' · 月建 ' + cast.yuezhi +
      ' · 应爻「' + cast.lines_dz[yingPos - 1] + cast.lines_wx[yingPos - 1] + '」' +
      RD.seasonStateOf(cast.lines_wx[yingPos - 1], cast.yuezhi);

    var sum = $('#resSummary');
    sum.textContent = '';
    for (var p = 0; p < rd.summary.length; p++) {
      var lineText = rd.summary[p];
      if (!lineText) continue;
      sum.appendChild(renderPara(lineText, rd.roles ? rd.roles[p] : 'bd', rd.vdHot)); // 三十六轮只标两处；四十轮判断句高亮结论
    }

    var timing = $('#resTiming');
    timing.textContent = '';
    /* 八轮起日期并入 summary 第5行；术语 base 行撤出结果页（lyvia：难懂的句子不要） */

    var adv = $('#resAdvice');
    adv.textContent = '';
    hide($('#adviceBox'));

    /* 二十一轮的页面称号行已并入大字报（三十八轮lyvia：整页只出现一次），此处不再重复渲染 */

    $('#resFoot').textContent = rd.footnote;
    if (hasPost()) show($('#postNoteBtn')); else hide($('#postNoteBtn'));
  }
  function dexCount() { return dexLoad().length; }

  /* ── 三十六轮（lyvia）：高亮从撒词改成标位置。三十九轮收窄到“引子”，四十轮再改：
   * 判断句高亮结论短语（rd.vdHot），正文有冒号只上冒号前；金句整句保留但撤小标题，emoji 后直接接句子。
   * 卦盘卡（drawCard）用同一套角色式样，页面与卡图一个口径
   */
  var ROLE_TAGS = { gua: '🔮 卦象', vd: '💬 关系判断' };
  function elLead(text, stop) {
    var k = text.indexOf(stop);
    if (k <= 0) return null;
    return { lead: text.slice(0, k), rest: text.slice(k) };
  }
  /* 四十轮（lyvia）：判断句的高亮位=结论短语（rd.vdHot，源文本 ==标记== 拆出），不再高亮开头的引子 */
  function hotPara(text, hot) {
    var p = el('p', 'para');
    var k = hot ? text.indexOf(hot) : -1;
    if (k >= 0) {
      p.appendChild(document.createTextNode(text.slice(0, k)));
      p.appendChild(el('span', 'hl-lead', hot));
      p.appendChild(document.createTextNode(text.slice(k + hot.length)));
    } else {
      p.appendChild(document.createTextNode(text));
    }
    return p;
  }
  function renderPara(text, role, hot) {
    if (role === 'vd') {
      var box = el('div', 'hl-block hl-vd'); // 标签在块级容器上；.para 里只给结论上色（断言按行取textContent不受影响）
      box.appendChild(el('span', 'hl-tag', ROLE_TAGS.vd));
      box.appendChild(hotPara(text, hot || ''));
      return box;
    }
    if (role === 'gold') {
      var g = el('p', 'para hl-gold'); // 无小标题，emoji 后直接接金句（整句金块式样不变）
      g.appendChild(document.createTextNode('✨ ' + text));
      return g;
    }
    var p = el('p', 'para' + (role === 'gua' ? ' gua-para' : ''));
    if (role === 'gua') p.appendChild(el('span', 'sec-tag', ROLE_TAGS.gua + ' · '));
    if (role === 'bd') {
      var lr = elLead(text, '：');
      if (lr) {
        p.appendChild(el('span', 'hl-lead', lr.lead));
        p.appendChild(document.createTextNode(lr.rest));
        return p;
      }
    }
    p.appendChild(document.createTextNode(text));
    return p;
  }
  /* 卦盘卡用：按角色定字号字重与颜色（与页面同一套口径）；vd/bd 引子拆段在 drawCard 里按角色定 */
  function roleSpec(role) {
    if (role === 'gua') return { color: '#9A9A9A', bold: false, px: 21, tag: '' };
    if (role === 'vd') return { color: '#2D2D2D', bold: false, px: 24, tag: '💬 关系判断' };
    if (role === 'gold') return { color: '#9A6F08', bold: true, px: 26, tag: '', pfx: '✨ ' };
    return { color: '#2D2D2D', bold: false, px: 24, tag: '' };
  }

  // ── 卦卡（完整卦盘 Canvas）──
  function wrapLines(ctx, text, maxWidth) {
    var out = [], line = '';
    for (var i = 0; i < text.length; i++) {
      var test = line + text.charAt(i);
      if (ctx.measureText(test).width > maxWidth && line) { out.push(line); line = text.charAt(i); }
      else line = test;
    }
    if (line) out.push(line);
    return out;
  }
  /* 三十六轮：定字号字重后按整行量宽贪心折行——量与绘走同一字体，不出框 */
  function wrapUniform(ctx, text, SERIF, px, bold, maxWidth) {
    ctx.font = (bold ? 'bold ' : '') + px + 'px ' + SERIF;
    return wrapLines(ctx, text, maxWidth);
  }
  /* 三十九轮：引子混排折行——逐字量宽贪心换行，行内分段各保色保字重（量与绘同源不出框） */
  function wrapSegs(ctx, segs, SERIF, px, maxWidth) {
    var lines = [[]], x = 0;
    for (var s = 0; s < segs.length; s++) {
      var sg = segs[s];
      ctx.font = (sg.bold ? 'bold ' : '') + px + 'px ' + SERIF;
      var buf = '';
      for (var ci = 0; ci < sg.t.length; ci++) {
        var ch = sg.t.charAt(ci);
        var w = ctx.measureText(ch).width;
        if (x + w > maxWidth && buf !== '') {
          lines[lines.length - 1].push({ t: buf, color: sg.color, bold: sg.bold });
          lines.push([]); x = 0; buf = '';
        }
        buf += ch; x += w;
      }
      if (buf !== '') lines[lines.length - 1].push({ t: buf, color: sg.color, bold: sg.bold });
    }
    var out = [];
    for (var li = 0; li < lines.length; li++) if (lines[li].length) out.push(lines[li]);
    return out;
  }

  function drawCard() {
    var cast = state.cast, rd = state.reading;
    var SERIF = '"Songti SC","STSong","Noto Serif SC",serif';
    var probe = document.createElement('canvas').getContext('2d');

    // 二十五轮（lyvia）：先量内容再定画布高，全文不许出框
    // 三十六轮按角色定式样；三十九轮：金句撤标签改 emoji 前缀，vd/bd 引子拆段混排
    var sumEntries = []; // 逐视觉行：{t, px, color, bold, gap} 或 {segs, px, gap}
    for (var pi = 0; pi < rd.summary.length; pi++) {
      var role0 = rd.roles ? rd.roles[pi] : 'bd';
      var spec0 = roleSpec(role0);
      if (spec0.tag) sumEntries.push({ t: spec0.tag, px: 19, color: '#8B7EC8', bold: false, gap: 12 });
      var txt0 = rd.summary[pi];
      if (spec0.pfx) txt0 = spec0.pfx + txt0;
      var segs0 = null;
      if (role0 === 'vd' && rd.vdHot) { // 四十轮：判断句高亮结论短语（与页面同位）
        var kh = txt0.indexOf(rd.vdHot);
        if (kh >= 0) segs0 = [
          { t: txt0.slice(0, kh), color: spec0.color, bold: false },
          { t: rd.vdHot, color: '#5A4692', bold: true },
          { t: txt0.slice(kh + rd.vdHot.length), color: spec0.color, bold: false }
        ];
      } else if (role0 === 'bd') { // 三十九轮：正文只给冒号前的引子上色
        var k0 = txt0.indexOf('：');
        if (k0 > 0) segs0 = [
          { t: txt0.slice(0, k0), color: '#5A4692', bold: true },
          { t: txt0.slice(k0), color: spec0.color, bold: spec0.bold }
        ];
      }
      var ls0 = segs0 ? wrapSegs(probe, segs0, SERIF, spec0.px, 570)
        : wrapUniform(probe, txt0, SERIF, spec0.px, spec0.bold, 570);
      for (var li0 = 0; li0 < ls0.length; li0++) {
        sumEntries.push(segs0
          ? { segs: ls0[li0], px: spec0.px, gap: 0 }
          : { t: ls0[li0], px: spec0.px, color: spec0.color, bold: spec0.bold, gap: 0 });
      }
      sumEntries[sumEntries.length - 1].gap = 14; // 段后留白，分段读
    }
    var yaoTop = 296;
    var syStart = yaoTop + 240 + 58;          // 6爻行后＋星级行
    var sumH = 0;
    for (var si0 = 0; si0 < sumEntries.length; si0++) sumH += 38 + sumEntries[si0].gap;
    probe.font = '19px ' + SERIF;
    var footLines = wrapLines(probe, rd.footnote, 590).slice(0, 3);
    var footH = footLines.length * 26 + 44;   // +26 给底部 idolship · 豆卜 品牌行（三十五轮lyvia）
    var MAXH = 1800;
    var total = Math.min(MAXH, Math.max(960, syStart + sumH + footH + 40));
    var maxSumH = total - syStart - footH - 40;
    var lineH = sumH > maxSumH ? Math.max(30, Math.floor(maxSumH / sumEntries.length)) : 38; // 顶到上限压行距不压字号

    var cv = document.createElement('canvas');
    cv.width = 1440; cv.height = total * 2; // 五十四轮（lyvia 真机：图糊）：2 倍分辨率渲染，绘制坐标照旧
    var ctx = cv.getContext('2d');
    ctx.scale(2, 2);

    ctx.fillStyle = '#FFF9F0';
    ctx.fillRect(0, 0, 720, total);
    ctx.strokeStyle = '#8B7EC8';
    ctx.lineWidth = 4;
    ctx.strokeRect(14, 14, 692, total - 28);
    ctx.strokeStyle = '#FF9E6C';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(24, 24, 672, total - 48);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#6B5DA8';
    ctx.font = '34px ' + SERIF;
    ctx.fillText('真假CP鉴定器', 360, 86);
    ctx.fillStyle = '#9E9E9E';
    ctx.font = '23px ' + SERIF;
    var p = cast.event_date.split('-');
    var line2 = Number(p[1]) + '月' + Number(p[2]) + '日 · ' + cast.day_gz + '日 · 问' + cast.category_label;
    /* 四十一轮（lyvia）：分享卡头部同样撤「已BE」——同大字报，表态不进头部小字 */
    if (state.cat === 'career' && state.cpName) line2 = Number(p[1]) + '月' + Number(p[2]) + '日 · ' + state.cpName +
      srcSuffix();
    ctx.fillText(line2, 360, 122);

    ctx.fillStyle = '#2D2D2D';
    ctx.font = '58px ' + SERIF;
    ctx.fillText(cast.ben_gua, 360, 196);
    ctx.fillStyle = '#8B7EC8';
    ctx.font = '26px ' + SERIF;
    ctx.fillText('第' + cast.moving + '爻动 · 变「' + cast.bian_gua + '」', 360, 232);

    ctx.strokeStyle = '#FFD4A8';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(70, 258); ctx.lineTo(650, 258); ctx.stroke();

    ctx.textAlign = 'left';
    var y = yaoTop;
    var cShi = RD.shiPosOf(cast), cYing = RD.yingPosOf(cast); // 三十一轮：卡图角标世/应
    for (var i = 5; i >= 0; i--) {
      var yang = cast.lines[i] === 1;
      var isYs = (i + 1 === cShi || i + 1 === cYing);
      var isMv = cast.moving === i + 1;
      if (isYs) { ctx.fillStyle = 'rgba(255,158,108,0.16)'; ctx.fillRect(60, y - 24, 600, 34); }
      ctx.fillStyle = isYs ? '#E07A3E' : '#2D2D2D';
      ctx.font = '25px ' + SERIF;
      var marks = cast.lines_marks[i] ? '　' + cast.lines_marks[i] : '';
      var tail = (isMv ? (yang ? '○' : '✕') : '') + (i + 1 === cShi ? ' ·世' : '') + (i + 1 === cYing ? ' ·应' : '');
      ctx.textAlign = 'left';
      ctx.fillText(yaoName(i, yang), 76, y);
      ctx.fillText(yang ? '━━━━━━' : '━━　━', 146, y);
      ctx.fillText(cast.liuqin[i] + cast.lines_dz[i] + cast.lines_wx[i] + marks + tail, 330, y);
      y += 40;
    }

    ctx.textAlign = 'center';
    ctx.fillStyle = '#FF9E6C';
    ctx.font = '30px ' + SERIF;
    ctx.fillText('★'.repeat(cast.star) + '　' + rd.verdict, 360, y + 16);

    /* 三十六轮标位置；三十九轮：引子混排行（segs）逐段上色，其余整行一式 */
    ctx.textAlign = 'left';
    var sy = syStart;
    for (var ei = 0; ei < sumEntries.length; ei++) {
      var en = sumEntries[ei];
      var sx = 70;
      if (en.segs) {
        for (var gi = 0; gi < en.segs.length; gi++) {
          var sg = en.segs[gi];
          ctx.fillStyle = sg.color;
          ctx.font = (sg.bold ? 'bold ' : '') + en.px + 'px ' + SERIF;
          ctx.fillText(sg.t, sx, sy);
          sx += ctx.measureText(sg.t).width;
        }
      } else {
        ctx.fillStyle = en.color;
        ctx.font = (en.bold ? 'bold ' : '') + en.px + 'px ' + SERIF;
        ctx.fillText(en.t, sx, sy);
      }
      sy += lineH + en.gap;
    }

    ctx.textAlign = 'center';
    ctx.fillStyle = '#9E9E9E';
    ctx.font = '19px ' + SERIF;
    var fy = total - 70 - (footLines.length - 1) * 26;
    for (var fi = 0; fi < footLines.length; fi++) {
      ctx.fillText(footLines[fi], 360, fy);
      fy += 26;
    }
    ctx.fillStyle = '#B9AEDE'; // 每页底端软性品牌行（三十五轮lyvia）
    ctx.font = '18px ' + SERIF;
    ctx.fillText('idolship · 豆卜', 360, total - 40);
    /* 五十四轮（lyvia 真机：图糊）：不再缩 600 宽；旧 100KB 红线是旧分享链路的，
     * 现在 writeTempFile/postNote 直收 data uri，放宽到 1.2MB 顶＋阶梯降质兜底 */
    state.cardCanvas = cv;
    var uri = '';
    var qs = [0.82, 0.76, 0.7, 0.62, 0.55];
    for (var qi2 = 0; qi2 < qs.length; qi2++) {
      var u2 = '';
      try { u2 = cv.toDataURL('image/jpeg', qs[qi2]); } catch (eQ) { u2 = ''; }
      if (u2.indexOf('data:image') === 0 && u2.length < 1200000) { uri = u2; break; }
    }
    if (!uri) { try { uri = cv.toDataURL('image/jpeg', 0.5); } catch (eF) { uri = ''; } }
    if (uri.indexOf('data:image') !== 0) uri = '';
    return uri;
  }

  function ensureCard() {
    if (!state.cardCanvas) state.cardUri = drawCard();
    return state.cardUri;
  }

  // ── 大字报（分享主物料）：CP名 + 档位大字 + 金句 + 称号 ──
  function drawPoster() {
    var cast = state.cast, rd = state.reading;
    var p = RD.posterFor(cast, rd);
    var cv = document.createElement('canvas');
    cv.width = 1440; cv.height = 1920; // 五十四轮：2 倍分辨率渲染
    var ctx = cv.getContext('2d');
    ctx.scale(2, 2);
    var SERIF = '"Songti SC","STSong","Noto Serif SC",serif';
    var bandColor = rd.band.key === 'high' ? '#4CAF50' : (rd.band.key === 'mid' ? '#FF9E6C' : '#E57373');

    ctx.fillStyle = '#FFF9F0';
    ctx.fillRect(0, 0, 720, 960);
    ctx.strokeStyle = '#8B7EC8';
    ctx.lineWidth = 4;
    ctx.strokeRect(14, 14, 692, 932);
    ctx.strokeStyle = '#FF9E6C';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(24, 24, 672, 912);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#6B5DA8';
    ctx.font = '30px ' + SERIF;
    ctx.fillText('真假CP鉴定器', 360, 92);
    var dt = cast.event_date.split('-');
    ctx.fillStyle = '#9E9E9E';
    ctx.font = '22px ' + SERIF;
    /* 四十一轮（lyvia）：头部小字撤掉「已BE局」——那是她自己的表态，不是测算结果，
     * 钉在大字报最上面会像工具算出来的结论；关系判断只留在解读正文里（「已经BE」引号引用）。 */
    var meta = Number(dt[1]) + '月' + Number(dt[2]) + '日 · ' + cast.day_gz + '日' +
      srcSuffix() +
      (state.cat === 'career' ? ' · 第' + state.cpCount + '对' : '');
    ctx.fillText(meta, 360, 126);

    // CP名（有就上卡）
    var nameY = 0;
    if (state.cat === 'career' && state.cpName) {
      ctx.fillStyle = '#2D2D2D';
      ctx.font = '44px ' + SERIF;
      var nm = state.cpName.length > 12 ? state.cpName.slice(0, 12) : state.cpName;
      ctx.fillText(nm, 360, 206);
      nameY = 206;
    }

    // 结论大字（按字数自适应字号）
    var bigSize = p.big.length <= 3 ? 128 : (p.big.length === 4 ? 108 : (p.big.length === 5 ? 92 : 74));
    ctx.fillStyle = bandColor;
    ctx.font = 'bold ' + bigSize + 'px ' + SERIF;
    var bigY = (nameY ? nameY + 158 : 380);
    ctx.fillText(p.big, 360, bigY);

    ctx.strokeStyle = '#FF9E6C';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(250, bigY + 52); ctx.lineTo(470, bigY + 52); ctx.stroke();

    ctx.fillStyle = '#FF9E6C';
    ctx.font = '30px ' + SERIF;
    ctx.fillText('★'.repeat(cast.star) + '　' + rd.band.label, 360, bigY + 106);

    ctx.fillStyle = '#6B5DA8';
    ctx.font = '26px ' + SERIF;
    ctx.fillText(cast.ben_gua + ' → ' + cast.bian_gua + ' · 第' + cast.moving + '爻动', 360, bigY + 168);

    ctx.fillStyle = '#757575';
    ctx.font = '30px ' + SERIF;
    var ql = wrapLines(ctx, '「' + p.quote + '」', 560);
    var qy = bigY + 236;
    for (var qi = 0; qi < Math.min(ql.length, 2); qi++) {
      ctx.fillText(ql[qi], 360, qy);
      qy += 44;
    }

    // 称号行（二十一轮：获得称号 / 大字称号 / 嗑过的CP数量）
    if (state.cat === 'career') {
      ctx.fillStyle = '#9E9E9E';
      ctx.font = '20px ' + SERIF;
      ctx.fillText('获得称号', 360, qy + 34);
      ctx.fillStyle = '#E57373';
      ctx.font = 'bold 34px ' + SERIF;
      ctx.fillText('【' + titleOf(state.cpCount) + '】', 360, qy + 76);
      ctx.fillStyle = '#9E9E9E';
      ctx.font = '22px ' + SERIF;
      ctx.fillText('嗑过的CP数量：' + state.cpCount + '对', 360, qy + 112);
    }

    ctx.fillStyle = '#9E9E9E';
    ctx.font = '19px ' + SERIF;
    ctx.fillText('纯本地趣味鉴定 · 不构成对任何真实人物的判断', 360, 884);
    ctx.fillStyle = '#B9AEDE'; // 每页底端软性品牌行（三十五轮lyvia）
    ctx.font = '18px ' + SERIF;
    ctx.fillText('idolship · 豆卜', 360, 916);

    state.posterCanvas = cv; // 五十四轮：2 倍直出不再缩 600 宽
    var uri = '';
    try { uri = cv.toDataURL('image/jpeg', 0.82); } catch (e) { uri = ''; }
    if (uri.indexOf('data:image') !== 0) uri = '';
    return uri;
  }

  function ensurePoster() {
    if (!state.posterCanvas) state.posterUri = drawPoster();
    return state.posterUri;
  }

  /* 五十四轮（lyvia）：发笔记要带「测算历史」页——集齐多少卦、最近嗑过谁，一眼看到养成感 */
  function drawHistoryPoster() {
    var arr = loadHistory();
    var cv = document.createElement('canvas');
    cv.width = 1440; cv.height = 1920;
    var ctx = cv.getContext('2d');
    ctx.scale(2, 2);
    var SERIF = '"Songti SC","STSong","Noto Serif SC",serif';

    ctx.fillStyle = '#FFF9F0';
    ctx.fillRect(0, 0, 720, 960);
    ctx.strokeStyle = '#8B7EC8';
    ctx.lineWidth = 4;
    ctx.strokeRect(14, 14, 692, 932);
    ctx.strokeStyle = '#FF9E6C';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(24, 24, 672, 912);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#6B5DA8';
    ctx.font = '34px ' + SERIF;
    ctx.fillText('真假CP鉴定器', 360, 92);
    ctx.fillStyle = '#9E9E9E';
    ctx.font = '22px ' + SERIF;
    ctx.fillText('我的测算档案', 360, 126);

    ctx.fillStyle = '#E07A3E';
    ctx.font = 'bold 40px ' + SERIF;
    ctx.fillText('已收录 ' + dexCount() + '/64 卦', 360, 172);
    ctx.fillStyle = '#757575';
    ctx.font = '20px ' + SERIF;
    var cpPairs = 0;
    for (var ci = 0; ci < arr.length; ci++) { if (arr[ci].n) cpPairs++; }
    var sub = '卦史共 ' + arr.length + ' 条';
    if (cpPairs > 0) sub = '嗑过 ' + Math.max(cpPairs, state.cat === 'career' ? state.cpCount : 0) + ' 对CP · ' + sub;
    ctx.fillText(sub, 360, 202);

    /* 六十轮（lyvia）：第三张图=「卦史」页完整内容——八卦图鉴 64 格 + 最近卦史 */
    ctx.textAlign = 'center';
    ctx.fillStyle = '#5A4692';
    ctx.font = 'bold 24px ' + SERIF;
    ctx.fillText('八卦图鉴', 360, 236);
    var got = dexLoad();
    var names = LY.HEXAGRAM_NAMES;
    var keys = Object.keys(names);
    var cw = 62, chh = 38, gx = 112, gy = 252;
    for (var gi = 0; gi < keys.length; gi++) {
      var col = gi % 8, row = Math.floor(gi / 8);
      var cx = gx + col * cw, cyy = gy + row * chh;
      var nm = names[keys[gi]];
      var isGot = got.indexOf(nm) >= 0;
      ctx.fillStyle = isGot ? '#F3EEFB' : '#FFFDF9';
      ctx.fillRect(cx + 2, cyy + 2, cw - 4, chh - 4);
      ctx.strokeStyle = isGot ? '#8B7EC8' : '#F0ECE4';
      ctx.lineWidth = 1;
      ctx.strokeRect(cx + 2, cyy + 2, cw - 4, chh - 4);
      ctx.fillStyle = isGot ? '#5A4692' : '#C9C2B6';
      ctx.font = (isGot ? 'bold ' : '') + '15px ' + SERIF;
      ctx.fillText(dexShort(nm), cx + cw / 2, cyy + chh / 2 + 5);
    }

    ctx.textAlign = 'center';
    ctx.fillStyle = '#5A4692';
    ctx.font = 'bold 24px ' + SERIF;
    ctx.fillText('最近卦史', 360, 592);
    if (!arr.length) {
      ctx.fillStyle = '#9E9E9E';
      ctx.font = '24px ' + SERIF;
      ctx.fillText('还没有卦，摇第一卦吧', 360, 700);
    } else {
      ctx.textAlign = 'left';
      var hy = 622;
      for (var hi = 0; hi < arr.length && hi < 4; hi++) {
        var h = arr[hi];
        var day = (h.t || '').slice(5);
        var who = h.n ? (h.n.length > 6 ? h.n.slice(0, 6) : h.n) : h.cat;
        ctx.fillStyle = '#B9AEDE';
        ctx.font = '16px ' + SERIF;
        ctx.fillText(day, 76, hy);
        ctx.fillStyle = hi === 0 ? '#E07A3E' : '#2D2D2D';
        ctx.font = 'bold 19px ' + SERIF;
        ctx.fillText(who, 142, hy);
        ctx.fillStyle = '#6B5DA8';
        ctx.font = '16px ' + SERIF;
        ctx.fillText(h.ben + '→' + h.bian, 288, hy);
        ctx.fillStyle = '#E07A3E';
        ctx.font = '16px ' + SERIF;
        ctx.textAlign = 'right';
        ctx.fillText(h.v + ' ' + '★'.repeat(h.star), 644, hy);
        ctx.textAlign = 'left';
        ctx.strokeStyle = '#F3E8D7';
        ctx.beginPath(); ctx.moveTo(76, hy + 22); ctx.lineTo(644, hy + 22); ctx.stroke();
        hy += 44;
      }
    }

    ctx.textAlign = 'center';
    ctx.fillStyle = '#5A4692';
    ctx.font = '24px ' + SERIF;
    ctx.fillText('你也来测测：你磕的CP是真是假？', 360, 852);
    ctx.fillStyle = '#9E9E9E';
    ctx.font = '19px ' + SERIF;
    ctx.fillText('纯本地趣味鉴定 · 不构成对任何真实人物的判断', 360, 884);
    ctx.fillStyle = '#B9AEDE';
    ctx.font = '18px ' + SERIF;
    ctx.fillText('idolship · 豆卜', 360, 916);
    return cv.toDataURL('image/jpeg', 0.82);
  }
  function ensureHistory() {
    if (!state.historyUri) state.historyUri = drawHistoryPoster();
    return state.historyUri;
  }

  // 预览必出：data: 图若被容器拦（img 加载失败），直接把画布节点挂上去，保证看得到图
  function previewCard(uri, cv) {
    var img = $('#cardImg');
    var holder = $('#cardCanvas');
    state.previewUri = uri; // 五十轮：弹层「发笔记分享」按当前预览的图发
    img.className = '';
    img.setAttribute('src', uri || ' ');
    var sb = $('#cardShareBtn');
    if (sb) show(sb); // 五十一轮：提示承诺了这个按钮就常亮；没接口时点了给诊断 toast
    var ch = $('#cardHint'); // 五十二轮：无桥时提示同步改「截图即存」，不悬空承诺
    if (ch) ch.textContent = hasPost() ? '点下面「发笔记保存全部历史图鉴」，大字报·卦盘·历史图鉴一次带走' : '截图即可保存这张图';
    if (holder) {
      holder.textContent = '';
      holder.className = 'hidden';
      img.onerror = function () {
        img.className = 'hidden';
        if (cv) { cv.className = 'card-canvas'; holder.appendChild(cv); }
        holder.className = '';
      };
    }
    show($('#cardMask'));
  }

  /* 四十九轮（lyvia 真机抓：大字报保存不了）：官方规范（vendor jsbridge-api.md）推荐
   * 「已有 base64 先 writeTempFile 换本地 filePath 再存相册」，原样直传 data:uri 是允许
   * 但非推荐路径，真机大串 base64 有被容器拒掉的风险。这里规范路径优先，老容器没有
   * writeTempFile 时退回直传。权限弹窗只在这一刻触发（规范：需用户主动操作触发），
   * 打开小工具不会问——表单「所需权限」只是静态声明。 */
  function saveToAlbum(uri, quiet) {
    if (!hasSave()) {
      /* 五十二轮（诊断闭环：她真机 toast=「xhs未注入」）：这版内测容器整个没注入桥，
       * 报错腔吓用户——改用户视角：截图即存；接口缺失的细节只留给桥在但接口缺的分支 */
      toast(mt() ? '没找到存图接口(saveImageToPhotosAlbum缺)，可截图分享' : '这版容器还没开存图接口，截图即可保存', 5200);
      return Promise.resolve(false);
    }
    var b = mt(); // 点击时现取（容器可能晚注入）
    var step = typeof b.writeTempFile === 'function'
      ? b.writeTempFile({ data: uri }).then(function (res) {
          return res && res.filePath ? res.filePath : uri;
        })
      : Promise.resolve(uri);
    return step.then(function (filePath) {
      return b.saveImageToPhotosAlbum({ filePath: filePath });
    }).then(function () {
      /* 五十四轮（lyvia）：已授权就不再弹权限窗——成功必须自己说话；
       * 五十六轮：三张打包存时安静，存完统一报一次，不连弹三条 */
      if (!quiet) toast('已保存到相册，去手机相册查看', 2600);
      return true;
    }).catch(function (err) {
      /* 五十轮（lyvia 真机：上架后仍存不了）：容器把系统长按菜单禁了（规范§4），
       * 存相册是唯一存图路——失败必须把原因带出来（errMsg 截尾），否则远程没法诊断；
       * 同时指到发笔记分享（弹层里新增按钮），产品不至于「只能干看着」。 */
      var why = err && err.errMsg ? String(err.errMsg).slice(-36) : '';
      if (!quiet) toast(why ? '没存上(' + why + ')，可截图或发笔记' : '没存上，可截图或发笔记', 5200);
      return false;
    });
  }

  /* 五十七轮（lyvia）：存图拆回单张——「存本次完整卦盘」「存本次大字海报」各管各的；
   * 全套带走（大字报+卦盘+历史图鉴）只走发笔记主按钮 */
  function onSaveCardImg() {
    var uri;
    try { uri = ensureCard(); } catch (e) { toast('图还没生成好，稍后再试'); return; }
    saveToAlbum(uri);
  }
  function onSavePosterImg() {
    var uri;
    try { uri = ensurePoster(); } catch (e) { toast('图还没生成好，稍后再试'); return; }
    saveToAlbum(uri);
  }

  function onSavePoster() {
    var uri = ensurePoster();
    previewCard(uri, state.posterCanvas);
    saveToAlbum(uri);
  }

  function postNoteWith(uris) {
    var b = mt();
    if (!b || typeof b.postNote !== 'function') {
      toast(mt() ? '没找到发笔记接口(postNote缺)，可截图分享' : '这版容器还没开发笔记接口，可截图分享', 5200);
      return;
    }
    /* 五十四轮：发笔记=三张图打包（大字报+完整卦盘+测算历史）。
     * 五十六轮（lyvia 拍板）：没人因为「玩了个工具」想发笔记——标题给悬念，正文只给邀请；
     * 卦曰/金句/卦象/卦史全撤出文案（都在三张图里），「引用原笔记」是她发布页的手动动作。 */
    if (!uris || !uris.length) uris = [ensurePoster(), ensureCard(), ensureHistory()];
    var rd = state.reading;
    var isCp = state.cat === 'career' && !!state.cpName;
    var ptitle = isCp ? '竟然，我的CP竟然是这种关系'
      : (rd && rd.verdict ? '我摇出一卦：「' + rd.verdict + '」' : '竟然，一卦摇出这种答案');
    if (ptitle.length > 20) ptitle = ptitle.slice(0, 20); // 容器文档：title 最长 20
    b.postNote({
      title: ptitle,
      content: '你来测测你磕的CP是真是假吧👇\n小工具就挂在这篇笔记下面，点开就能测',
      pageType: 'photo_publish',
      mediaInfo: { image_resources: uris.map(function (u) { return { url: u }; }) }
    }).then(function () {
      /* 真机：跳发布页本身就是反馈，保持安静 */
    }).catch(function () {
      toast('发布没完成，可截图分享');
    });
  }

  function onPostNote() {
    postNoteWith(); // 五十四轮：三张图打包；无桥时 postNoteWith 自己给诊断 toast
  }

  // ── 说明弹层 ──
  function openAbout() { show($('#sheetMask')); }
  function closeAbout() { hide($('#sheetMask')); }

  // ── 事件绑定 ──
  function bind() {
    var btn = $('#shakeBtn');
    btn.addEventListener('pointerdown', startShake);
    btn.addEventListener('pointerup', endShake);
    btn.addEventListener('pointercancel', endShake);
    btn.addEventListener('pointerleave', endShake);
    btn.addEventListener('contextmenu', function (e) { e.preventDefault(); });

    $('#aboutBtn').addEventListener('click', openAbout);
    $('#aboutClose').addEventListener('click', closeAbout);
    $('#sheetMask').addEventListener('click', function (e) {
      if (e.target === $('#sheetMask')) closeAbout();
    });
    $('#cardClose').addEventListener('click', function () { hide($('#cardMask')); });
    var shareBtn = $('#cardShareBtn');
    if (shareBtn) shareBtn.addEventListener('click', function () {
      hide($('#cardMask'));
      postNoteWith(); // 五十四轮：同样三张图打包；无桥时给诊断 toast
    });
    $('#cardMask').addEventListener('click', function (e) {
      if (e.target === $('#cardMask')) hide($('#cardMask'));
    });

    $('#stateBack').addEventListener('click', function () { goto('viewChoose'); });
    $('#skipStateBtn').addEventListener('click', function () { state.cpState = ''; gotoInput(); }); // 十四轮：跳过表态，卦直说
    $('#inputStart').addEventListener('click', submitInput);
    $('#inputBack').addEventListener('click', function () { goto('viewState'); });
    $('#manualEntryBtn').addEventListener('click', openManual); // 五十五轮：手动起卦
    $('#manualBack').addEventListener('click', function () { goto('viewInput'); });
    $('#segFit').addEventListener('click', function () { setManualMode('fit'); });
    $('#segShake').addEventListener('click', function () { setManualMode('shake'); });
    $('#manualRollBtn').addEventListener('click', manualRollOne);
    $('#manualReset').addEventListener('click', function () {
      if (!state.manual) return;
      state.manual.thrown = 0;
      state.manual.vals = [0, 0, 0, 0, 0, 0];
      renderManual();
    });
    $('#manualGo').addEventListener('click', manualGo);
    $('#castNumInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') submitInput();
    });
    $('#cpNameInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') submitInput();
    });

    $('#saveCardBtn').addEventListener('click', onSaveCardImg); // 五十七轮：单存本次完整卦盘
    $('#savePosterBtn').addEventListener('click', onSavePosterImg); // 五十七轮：单存本次大字海报
    $('#postNoteBtn').addEventListener('click', onPostNote);
    var inlinePoster = $('#posterBox'); // 三十七轮：点前置大字报=打开保存预览；四十八轮改绑盒子——兜底 canvas 也要能点开
    if (inlinePoster) inlinePoster.addEventListener('click', onSavePoster);
    $('#againBtn').addEventListener('click', function () {
      if (state.cat === 'career') { goto('viewInput'); }
      else { resetCoins(); goto('viewCast'); }
    });
    $('#backChoose1').addEventListener('click', function () { goto('viewOther'); });
    $('#backChoose2').addEventListener('click', function () { goto('viewChoose'); });
    $('#startCpBtn').addEventListener('click', function () { pickCat('career'); });
    $('#otherBtn').addEventListener('click', function () { goto('viewOther'); });
    $('#otherBack').addEventListener('click', function () { goto('viewChoose'); });
    $('#historyBtn').addEventListener('click', function () { renderDex(); renderHistory(); goto('viewHistory'); });
    $('#historyBack').addEventListener('click', function () { goto(state.cast ? 'viewResult' : 'viewChoose'); });
  }

  function init() {
    buildOtherList();
    bind();
    goto('viewChoose');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
