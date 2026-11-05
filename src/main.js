const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- 헤더, 연도 ----------
const header = document.querySelector('.header');
const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

document.getElementById('year').textContent = new Date().getFullYear();

// ---------- 스크롤 등장 ----------
const revealIO = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('is-in');
      revealIO.unobserve(entry.target);
    }
  },
  { rootMargin: '0px 0px -8% 0px' },
);
document.querySelectorAll('[data-reveal]').forEach((el) => revealIO.observe(el));

// ---------- 프로젝트 목록: 커서를 따라다니는 미리보기 ----------
const indexList = document.querySelector('.index-list');
const preview = document.querySelector('.index-preview');

if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
  let x = 0, y = 0, tx = 0, ty = 0, frame = 0;
  const follow = reduceMotion ? 1 : 0.18;

  const tick = () => {
    x += (tx - x) * follow;
    y += (ty - y) * follow;
    preview.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    frame = Math.abs(tx - x) + Math.abs(ty - y) > 0.5 ? requestAnimationFrame(tick) : 0;
  };
  const aim = (e) => {
    tx = e.clientX;
    ty = e.clientY;
    // 오른쪽 끝에 가까우면 미리보기를 커서 왼쪽에 띄운다
    preview.classList.toggle('flip', tx > window.innerWidth - 400);
    if (!frame) frame = requestAnimationFrame(tick);
  };

  indexList.addEventListener('pointerenter', (e) => {
    x = tx = e.clientX;
    y = ty = e.clientY;
    aim(e);
  });
  indexList.addEventListener('pointermove', aim);
  indexList.addEventListener('pointerleave', () => preview.classList.remove('on'));
  indexList.querySelectorAll('[data-preview]').forEach((row) => {
    row.addEventListener('pointerenter', () => {
      preview.dataset.show = row.dataset.preview;
      preview.classList.add('on');
    });
  });
}

// ---------- 프로젝트 데모 ----------
// 데모마다 단계를 바꿔 가며 .scene에 data-step을 붙이고, 모양은 CSS가 맡는다.
const wait = (ms, signal) =>
  new Promise((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason);
    const timer = setTimeout(resolve, ms);
    signal.addEventListener('abort', () => { clearTimeout(timer); reject(signal.reason); }, { once: true });
  });

const demos = {
  async weight(scene, sleep) {
    const num = scene.querySelector('[data-count]');
    const from = 80.8, to = 69.5, steps = 45;
    num.textContent = from.toFixed(1);
    scene.dataset.step = 'idle';
    await sleep(400);
    scene.dataset.step = 'in';
    await sleep(500);
    scene.dataset.step = 'draw';
    for (let i = 1; i <= steps; i++) {
      const t = 1 - Math.pow(1 - i / steps, 3);
      num.textContent = (from + (to - from) * t).toFixed(1);
      await sleep(40);
    }
    await sleep(2600);
    scene.dataset.step = 'out';
    await sleep(700);
  },

  async memo(scene, sleep) {
    const query = scene.querySelector('[data-typed]');
    const tag = scene.querySelector('[data-tag]');
    for (const [text, label] of [['ㅈㅇㄹㄷㄹ', '초성 검색'], ['자이로드럽', '오타 허용']]) {
      scene.dataset.step = 'type';
      query.textContent = '';
      tag.textContent = label;
      await sleep(500);
      for (const ch of text) {
        query.textContent += ch;
        await sleep(150 + Math.random() * 110);
      }
      await sleep(350);
      scene.dataset.step = 'found';
      await sleep(2600);
      scene.dataset.step = 'clear';
      await sleep(350);
      while (query.textContent) {
        query.textContent = query.textContent.slice(0, -1);
        await sleep(55);
      }
    }
  },

  async pocket(scene, sleep) {
    scene.dataset.step = 'idle';
    await sleep(700);
    scene.dataset.step = 'notify';
    await sleep(1800);
    scene.dataset.step = 'record';
    await sleep(3000);
    scene.dataset.step = 'out';
    await sleep(700);
  },

  async voca(scene, sleep) {
    scene.dataset.step = 'idle';
    await sleep(600);
    scene.dataset.step = 'move';
    await sleep(1100);
    scene.dataset.step = 'card';
    await sleep(3400);
    scene.dataset.step = 'leave';
    await sleep(1100);
  },

  async eink(scene, sleep) {
    for (const device of ['a', 'b']) {
      scene.dataset.step = device;
      await sleep(2200);
      scene.dataset.step = `${device}-flash`;
      await sleep(900);
      scene.dataset.step = device;
      await sleep(2400);
    }
  },
};

