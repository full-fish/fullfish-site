// 프로젝트 상세 페이지: 헤더 메뉴, 목차 위치 표시, 이미지 크게 보기
(() => {
  document.documentElement.classList.add('js');

  // 헤더 (메인 src/main.js와 같은 동작)
  const header = document.querySelector('.header');
  const nav = document.getElementById('nav');
  const navToggle = document.getElementById('navToggle');
  navToggle.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a')) {
      nav.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    }
  });
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  // 목차: 지금 읽는 위치 표시
  const toc = document.getElementById('toc');
  const tocToggle = document.getElementById('tocToggle');
  const tocCurrent = document.getElementById('tocCurrent');
  const links = [...toc.querySelectorAll('a[data-toc]')];
  const heads = links.map((a) => document.getElementById(a.dataset.toc)).filter(Boolean);
  const mobile = window.matchMedia('(max-width: 1080px)');
  let activeId = null;

  const keepVisible = (link) => {
    if (mobile.matches) return;
    const r = link.getBoundingClientRect();
    const t = toc.getBoundingClientRect();
    if (r.top < t.top + 32 || r.bottom > t.bottom - 32) {
      toc.scrollTop += r.top - t.top - t.height / 2;
    }
  };

  const update = () => {
    header.classList.toggle('scrolled', window.scrollY > 8);
    const line = mobile.matches ? 150 : 110;
    let cur = heads[0];
    for (const h of heads) {
      if (h.getBoundingClientRect().top - line <= 0) cur = h;
      else break;
    }
    const doc = document.documentElement;
    if (window.innerHeight + window.scrollY >= doc.scrollHeight - 4) cur = heads[heads.length - 1];
    if (!cur || cur.id === activeId) return;
    activeId = cur.id;
    let activeLink = null;
    for (const a of links) {
      const on = a.dataset.toc === activeId;
      a.classList.toggle('is-active', on);
      if (on) { a.setAttribute('aria-current', 'location'); activeLink = a; }
      else a.removeAttribute('aria-current');
    }
    toc.querySelectorAll('.toc-chapter').forEach((li) => li.classList.toggle('is-open', li.contains(activeLink)));
    const chapter = activeLink.closest('.toc-chapter').querySelector(':scope > a');
    tocCurrent.textContent = activeLink === chapter ? chapter.textContent : `${chapter.textContent} · ${activeLink.textContent}`;
    keepVisible(activeLink);
  };

  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { update(); ticking = false; });
  }, { passive: true });
  window.addEventListener('resize', update);
  update();

  // 모바일 목차 펼치기
  const setToc = (open) => {
    toc.classList.toggle('is-open', open);
    tocToggle.setAttribute('aria-expanded', String(open));
    const active = toc.querySelector('a.is-active');
    // 목차 안에서만 스크롤 (페이지는 그대로)
    if (open && active) toc.scrollTop = active.offsetTop - toc.clientHeight / 2;
  };
  tocToggle.addEventListener('click', () => setToc(!toc.classList.contains('is-open')));
  toc.addEventListener('click', (e) => { if (e.target.closest('a') && mobile.matches) setToc(false); });
  document.addEventListener('click', (e) => {
    if (toc.classList.contains('is-open') && !toc.contains(e.target) && !tocToggle.contains(e.target)) setToc(false);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && toc.classList.contains('is-open')) setToc(false); });

  // 이미지 크게 보기 (이미지 모아 보기의 순서대로 넘김)
  const items = [...document.querySelectorAll('.g-item')].map((b) => ({
    key: b.dataset.lb, src: b.dataset.full, w: Number(b.dataset.w), h: Number(b.dataset.h), caption: b.dataset.caption,
  }));
  const dlg = document.getElementById('lightbox');
  const img = document.getElementById('lbImg');
  const cap = document.getElementById('lbCaption');
  const count = document.getElementById('lbCount');
  let index = 0;

  const preload = (i) => { const it = items[(i + items.length) % items.length]; const p = new Image(); p.src = it.src; };
  const show = (i) => {
    index = (i + items.length) % items.length;
    const it = items[index];
    img.src = it.src;
    img.width = it.w;
    img.height = it.h;
    img.alt = it.caption;
    cap.textContent = it.caption;
    count.textContent = `${index + 1} / ${items.length}`;
    preload(index + 1);
    preload(index - 1);
  };
  const open = (key) => {
    const i = items.findIndex((it) => it.key === key);
    show(i < 0 ? 0 : i);
    if (typeof dlg.showModal === 'function') dlg.showModal();
    else dlg.setAttribute('open', '');
    document.body.classList.add('lb-open');
  };
  const close = () => {
    if (typeof dlg.close === 'function') dlg.close();
    else { dlg.removeAttribute('open'); document.body.classList.remove('lb-open'); }
  };
  dlg.addEventListener('close', () => document.body.classList.remove('lb-open'));

  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-lb]');
    if (trigger && items.length) { e.preventDefault(); open(trigger.dataset.lb); }
  });
  document.getElementById('lbClose').addEventListener('click', close);
  document.getElementById('lbPrev').addEventListener('click', () => show(index - 1));
  document.getElementById('lbNext').addEventListener('click', () => show(index + 1));
  dlg.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(index - 1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); show(index + 1); }
  });
  // 그림 바깥을 누르면 닫기
  let swiped = false;
  dlg.addEventListener('click', (e) => {
    if (swiped) { swiped = false; return; }
    if (e.target === dlg || e.target.classList.contains('lb-stage')) close();
  });
  // 좌우로 밀어서 넘기기
  let startX = null;
  let startY = null;
  const stage = dlg.querySelector('.lb-stage');
  stage.addEventListener('pointerdown', (e) => { startX = e.clientX; startY = e.clientY; });
  stage.addEventListener('pointerup', (e) => {
    if (startX === null) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    startX = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
      swiped = true;
      show(index + (dx < 0 ? 1 : -1));
    }
  });
})();
