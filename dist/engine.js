/* 豆卜·离线精简版 — 六爻引擎（自线上 idol-astro/liuyao.py 1:1 移植, 0903 快照）
 * 经典脚本 / ES2017 上限 / 无网络 / window.LiuYao 命名空间
 * 一致性基准: tests/consistency_check.py 对照 ref/liuyao.py
 */
(function () {
  'use strict';

  // ── 先天八卦 ──
  var BAGUA = {
    1: { name: '乾', wx: '金', lines: [1, 1, 1], symbol: '☰', nature: '天' },
    2: { name: '兑', wx: '金', lines: [1, 1, 0], symbol: '☱', nature: '泽' },
    3: { name: '离', wx: '火', lines: [1, 0, 1], symbol: '☲', nature: '火' },
    4: { name: '震', wx: '木', lines: [1, 0, 0], symbol: '☳', nature: '雷' },
    5: { name: '巽', wx: '木', lines: [0, 1, 1], symbol: '☴', nature: '风' },
    6: { name: '坎', wx: '水', lines: [0, 1, 0], symbol: '☵', nature: '水' },
    7: { name: '艮', wx: '土', lines: [0, 0, 1], symbol: '☶', nature: '山' },
    8: { name: '坤', wx: '土', lines: [0, 0, 0], symbol: '☷', nature: '地' }
  };

  // ── 64 卦名 key='上,下' ──
  var HEXAGRAM_NAMES = {
    '1,1': '乾为天', '1,2': '天泽履', '1,3': '天火同人', '1,4': '天雷无妄',
    '1,5': '天风姤', '1,6': '天水讼', '1,7': '天山遁', '1,8': '天地否',
    '2,1': '泽天夬', '2,2': '兑为泽', '2,3': '泽火革', '2,4': '泽雷随',
    '2,5': '泽风大过', '2,6': '泽水困', '2,7': '泽山咸', '2,8': '泽地萃',
    '3,1': '火天大有', '3,2': '火泽睽', '3,3': '离为火', '3,4': '火雷噬嗑',
    '3,5': '火风鼎', '3,6': '火水未济', '3,7': '火山旅', '3,8': '火地晋',
    '4,1': '雷天大壮', '4,2': '雷泽归妹', '4,3': '雷火丰', '4,4': '震为雷',
    '4,5': '雷风恒', '4,6': '雷水解', '4,7': '雷山小过', '4,8': '雷地豫',
    '5,1': '风天小畜', '5,2': '风泽中孚', '5,3': '风火家人', '5,4': '风雷益',
    '5,5': '巽为风', '5,6': '风水涣', '5,7': '风山渐', '5,8': '风地观',
    '6,1': '水天需', '6,2': '水泽节', '6,3': '水火既济', '6,4': '水雷屯',
    '6,5': '水风井', '6,6': '坎为水', '6,7': '水山蹇', '6,8': '水地比',
    '7,1': '山天大畜', '7,2': '山泽损', '7,3': '山火贲', '7,4': '山雷颐',
    '7,5': '山风蛊', '7,6': '山水蒙', '7,7': '艮为山', '7,8': '山地剥',
    '8,1': '地天泰', '8,2': '地泽临', '8,3': '地火明夷', '8,4': '地雷复',
    '8,5': '地风升', '8,6': '地水师', '8,7': '地山谦', '8,8': '坤为地'
  };

  // ── 京房八宫五行 ──
  var PALACE_WX = {
    '1,1': '金', '1,5': '金', '1,7': '金', '1,8': '金', '5,8': '金', '7,8': '金', '3,8': '金', '3,1': '金',
    '2,2': '金', '2,6': '金', '2,8': '金', '2,7': '金', '6,7': '金', '8,7': '金', '4,7': '金', '4,2': '金',
    '3,3': '火', '3,7': '火', '3,5': '火', '3,6': '火', '7,6': '火', '5,6': '火', '1,6': '火', '1,3': '火',
    '4,4': '木', '4,8': '木', '4,6': '木', '4,5': '木', '8,5': '木', '6,5': '木', '2,5': '木', '2,4': '木',
    '5,5': '木', '5,1': '木', '5,3': '木', '5,4': '木', '1,4': '木', '3,4': '木', '7,4': '木', '7,5': '木',
    '6,6': '水', '6,2': '水', '6,4': '水', '6,3': '水', '2,3': '水', '4,3': '水', '8,3': '水', '8,6': '水',
    '7,7': '土', '7,3': '土', '7,1': '土', '7,2': '土', '3,2': '土', '1,2': '土', '5,2': '土', '5,7': '土',
    '8,8': '土', '8,4': '土', '8,2': '土', '8,1': '土', '4,1': '土', '2,1': '土', '6,1': '土', '6,8': '土'
  };

  // ── 卦辞 ──
  var HEXAGRAM_TEXT = {
    '乾为天': '元亨利贞，刚健中正，大吉之卦',
    '坤为地': '厚德载物，柔顺包容，宜静守',
    '水雷屯': '初难后解，需耐心待时',
    '山水蒙': '蒙昧求明，宜请教学习',
    '水天需': '等待时机，密云不雨',
    '天水讼': '争讼是非，宜和解',
    '地水师': '统率有方，谋略可行',
    '水地比': '亲附团结，人际和谐',
    '风天小畜': '小有积蓄，力量初聚',
    '天泽履': '踩虎尾不咥人，慎行无害',
    '地天泰': '天地交泰，万事通达，大吉',
    '天地否': '天地不交，闭塞不顺',
    '天火同人': '同心同德，人际和谐，吉',
    '火天大有': '大有所获，盛大有成，吉',
    '地山谦': '谦逊低调，可保长久',
    '雷地豫': '欢乐愉悦，利于行动',
    '泽雷随': '随顺时机，变通为宜',
    '山风蛊': '积弊需治，整饬革新',
    '地泽临': '居高临下，势有所成',
    '风地观': '观察体悟，宜静观',
    '火雷噬嗑': '咬合障碍，需努力突破',
    '山火贲': '修饰文采，表面光鲜',
    '山地剥': '剥落衰败，宜守不宜进',
    '地雷复': '一阳来复，转机初现，吉',
    '天雷无妄': '守正勿妄，无往不利',
    '山天大畜': '大有所蓄，积聚力量，吉',
    '山雷颐': '养身养德，正道养育',
    '泽风大过': '负担过重，量力而行',
    '坎为水': '重险重叠，宜谨慎',
    '离为火': '光明附丽，宜有所为',
    '泽山咸': '感应相合，情意相通，吉',
    '雷风恒': '持之以恒，长久不变',
    '天山遁': '退避隐遁，宜暂时抽身',
    '雷天大壮': '声势浩大，刚强有力',
    '火地晋': '晋升上进，光明前行，吉',
    '地火明夷': '光明受伤，宜韬光养晦',
    '风火家人': '家人同心，内务和睦，吉',
    '火泽睽': '乖违背离，事有违逆',
    '水山蹇': '行路艰难，进退两难',
    '雷水解': '险难消解，困局得舒，吉',
    '山泽损': '减损奉献，先难后易',
    '风雷益': '有所增益，利有攸往，吉',
    '泽天夬': '果决断除，需果断行事',
    '天风姤': '不期而遇，防小人',
    '泽地萃': '人才聚集，汇萃一堂，吉',
    '地风升': '顺势上升，步步高升，吉',
    '泽水困': '困境受围，宜守拙待时',
    '水风井': '井养不穷，源源不绝',
    '泽火革': '变革革新，去故取新',
    '火风鼎': '鼎新树立，稳固成器，吉',
    '震为雷': '震动惊醒，处变不惊',
    '艮为山': '适时停止，宜静守',
    '风山渐': '循序渐进，稳步推进，吉',
    '雷泽归妹': '位置不正，宜守本分',
    '雷火丰': '丰盛圆满，盛极需慎',
    '火山旅': '行旅在外，宜随遇而安',
    '巽为风': '柔顺渗透，顺风进退',
    '兑为泽': '喜悦相随，和悦相处，吉',
    '风水涣': '涣散消解，宜重新凝聚',
    '水泽节': '节制有度，适可而止',
    '风泽中孚': '诚信中肯，感人肺腑，吉',
    '雷山小过': '小有过越，宜小不宜大',
    '水火既济': '已成定局，宜防患未然',
    '火水未济': '尚未完成，需继续推进'
  };

  // ── 干支 / 冲合刑害 ──
  var GAN = '甲乙丙丁戊己庚辛壬癸';
  var ZHI_ALL = '子丑寅卯辰巳午未申酉戌亥';
  var CHONG = { 子: '午', 午: '子', 丑: '未', 未: '丑', 寅: '申', 申: '寅', 卯: '酉', 酉: '卯', 辰: '戌', 戌: '辰', 巳: '亥', 亥: '巳' };
  var LIUHE = { 子: '丑', 丑: '子', 寅: '亥', 亥: '寅', 卯: '戌', 戌: '卯', 辰: '酉', 酉: '辰', 巳: '申', 申: '巳', 午: '未', 未: '午' };
  var HAI = { 子: '未', 未: '子', 丑: '午', 午: '丑', 寅: '巳', 巳: '寅', 卯: '辰', 辰: '卯', 申: '亥', 亥: '申', 酉: '戌', 戌: '酉' };
  var ZHI_WX = { 子: '水', 丑: '土', 寅: '木', 卯: '木', 辰: '土', 巳: '火', 午: '火', 未: '土', 申: '金', 酉: '金', 戌: '土', 亥: '水' };
  var WX_SHENG = { 金: '水', 水: '木', 木: '火', 火: '土', 土: '金' };
  var WX_KE = { 金: '木', 木: '土', 土: '水', 水: '火', 火: '金' };
  var XING_PAIRS = {
    '寅巳': 1, '巳寅': 1, '巳申': 1, '申巳': 1, '申寅': 1, '寅申': 1,
    '丑戌': 1, '戌丑': 1, '戌未': 1, '未戌': 1, '未丑': 1, '丑未': 1,
    '子卯': 1, '卯子': 1, '辰辰': 1, '午午': 1, '酉酉': 1, '亥亥': 1
  };

  // ── 月令旺衰 ──
  var SEASON_WANG = {
    春: { 旺: '木', 相: '火', 休: '水', 囚: '金', 死: '土' },
    夏: { 旺: '火', 相: '土', 休: '木', 囚: '水', 死: '金' },
    秋: { 旺: '金', 相: '水', 休: '土', 囚: '火', 死: '木' },
    冬: { 旺: '水', 相: '木', 休: '金', 囚: '土', 死: '火' },
    季月: { 旺: '土', 相: '金', 休: '火', 囚: '木', 死: '水' }
  };
  var SEASON_LABEL = { 春: '春季', 夏: '夏季', 秋: '秋季', 冬: '冬季', 季月: '四季月' };
  var WANG_SCORE = { 旺: 2, 相: 1, 休: 0, 囚: -1, 死: -2 };

  // ── 节气近似（与 Python 同源精度, 交界±1-2天）──
  var JIE_EDGES = [[1, 5, '丑'], [2, 4, '寅'], [3, 6, '卯'], [4, 4, '辰'], [5, 5, '巳'], [6, 6, '午'],
    [7, 6, '未'], [8, 7, '申'], [9, 7, '酉'], [10, 8, '戌'], [11, 7, '亥'], [12, 7, '子']];

  // ── 爻位地支（引擎原始配法, 与线上一致）──
  var YANG_DZ = ['子', '寅', '辰', '午', '申', '戌'];
  var YIN_DZ = ['未', '巳', '卯', '丑', '亥', '酉'];
  var DZ_TO_WX = { 子: '水', 丑: '土', 寅: '木', 卯: '木', 辰: '土', 巳: '火', 午: '火', 未: '土', 申: '金', 酉: '金', 戌: '土', 亥: '水' };

  // ── 追星趣味分类 → 用神（六爻通行取用；key 与引擎分类常量保持不变）──
  var CATEGORIES = {
    career: { label: 'CP契合', yongshen: '官鬼' },
    wealth: { label: '抢票成行', yongshen: '妻财' },
    study:  { label: '本命缘分', yongshen: '父母' },
    social: { label: '粉圈人际', yongshen: '兄弟' },
    mind:   { label: '追星心情', yongshen: '子孙' }
  };

  var STATE_LABELS = { 旺: '极旺', 相: '次旺', 休: '平淡', 囚: '受困', 死: '极弱' };

  // ── 日期工具（禁字符串解析, 全部 Y,M,D 构造 / UTC 序数）──
  // 公历 y,m,d(1基) → 与 Python date.toordinal() 一致的序数
  function toOrdinal(y, m, d) {
    var days = Math.floor(Date.UTC(y, m - 1, d) / 86400000);
    return days + 719163; // 1970-01-01 = ordinal 719163
  }
  function ordinalToYMD(ord) {
    var ms = (ord - 719163) * 86400000;
    var dt = new Date(ms);
    return [dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate()];
  }
  var ANCHOR_ORD = toOrdinal(1949, 10, 1); // 1949-10-01 = 甲子日

  function dayZhiOf(ord) { return ZHI_ALL[(ord - ANCHOR_ORD) % 12]; }
  function dayGzOf(ord) {
    var i = (ord - ANCHOR_ORD) % 60;
    return GAN[i % 10] + ZHI_ALL[i % 12];
  }

  function seasonOf(y, m, d) {
    if ((m === 2 && d >= 4) || m === 3 || (m === 4 && d < 4)) return '春';
    if ((m === 4 && d >= 4) || (m === 5 && d < 5)) return '季月';
    if ((m === 5 && d >= 5) || m === 6 || (m === 7 && d < 6)) return '夏';
    if ((m === 7 && d >= 6) || (m === 8 && d < 7)) return '季月';
    if ((m === 8 && d >= 7) || m === 9 || (m === 10 && d < 8)) return '秋';
    if ((m === 10 && d >= 8) || (m === 11 && d < 7)) return '季月';
    if ((m === 11 && d >= 7) || m === 12 || (m === 1 && d < 5)) return '冬';
    return '季月';
  }

  function yuezhiOf(y, m, d) {
    var z = '子';
    for (var i = 0; i < JIE_EDGES.length; i++) {
      var em = JIE_EDGES[i][0], ed = JIE_EDGES[i][1], ez = JIE_EDGES[i][2];
      if (m === em && d >= ed) return ez;
      if (m > em) z = ez;
    }
    return z;
  }

  function liuqinOf(otherWx, meWx) {
    if (otherWx === meWx) return '兄弟';
    var sheng = { 木: '火', 火: '土', 土: '金', 金: '水', 水: '木' };
    if (sheng[meWx] === otherWx) return '子孙';
    if (sheng[otherWx] === meWx) return '父母';
    var ke = { 木: '土', 火: '金', 土: '水', 金: '木', 水: '火' };
    if (ke[meWx] === otherWx) return '妻财';
    if (ke[otherWx] === meWx) return '官鬼';
    return '兄弟';
  }

  function wxOfLiuqin(liuqin, meWx) {
    var sheng = { 木: '火', 火: '土', 土: '金', 金: '水', 水: '木' };
    var ke = { 木: '土', 火: '金', 土: '水', 金: '木', 水: '火' };
    var k;
    if (liuqin === '兄弟') return meWx;
    if (liuqin === '子孙') return sheng[meWx] || meWx;
    if (liuqin === '父母') {
      for (k in sheng) { if (sheng.hasOwnProperty(k) && sheng[k] === meWx) return k; }
      return meWx;
    }
    if (liuqin === '妻财') return ke[meWx] || meWx;
    if (liuqin === '官鬼') {
      for (k in ke) { if (ke.hasOwnProperty(k) && ke[k] === meWx) return k; }
      return meWx;
    }
    return meWx;
  }

  function relTo(a, b) {
    if (a === b) return '同';
    var sheng = { 木: '火', 火: '土', 土: '金', 金: '水', 水: '木' };
    if (sheng[a] === b) return '生';
    var ke = { 木: '土', 火: '金', 土: '水', 金: '木', 水: '火' };
    if (ke[a] === b) return '克';
    return '无关';
  }

  function idxFromLines(lines) {
    for (var idx = 1; idx <= 8; idx++) {
      var info = BAGUA[idx];
      if (info.lines[0] === lines[0] && info.lines[1] === lines[1] && info.lines[2] === lines[2]) return idx;
    }
    return 8;
  }

  // 标记截断: 总长>4 字时按优先级重切, 保留前 4 个 token
  var MARK_ORDER = ['空', '破', '冲', '合', '刑', '害', '日克', '月克', '日生', '月生'];
  function truncateMarks(t) {
    if (t.length <= 4) return t;
    var toks = [], rest = t, i = 0;
    while (i < rest.length) {
      var matched = false;
      for (var j = 0; j < MARK_ORDER.length; j++) {
        var tk = MARK_ORDER[j];
        if (rest.startsWith(tk, i)) { toks.push(tk); i += tk.length; matched = true; break; }
      }
      if (!matched) i += 1;
    }
    return toks.slice(0, 4).join('');
  }

  // 日辰信息 + 六爻标记（空/破/冲/合/刑/害/日克/月克/日生/月生）
  function applyDayInfo(cast) {
    try {
      var parts = (cast.event_date || '').split('-');
      var y = parseInt(parts[0], 10), m = parseInt(parts[1], 10), d = parseInt(parts[2], 10);
      if (!y || !m || !d) throw new Error('bad date');
      var ord = toOrdinal(y, m, d);
      var idx = (ord - ANCHOR_ORD) % 60;
      var dayZhi = ZHI_ALL[idx % 12];
      var dayGz = GAN[idx % 10] + dayZhi;
      var shouZhi = (idx - (idx % 10)) % 12;
      var xunkong = ZHI_ALL[(shouZhi - 2) % 12] + ZHI_ALL[(shouZhi - 1) % 12];
      var yuezhi = yuezhiOf(y, m, d);
      var po = CHONG[yuezhi];
      var rc = CHONG[dayZhi];
      var rh = LIUHE[dayZhi];
      var mwx0 = ZHI_WX[yuezhi];
      var dwx0 = ZHI_WX[dayZhi];
      var marks = [];
      var dzList = cast.lines_dz || [];
      for (var i = 0; i < dzList.length; i++) {
        var dz = dzList[i], t = '';
        if (dz) {
          if (xunkong.indexOf(dz) >= 0) t += '空';
          if (dz === po) t += '破';
          if (dz === rc) t += '冲';
          if (dz === rh) t += '合';
          if (XING_PAIRS[dz + dayZhi]) t += '刑';
          if (HAI[dayZhi] === dz) t += '害';
          var ywx = ZHI_WX[dz];
          if (WX_KE[dwx0] === ywx) t += '日克';
          if (WX_KE[mwx0] === ywx) t += '月克';
          if (WX_SHENG[dwx0] === ywx) t += '日生';
          if (WX_SHENG[mwx0] === ywx) t += '月生';
        }
        marks.push(truncateMarks(t));
      }
      while (marks.length < 6) marks.push('');
      cast.day_gz = dayGz;
      cast.day_zhi = dayZhi;
      cast.xunkong = xunkong;
      cast.yuezhi = yuezhi;
      cast.lines_marks = marks;
    } catch (e) {
      cast.day_gz = '';
      cast.day_zhi = '';
      cast.xunkong = '';
      cast.yuezhi = '';
      cast.lines_marks = ['', '', '', '', '', ''];
    }
    return cast;
  }

  // ── 应期日历（线上 _yingqi_dates_str 1:1 规则; 用神爻地支 → 公历日期）──
  function yingqiDates(cast) {
    var out = [];
    try {
      if (!cast.day_gz) return out;
      var parts = (cast.event_date || '').split('-');
      var y0 = parseInt(parts[0], 10), m0 = parseInt(parts[1], 10), d0 = parseInt(parts[2], 10);
      if (!y0 || !m0 || !d0) return out;
      var ord0 = toOrdinal(y0, m0, d0);
      var pos = cast.yongshen_positions || [];
      var ldz = cast.lines_dz || [];
      var yz = (pos.length && pos[0] - 1 >= 0 && pos[0] - 1 < ldz.length) ? ldz[pos[0] - 1] : '';
      if (yz) {
        var hDates = [], vDates = [], cDates = [];
        for (var k = 1; k <= 45; k++) {
          var z = dayZhiOf(ord0 + k);
          var ymd = ordinalToYMD(ord0 + k);
          var lbl = ymd[1] + '月' + ymd[2] + '日';
          if (z === LIUHE[yz] && hDates.length < 2) hDates.push(lbl);
          if (z === yz && vDates.length < 2) vDates.push(lbl);
          if (z === CHONG[yz] && cDates.length < 1) cDates.push(lbl);
        }
        if (hDates.length) out.push({ kind: '合日', yz: yz, dates: hDates, note: '与用神' + yz + '相合，宜推进沟通' });
        if (vDates.length) out.push({ kind: '当值', yz: yz, dates: vDates, note: '用神' + yz + '当值，事气最显' });
        if (cDates.length) out.push({ kind: '冲日', yz: yz, dates: cDates, note: '冲' + yz + '之日，多为变动窗口' });
      }
      var xk = cast.xunkong || '';
      if (xk.length === 2) {
        var oDates = [];
        for (var k2 = 1; k2 <= 20; k2++) {
          var z2 = dayZhiOf(ord0 + k2);
          if (xk.indexOf(z2) >= 0 && oDates.length < 2) {
            var ymd2 = ordinalToYMD(ord0 + k2);
            oDates.push(ymd2[1] + '月' + ymd2[2] + '日');
          }
        }
        if (oDates.length) out.push({ kind: '出空', yz: xk, dates: oDates, note: '旬空' + xk + '出空，悬而未决者落定' });
      }
      var yz2 = cast.yuezhi || '';
      if (yz2) {
        for (var j = 0; j < JIE_EDGES.length; j++) {
          var em = JIE_EDGES[j][0], ed = JIE_EDGES[j][1], ez = JIE_EDGES[j][2];
          var ny = y0, nm = em, nd = ed;
          var candOrd = toOrdinal(ny, nm, nd);
          if (candOrd <= ord0) { ny = y0 + 1; candOrd = toOrdinal(ny, nm, nd); }
          var diff = candOrd - ord0;
          if (diff > 0 && diff <= 40) {
            out.push({ kind: '换月', yz: ez, dates: [nm + '月' + nd + '日'], note: nm + '月' + nd + '日换月，之后进入' + ez + '月' });
            break;
          }
        }
      }
    } catch (e) { /* 保持静默, 与线上一致 */ }
    return out;
  }

  // ── 排盘核心（手动六爻 + 动爻; 三数起卦经 toLines/c 的换算在外层）──
  function castFromLines(lines, moving, ymd, catKey) {
    var cat = CATEGORIES[catKey] || CATEGORIES.mind;
    var y = ymd[0], m = ymd[1], d = ymd[2];
    var upperIdx = idxFromLines(lines.slice(3));
    var lowerIdx = idxFromLines(lines.slice(0, 3));
    var upper = BAGUA[upperIdx];
    var lower = BAGUA[lowerIdx];
    var key = upperIdx + ',' + lowerIdx;
    var name = HEXAGRAM_NAMES[key] || '未知卦';
    var palaceWx = PALACE_WX[key] || '土';

    var linesDz = [], linesWx = [];
    for (var i = 0; i < 6; i++) {
      var dz = lines[i] === 1 ? YANG_DZ[i] : YIN_DZ[i];
      linesDz.push(dz);
      linesWx.push(DZ_TO_WX[dz]);
    }
    var liuqin = [];
    for (var j = 0; j < 6; j++) liuqin.push(liuqinOf(linesWx[j], palaceWx));

    var changedLines = lines.slice();
    changedLines[moving - 1] = changedLines[moving - 1] === 1 ? 0 : 1;
    var newUpperIdx = idxFromLines(changedLines.slice(3));
    var newLowerIdx = idxFromLines(changedLines.slice(0, 3));
    var changedName = HEXAGRAM_NAMES[newUpperIdx + ',' + newLowerIdx] || '未知卦';

    var season = seasonOf(y, m, d);
    var seasonMap = SEASON_WANG[season];

    var yongshen = cat.yongshen;
    var yongshenPositions = [];
    for (var p = 0; p < 6; p++) { if (liuqin[p] === yongshen) yongshenPositions.push(p + 1); }
    var yongshenWx = wxOfLiuqin(yongshen, palaceWx);
    var yongshenState = '休';
    for (var sName in seasonMap) { if (seasonMap.hasOwnProperty(sName) && seasonMap[sName] === yongshenWx) { yongshenState = sName; break; } }

    var movingLq = liuqin[moving - 1];
    var movingWx = linesWx[moving - 1];
    var movingDz = linesDz[moving - 1];
    // 线上怪癖对齐: cast_hexagram 基础阶段 moving_relation 一律按默认用神「妻财」算,
    // divine_for_event 覆盖用神后不重算此字段（score 亦沿用旧 relation 值）
    var baseYongshenWx = wxOfLiuqin('妻财', palaceWx);
    var movingRelation = relTo(movingWx, baseYongshenWx);
    var relationScore = movingRelation === '生' ? 1 : (movingRelation === '克' ? -1 : 0);
    var isYongshenMoving = movingLq === yongshen;
    var selfScore = isYongshenMoving ? 1 : 0;
    var total = (WANG_SCORE[yongshenState] || 0) + relationScore + selfScore;
    var star = total >= 3 ? 5 : (total >= 1 ? 4 : (total >= 0 ? 3 : (total >= -2 ? 2 : 1)));

    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var cast = {
      event_date: y + '-' + pad(m) + '-' + pad(d),
      season: season,
      season_label: SEASON_LABEL[season] || '',
      category: catKey,
      category_label: cat.label,
      upper_gua: upper.name + upper.nature,
      lower_gua: lower.name + lower.nature,
      upper_symbol: upper.symbol,
      lower_symbol: lower.symbol,
      palace_wx: palaceWx,
      ben_gua: name,
      ben_text: HEXAGRAM_TEXT[name] || '',
      bian_gua: changedName,
      bian_text: HEXAGRAM_TEXT[changedName] || '',
      lines: lines,
      changed_lines: changedLines,
      lines_dz: linesDz,
      lines_wx: linesWx,
      moving: moving,
      moving_dz: movingDz,
      moving_liuqin: movingLq,
      moving_wx: movingWx,
      moving_relation: movingRelation,
      liuqin: liuqin,
      yongshen: yongshen,
      yongshen_wx: yongshenWx,
      yongshen_state: yongshenState,
      yongshen_positions: yongshenPositions,
      is_yongshen_moving: isYongshenMoving,
      score: total,
      star: star
    };
    applyDayInfo(cast);
    cast.yongshen = yongshen;           // 与 divine_for_event 一致: 日辰后再按分类重定用神相关量
    cast.yongshen_wx = wxOfLiuqin(yongshen, cast.palace_wx);
    var sm2 = SEASON_WANG[cast.season];
    var ys2 = '休';
    for (var s2 in sm2) { if (sm2.hasOwnProperty(s2) && sm2[s2] === cast.yongshen_wx) { ys2 = s2; break; } }
    cast.yongshen_state = ys2;
    var yp2 = [];
    for (var p2 = 0; p2 < 6; p2++) { if (cast.liuqin[p2] === yongshen) yp2.push(p2 + 1); }
    cast.yongshen_positions = yp2;
    cast.is_yongshen_moving = cast.moving_liuqin === yongshen;
    var sc2 = (WANG_SCORE[ys2] || 0) + (cast.moving_relation === '生' ? 1 : (cast.moving_relation === '克' ? -1 : 0)) + (cast.is_yongshen_moving ? 1 : 0);
    cast.score = sc2;
    cast.star = sc2 >= 3 ? 5 : (sc2 >= 1 ? 4 : (sc2 >= 0 ? 3 : (sc2 >= -2 ? 2 : 1)));
    return cast;
  }

  // 三数起卦: a→上卦, b→下卦, c→动爻
  function castFromNumbers(a, b, c, ymd, catKey) {
    var upperIdx = a % 8 || 8;
    var lowerIdx = b % 8 || 8;
    var moving = (c % 6) + 1;
    var lines = BAGUA[lowerIdx].lines.concat(BAGUA[upperIdx].lines);
    return castFromLines(lines, moving, ymd, catKey);
  }

  // ── 导出 ──
  var LiuYao = {
    BAGUA: BAGUA,
    HEXAGRAM_NAMES: HEXAGRAM_NAMES,
    HEXAGRAM_TEXT: HEXAGRAM_TEXT,
    CATEGORIES: CATEGORIES,
    STATE_LABELS: STATE_LABELS,
    CHONG: CHONG,
    LIUHE: LIUHE,
    castFromNumbers: castFromNumbers,
    castFromLines: castFromLines,
    yingqiDates: yingqiDates,
    dayGzOf: dayGzOf
  };

  if (typeof window !== 'undefined') {
    window.LiuYao = LiuYao;
  } else if (typeof global !== 'undefined') {
    global.LiuYao = LiuYao; // node 一致性测试用
  }
})();
