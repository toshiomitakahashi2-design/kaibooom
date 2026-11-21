/* KAIBOOOM 管理画面（サイトと同じ見た目・構造）
   site/template.html をそのまま使い、その上に「管理」のしくみだけを足す。
   - 一覧：サイトと同じグリッド。上に「承認待ち／公開中／非公開／見送り／すべて」のタブ
   - 記事：サイトと同じ記事ページ。上に状態と「承認して公開」などのボタン、修正案の見比べ
   - 編集：サイトと同じ「その場で編集」（鉛筆ボタン）
   - Gensparkの記事の取り込み欄
   build.py が template.html にこのファイルを差し込んで docs/admin.html をつくる。 */
(function(){
  const STAGE = {
    draft:     { label: '承認待ち', cls: 'st-draft' },
    published: { label: '公開中',   cls: 'st-pub' },
    hidden:    { label: '非公開',   cls: 'st-hidden' },
    rejected:  { label: '見送り',   cls: 'st-rej' }
  };
  const stage = p => STAGE[p.status] ? p.status : 'published';
  const waiting = p => stage(p) === 'draft' || !!p.proposal;
  const TABS = [
    ['wait', '承認待ち', waiting],
    ['published', '公開中', p => stage(p) === 'published'],
    ['hidden', '非公開', p => stage(p) === 'hidden'],
    ['rejected', '見送り', p => stage(p) === 'rejected'],
    ['all', 'すべて', () => true]
  ];
  const TEXT = ['title','oneliner','about','points'];
  const PROP_LABEL = { title: '見出し', oneliner: 'ひとことで言うと', about: 'なんの広告？', points: 'アイデア、ポイント' };
  const today = () => new Date().toISOString().slice(0,10);
  const $ = id => document.getElementById(id);
  let tab = null, adopt = null, backup = null, flash = '';

  const CSS = `
  .adm-pill{margin-left:8px;padding:2px 9px;border-radius:99px;background:var(--ink);color:var(--paper);font-size:11px;font-weight:700;letter-spacing:.04em;flex-shrink:0}
  .atabs{display:flex;gap:4px;flex-wrap:wrap;margin:0 0 14px}
  .atab{height:34px;padding:0 14px;border-radius:99px;font-size:13px;font-weight:700;color:var(--sub);border:1px solid var(--line)}
  .atab.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
  .atab b{font-family:'Archivo',sans-serif;font-weight:700;margin-left:5px;opacity:.75}
  .st{display:inline-block;margin-right:6px;padding:1px 7px;border-radius:99px;font-size:10.5px;font-weight:700;border:1px solid currentColor}
  .st-draft{color:#B26A00}.st-hidden{color:var(--sub)}.st-rej{color:var(--sub);text-decoration:line-through}.st-prop{color:var(--cut)}
  .apanel{margin:0 0 16px;padding:14px 16px;border-radius:14px;background:var(--soft);font-size:13px}
  .apanel .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .apanel .lab{font-weight:700;margin-right:4px}
  .apanel h2{font-size:14px;margin:0 0 8px}
  .eb-btn.ok{background:#1E7A46;color:#fff;border-color:#1E7A46}
  .eb-btn.ng{color:#C4321F;border-color:#C4321F}
  .prop{margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
  .prop h2{color:var(--cut)}
  .cmp{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:8px 0 10px}
  @media (max-width:640px){.cmp{grid-template-columns:minmax(0,1fr)}}
  .cmp div{white-space:pre-wrap;background:var(--paper);border-radius:10px;padding:10px 12px;line-height:1.8;font-size:12.5px;color:var(--body)}
  .cmp b{display:block;font-size:11px;color:var(--sub);margin-bottom:4px}
  .cmp .new b{color:var(--cut)}
  .amedia{margin-top:12px}
  .amedia summary{cursor:pointer;font-weight:700}
  .amedia label{display:block;font-size:12px;font-weight:700;margin:10px 0 4px}
  .amedia input,.amedia textarea,.imp textarea,.alock input{width:100%;font:inherit;font-size:13px;padding:8px 10px;border-radius:10px;border:1px solid var(--line);background:var(--paper);color:var(--ink)}
  .amedia textarea{min-height:64px}
  .imp{margin:0 0 16px;padding:12px 16px;border-radius:14px;border:1px dashed var(--line);font-size:13px}
  .imp summary{cursor:pointer;font-weight:700}
  .imp textarea{min-height:110px;font-family:ui-monospace,monospace;font-size:12px;margin:8px 0}
  .imp .eb-msg{white-space:pre-wrap}
  .alock{max-width:420px;margin:10vh auto;text-align:center}
  .alock h1{font-family:'Zen Old Mincho',serif;font-size:22px;margin:0 0 8px}
  .alock p{font-size:13px;color:var(--sub);line-height:1.8}
  .alock ol{text-align:left;font-size:13px;line-height:1.9;color:var(--sub);padding-left:20px}
  .alock .pinin{width:160px;font-size:24px;letter-spacing:.35em;text-align:center}
  .afoot{margin:40px 0 0;text-align:center}
  .afoot button{font-size:12px;color:var(--sub);text-decoration:underline}
  `;

  async function fetchAll(){
    const r = await fetch(API + '?t=' + Date.now(), { headers: gh(), cache: 'no-store' });
    if (r.status === 401 || r.status === 403) throw new Error('GitHubの鍵が使えませんでした。期限切れか、権限（Contents: Read and write）が足りないかもしれません。');
    if (!r.ok) throw new Error('読み込みに失敗しました（' + r.status + '）');
    const j = await r.json();
    return { sha: j.sha, all: JSON.parse(fromB64(j.content)) };
  }
  async function putAll(all, sha, message){
    const r = await fetch(API, { method: 'PUT', headers: { ...gh(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, content: toB64(JSON.stringify(all, null, 2) + '\n'), sha }) });
    if (r.status === 409) throw new Error('ちょうど自動更新と重なりました。もう一度押してください。');
    if (!r.ok) throw new Error('保存に失敗しました（' + r.status + '）');
  }
  // 最新を読み直してから1本だけ書き換える（自動更新で増えた記事を消さないため）
  async function change(slug, fn, message){
    const { sha, all } = await fetchAll();
    const t = all.find(x => x.slug === slug);
    if (!t) throw new Error('この記事が見つかりませんでした。');
    fn(t);
    await putAll(all, sha, message);
    const p = POSTS.find(x => x.slug === slug);
    Object.keys(p).forEach(k => { if (!(k in t)) delete p[k]; });
    Object.assign(p, t);
  }

  const A = window.KB_ADMIN = {
    filter(p){ return (TABS.find(t => t[0] === (tab || 'wait')) || TABS[0])[2](p); },
    badge(p){
      if (p.proposal && stage(p) !== 'draft') return '<span class="st st-prop">修正案あり</span>';
      const s = stage(p); return s === 'published' ? '' : `<span class="st ${STAGE[s].cls}">${STAGE[s].label}</span>`;
    },
    lead(list){
      const cur = tab || 'wait';
      const tabs = TABS.map(([k, label, f]) => `<button class="atab${k === cur ? ' on' : ''}" data-atab="${k}" aria-pressed="${k === cur}">${label}<b>${POSTS.filter(f).length}</b></button>`).join('');
      const title = (TABS.find(t => t[0] === cur) || TABS[0])[1] + (cat !== 'すべて' ? '・' + esc(cat) : '');
      const imp = `<details class="imp"><summary>Gensparkの記事を取り込む</summary>
        <p style="color:var(--sub);line-height:1.8;margin:8px 0 0">Gensparkのコードブロックの「Copy」でコピーしたJSONを貼り付けます。新しい記事は「承認待ち」に、既存の記事（slugが同じもの）は「修正案」として入ります。公開はされません。</p>
        <textarea id="imp-text" placeholder='[{"title": "...", "points": "..."}]'></textarea>
        <button class="eb-btn primary" id="imp-go">取り込む</button><div class="eb-msg" id="imp-msg" role="status"></div></details>`;
      return `<div class="atabs" role="tablist">${tabs}</div>${cur === 'wait' ? imp : ''}<div class="lead"><h1>${title}</h1><small>${list.length} 本</small></div>`;
    },
    post(p){
      // 修正案を入れて編集を始めたあと「やめる」を押したら、元の文に戻す
      if (!editing && adopt === p.slug && backup) { Object.assign(p, backup); adopt = null; backup = null; post(p.slug); return; }
      if (editing) return;
      const s = stage(p);
      const btn = (id, label, cls) => `<button class="eb-btn ${cls || ''}" id="${id}">${label}</button>`;
      const acts = {
        draft: btn('a-pub', '承認して公開する', 'ok') + btn('a-rej', '見送る', 'ng'),
        published: btn('a-hide', '非公開にする'),
        hidden: btn('a-pub', '公開する', 'ok') + btn('a-draft', '承認待ちに戻す'),
        rejected: btn('a-draft', '承認待ちに戻す') + btn('a-pub', '公開する', 'ok')
      }[s];
      const pr = p.proposal;
      const prop = pr ? `<div class="prop"><h2>修正案がとどいています</h2>
        <div style="color:var(--sub)">${esc([pr.date, pr.by && pr.by + ' より', pr.note].filter(Boolean).join('　'))}</div>
        <div class="cmp">${TEXT.filter(k => pr[k] && pr[k] !== p[k]).map(k => `<div><b>いま：${PROP_LABEL[k]}</b>${esc(p[k] || '')}</div><div class="new"><b>修正案：${PROP_LABEL[k]}</b>${esc(pr[k])}</div>`).join('') || '<div>いまの文章と同じです。</div>'}</div>
        <div class="row">${btn('a-adopt', '修正案を入れて編集する', 'primary')}${btn('a-drop', '修正案を捨てる', 'ng')}</div>
        <div style="color:var(--sub);margin-top:6px">「入れて編集する」を押すと、修正案の文で編集画面が開きます。手直しして「保存する」で反映されます。</div></div>` : '';
      const media = `<details class="amedia"><summary>写真・動画・国を直す</summary>
        <label for="am-image">メイン画像のURL（空にすると画像なし）</label><input id="am-image" value="${esc(p.image || '')}">
        <label for="am-videos">動画のURL（YouTube・Vimeo。1行に1本）</label><textarea id="am-videos">${esc((p.videos || []).map(v => v.type === 'vimeo' ? 'https://vimeo.com/' + v.id : 'https://www.youtube.com/watch?v=' + v.id).join('\n'))}</textarea>
        <label for="am-gallery">追加の写真のURL（1行に1枚）</label><textarea id="am-gallery">${esc((p.gallery || []).join('\n'))}</textarea>
        <label for="am-country">国・地域</label><input id="am-country" value="${esc(p.country || '')}">
        <div class="row" style="margin-top:10px">${btn('am-save', '写真・動画を保存', 'primary')}</div></details>`;
      const panel = `<div class="apanel" id="apanel"><div class="row"><span class="lab">状態</span><span class="st ${STAGE[s].cls}" style="margin-right:auto">${STAGE[s].label}</span>${acts}</div>
        <div class="eb-msg" id="a-msg" role="status">${esc(flash)}</div>${prop}${media}</div>`;
      flash = '';
      document.querySelector('.bar').insertAdjacentHTML('afterend', panel);
      const msg = (t, ng) => { const m = $('a-msg'); m.textContent = t; m.className = 'eb-msg' + (ng ? ' ng' : ''); };
      const run = async (fn, message, done) => {
        document.querySelectorAll('#apanel button').forEach(b => b.disabled = true); msg('保存中…');
        try { await change(p.slug, fn, message); flash = done; post(p.slug); }
        catch(e) { msg(e.message, true); document.querySelectorAll('#apanel button').forEach(b => b.disabled = false); }
      };
      const on = (id, f) => { const el = $(id); if (el) el.onclick = f; };
      on('a-pub', () => run(t => { t.status = 'published'; if (!t.approved) t.approved = today(); }, `admin: No.${p.no} を公開`, '公開しました。1〜2分でサイトに反映されます。'));
      on('a-rej', () => run(t => { t.status = 'rejected'; }, `admin: No.${p.no} を見送り`, '見送りにしました。'));
      on('a-hide', () => run(t => { t.status = 'hidden'; }, `admin: No.${p.no} を非公開`, '非公開にしました。'));
      on('a-draft', () => run(t => { t.status = 'draft'; }, `admin: No.${p.no} を承認待ちに戻す`, '承認待ちに戻しました。'));
      on('a-drop', () => run(t => { delete t.proposal; }, `admin: No.${p.no} の修正案を捨てる`, '修正案を捨てました。本文はそのままです。'));
      on('a-adopt', () => {
        backup = Object.fromEntries(TEXT.map(k => [k, p[k]])); adopt = p.slug;
        TEXT.forEach(k => { if (pr[k]) p[k] = pr[k]; });
        if (ss('kaibooom-unlocked') === '1') { editing = true; post(p.slug); window.scrollTo(0, 0); } else startEdit(p.slug);
      });
      on('am-save', () => {
        const lines = id => $(id).value.split('\n').map(x => x.trim()).filter(Boolean);
        const vids = lines('am-videos').map(u => {
          let m = u.match(/(?:youtube(?:-nocookie)?\.com\/(?:embed\/|watch\?(?:.*&)?v=|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
          if (m) return { type: 'youtube', id: m[1] };
          m = u.match(/vimeo\.com\/(?:video\/)?(\d{6,12})/); return m ? { type: 'vimeo', id: m[1] } : null;
        });
        if (vids.includes(null)) { msg('動画のURLが読み取れませんでした。YouTubeかVimeoのURLを1行に1本ずつ入れてください。', true); return; }
        const img = $('am-image').value.trim(), gal = lines('am-gallery'), country = $('am-country').value.trim();
        run(t => {
          if (img) t.image = img; else delete t.image;
          if (vids.length) t.videos = vids; else delete t.videos;
          if (gal.length) t.gallery = gal; else delete t.gallery;
          t.country = country; t.media_checked = true;
        }, `admin: No.${p.no} の写真・動画を編集`, '写真・動画を保存しました。');
      });
    },
    statusOnSave(t){ return STAGE[t.status] ? t.status : 'published'; },
    beforeSave(t, p){
      if (adopt !== t.slug || !t.proposal) return;
      // 修正案を採用：その文を「AIの元の文」として残す（ここからの手直しが学習に使われる）
      t.ai_base = Object.fromEntries(TEXT.map(k => [k, t.proposal[k] || backup[k] || '']));
      delete t.proposal; delete p.proposal; adopt = null; backup = null;
    }
  };

  /* ---- Gensparkの記事を取り込む（scripts/import_inbox.py と同じ決まり） ---- */
  const normUrl = u => String(u || '').trim().replace(/[?#].*$/, '').replace(/\/+$/, '').toLowerCase();
  const slugFrom = u => 'g-' + (normUrl(u).split('//').pop().replace(/[^0-9a-z]+/g, '-').slice(-40).replace(/^-+|-+$/g, '') || 'post');
  function parseImport(text){
    let t = text.trim().replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '');
    const a = t.indexOf('['), o = t.indexOf('{');
    if (a >= 0 && (o < 0 || a < o)) t = t.slice(a, t.lastIndexOf(']') + 1);
    let j = JSON.parse(t);
    return Array.isArray(j) ? j : (j.articles || j.posts || [j]);
  }
  async function importPosts(){
    const btn = $('imp-go'), m = $('imp-msg'); btn.disabled = true; m.className = 'eb-msg'; m.textContent = '取り込み中…';
    try {
      const items = parseImport($('imp-text').value);
      const { sha, all } = await fetchAll();
      const bySlug = new Map(all.map(p => [p.slug, p]));
      const byUrl = new Map(all.filter(p => p.source_url).map(p => [normUrl(p.source_url), p]));
      const byWork = new Map(all.map(p => [(p.client + '|' + p.work).toLowerCase(), p]));
      let no = Math.max(0, ...all.map(p => p.no)) + 1, added = 0, proposed = 0; const log = [];
      for (const raw of items) {
        const it = Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, typeof v === 'string' ? v.trim() : v]));
        if (it.points) it.points = it.points.replace(/\n{3,}/g, '\n\n');
        const target = it.slug && bySlug.get(it.slug);
        if (target) {
          const prop = Object.fromEntries(TEXT.filter(k => it[k] && it[k] !== target[k]).map(k => [k, it[k]]));
          if (!Object.keys(prop).length) { log.push(`No.${target.no}：変更なし`); continue; }
          target.proposal = { ...prop, by: it.by || 'Genspark', date: today(), ...(it.note ? { note: it.note } : {}) };
          proposed++; log.push(`No.${target.no}：修正案を置きました`); continue;
        }
        const miss = ['title','oneliner','about','points','work','client','source_url'].filter(k => !it[k]);
        if (miss.length) { log.push(`スキップ（${miss.join('・')}がない）：${it.title || '?'}`); continue; }
        const dup = byUrl.get(normUrl(it.source_url)) || byWork.get((it.client + '|' + it.work).toLowerCase());
        if (dup) { log.push(`スキップ（No.${dup.no}と同じ作品）：${it.title}`); continue; }
        let slug = slugFrom(it.source_url), base = slug, n = 2;
        while (bySlug.has(slug)) slug = `${base}-${n++}`;
        const p = { slug, no: no++, date: today(), category: CATS.includes(it.category) ? it.category : '広告' };
        TEXT.forEach(k => p[k] = it[k]);
        ['work','client','agency','production','award','country','source_name','source_url','image','date_released'].forEach(k => { if (it[k]) p[k] = it[k]; });
        p.source_name = p.source_name || it.source_url.split('/')[2];
        ['agency','production','award'].forEach(k => { if (!p[k]) p[k] = '—'; });
        const vids = (Array.isArray(it.videos) ? it.videos : []).filter(v => v && v.id && (v.type === 'youtube' || v.type === 'vimeo'));
        if (vids.length) p.videos = vids;
        p.status = 'draft'; p.engine = it.by || 'Genspark';
        p.ai_base = Object.fromEntries(TEXT.map(k => [k, p[k]]));
        all.push(p); bySlug.set(slug, p); byUrl.set(normUrl(p.source_url), p); byWork.set((p.client + '|' + p.work).toLowerCase(), p);
        added++; log.push(`No.${p.no}：承認待ちに追加　${p.title}`);
      }
      if (added || proposed) await putAll(all, sha, `admin: Gensparkから取り込み（新規${added}・修正案${proposed}）`);
      POSTS.splice(0, POSTS.length, ...all.sort((a, b) => b.no - a.no));
      tab = 'wait'; route();
      const m2 = $('imp-msg'); m2.className = 'eb-msg'; m2.textContent = `新しい下書き ${added} 本／修正案 ${proposed} 本\n` + log.join('\n');
      $('imp').open = true;
    } catch(e) { m.className = 'eb-msg ng'; m.textContent = '読み取れませんでした：' + e.message; btn.disabled = false; }
  }

  /* ---- 合鍵と端末の登録 ---- */
  function hideNav(hide){ ['cats-d','cats-m'].forEach(id => { const el = $(id); if (el) el.style.visibility = hide ? 'hidden' : ''; }); }
  function lock(){
    hideNav(true);
    app.innerHTML = `<div class="alock"><h1>管理ページ</h1><p>合鍵を入れてください</p>
      <input id="al-pin" class="pinin" type="password" inputmode="numeric" autocomplete="off" maxlength="8" aria-label="合鍵">
      <div style="margin-top:14px"><button class="eb-btn primary" id="al-go">ひらく</button></div><div class="eb-msg ng" id="al-msg" role="alert"></div></div>`;
    const input = $('al-pin'); input.focus();
    const go = async () => {
      if (await sha256(input.value) !== PIN_HASH) { $('al-msg').textContent = '合鍵がちがいます'; input.select(); return; }
      ss('kaibooom-unlocked', '1'); start();
    };
    $('al-go').onclick = go; input.onkeydown = e => { if (e.key === 'Enter') go(); };
  }
  function tokenForm(err){
    hideNav(true);
    app.innerHTML = `<div class="alock"><h1>この端末を登録する</h1><p>記事を書き換えるための「GitHubの鍵」を、この端末にだけ保存します（最初の1回だけ）。</p>
      <ol><li>GitHub 右上のアイコン →「Settings」</li><li>左メニュー下の「Developer settings」→「Personal access tokens」→「Fine-grained tokens」</li>
      <li>「Generate new token」。Repository access は「Only select repositories」→ kaibooom</li>
      <li>Permissions の「Contents」を「Read and write」にして「Generate token」</li><li>github_pat_ で始まる文字をコピーして、下に貼る</li></ol>
      <input id="al-token" type="password" autocomplete="off" placeholder="github_pat_xxxxxxxx" aria-label="GitHubの鍵">
      <div style="margin-top:14px"><button class="eb-btn primary" id="al-save">登録する</button></div><div class="eb-msg ng" id="al-msg" role="alert">${esc(err || '')}</div></div>`;
    $('al-save').onclick = () => {
      const t = $('al-token').value.trim(); if (!t) { $('al-msg').textContent = '鍵を貼り付けてください'; return; }
      try { localStorage.setItem('kaibooom-token', t); } catch(e) {}
      start();
    };
  }
  async function start(){
    if (ss('kaibooom-unlocked') !== '1') { lock(); return; }
    if (!canEdit()) { tokenForm(); return; }
    app.innerHTML = '<div class="empty">読み込み中…</div>';
    try {
      const { all } = await fetchAll();
      POSTS.splice(0, POSTS.length, ...all.sort((a, b) => b.no - a.no));
    } catch(e) {
      if (/鍵/.test(e.message)) { try { localStorage.removeItem('kaibooom-token'); } catch(_) {} tokenForm(e.message); }
      else app.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
      return;
    }
    hideNav(false);
    if (!tab) tab = POSTS.some(waiting) ? 'wait' : 'published';
    route(); loadOrig();
  }

  document.addEventListener('click', e => {
    const t = e.target.closest('[data-atab]');
    if (t) { tab = t.dataset.atab; lastScroll = 0; go(''); return; }
    if (e.target.closest('#imp-go')) importPosts();
    if (e.target.closest('#a-forget')) { try { localStorage.removeItem('kaibooom-token'); sessionStorage.removeItem('kaibooom-unlocked'); } catch(_) {} location.reload(); }
  });
  window.addEventListener('DOMContentLoaded', () => {
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    // ヘッダー：ロゴの横に「管理」、右上の「…」はサイトへのリンクにする
    const logo = $('home-link'); if (logo) logo.insertAdjacentHTML('afterend', '<span class="adm-pill">管理</span>');
    const tl = document.querySelector('.tagline'); if (tl) tl.remove();
    const site = document.querySelector('.tools a[href="./admin.html"]');
    if (site) { site.href = './'; site.setAttribute('aria-label', 'サイトを見る'); site.title = 'サイトを見る'; }
    const sv = $('nav-saved'); if (sv) sv.style.display = 'none';
    document.body.insertAdjacentHTML('beforeend', '<div class="afoot"><button id="a-forget">この端末の登録を解除する</button>　<a href="./admin-classic.html" style="font-size:12px;color:var(--sub)">旧管理画面</a></div>');
    start();
  });
})();