const running = new Map();

const play = (scene) => {
  if (reduceMotion || running.has(scene)) return;
  const controller = new AbortController();
  running.set(scene, controller);
  const sleep = (ms) => wait(ms, controller.signal);
  const run = demos[scene.dataset.demo];
  (async () => {
    try {
      for (;;) await run(scene, sleep);
    } catch {
      // 멈춤 신호로 끝난 경우
    }
  })();
};

const stop = (scene) => {
  const controller = running.get(scene);
  if (!controller) return;
  controller.abort();
  running.delete(scene);
  scene.dataset.step = 'idle';
};

// ---------- 넓은 화면: 고정된 기기 프레임 ----------
const chapters = [...document.querySelectorAll('.chapter')];
const stageDevice = document.querySelector('.stage-device');
const stageName = document.querySelector('.stage-name');
const stageBars = [...document.querySelectorAll('.stage-bars i')];
const desktop = window.matchMedia('(min-width: 1024px)');

const inlineScenes = chapters.map((chapter) => chapter.querySelector('.scene'));
const stageScenes = chapters.map((chapter) => {
  const clone = chapter.querySelector('.scene').cloneNode(true);
  clone.dataset.for = chapter.id;
  clone.querySelectorAll('img').forEach((img) => { img.alt = ''; });
  stageDevice.append(clone);
  return clone;
});

if (!reduceMotion) [...inlineScenes, ...stageScenes].forEach((scene) => { scene.dataset.step = 'idle'; });

const visible = new Set();

const sync = () => {
  const wide = desktop.matches;
  inlineScenes.forEach((scene) => (!wide && visible.has(scene) ? play(scene) : stop(scene)));
  stageScenes.forEach((scene) =>
    wide && visible.has(stageDevice) && scene.classList.contains('is-active') ? play(scene) : stop(scene),
  );
};

let activeChapter = null;
const setActive = (chapter) => {
  if (chapter === activeChapter) return;
  activeChapter = chapter;
  const index = chapters.indexOf(chapter);
  chapters.forEach((c) => c.classList.toggle('is-active', c === chapter));
  stageScenes.forEach((s) => s.classList.toggle('is-active', s.dataset.for === chapter.id));
  stageBars.forEach((bar, i) => bar.classList.toggle('on', i === index));
  stageDevice.dataset.device = chapter.dataset.device;
  stageName.textContent = chapter.dataset.name;
  stageName.classList.remove('swap');
  void stageName.offsetWidth; // 애니메이션을 처음부터 다시 재생
  stageName.classList.add('swap');
  sync();
};

// 화면 가운데 가로줄에 걸친 챕터를 지금 읽는 챕터로 본다
const chapterIO = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) if (entry.isIntersecting) setActive(entry.target);
  },
  { rootMargin: '-45% 0px -54% 0px' },
);
chapters.forEach((chapter) => chapterIO.observe(chapter));

const sceneIO = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    }
    sync();
  },
  { threshold: 0.35 },
);
[...inlineScenes, stageDevice].forEach((el) => sceneIO.observe(el));
desktop.addEventListener('change', sync);

setActive(chapters[0]);

// ---------- 메일 주소 복사 ----------
const copyButton = document.querySelector('[data-copy]');
const copyLabel = copyButton.querySelector('span');
let copyTimer = 0;
copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(copyButton.dataset.copy);
    copyLabel.textContent = '복사했어요';
    copyButton.classList.add('done');
  } catch {
    copyLabel.textContent = '복사하지 못했어요';
  }
  clearTimeout(copyTimer);
  copyTimer = setTimeout(() => {
    copyLabel.textContent = '주소 복사';
    copyButton.classList.remove('done');
  }, 2000);
});
