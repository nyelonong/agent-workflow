const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {pairLines, rangeFor, wordRanges, moveSelection} = require('../assets/review-diff.js');

const line = (type, old_line, new_line, text = type) => ({type, old_line, new_line, text});

test('context and unequal replacement blocks retain source row coordinates', () => {
  const lines = [line('meta', null, null), line('context', 1, 1),
    line('remove', 2, null), line('remove', 3, null), line('add', null, 2),
    line('context', 4, 3)];
  assert.deepEqual(pairLines(lines), [
    {meta: 0}, {old: 1, new: 1}, {old: 2, new: 4},
    {old: 3, new: null}, {old: 5, new: 5},
  ]);
});

test('metadata separates hunks and no-newline markers', () => {
  const lines = [line('remove', 1, null), line('meta', null, null),
    line('add', null, 1), line('meta', null, null), line('context', 100, 100)];
  assert.deepEqual(pairLines(lines), [
    {old: 0, new: null}, {meta: 1}, {old: null, new: 2}, {meta: 3}, {old: 4, new: 4},
  ]);
});

test('every existing source line appears exactly once on its own side', () => {
  for (let removed = 0; removed < 5; removed++) {
    for (let added = 0; added < 5; added++) {
      const lines = [line('context', 1, 1),
        ...Array.from({length: removed}, (_, i) => line('remove', i + 2, null)),
        ...Array.from({length: added}, (_, i) => line('add', null, i + 2)),
        line('context', removed + 2, added + 2)];
      const original = JSON.stringify(lines);
      const pairs = pairLines(lines);
      for (const side of ['old', 'new']) {
        const shown = pairs.filter(row => row[side] != null).map(row => lines[row[side]][side + '_line']);
        assert.deepEqual(shown, lines.map(row => row[side + '_line']).filter(number => number != null));
      }
      assert.equal(JSON.stringify(lines), original);
    }
  }
  assert.deepEqual(pairLines([]), []);
});

test('selection ranges retain old/new coordinates and tolerate opposite-side gaps', () => {
  const lines = [line('context', 8, 8), line('remove', 9, null),
    line('add', null, 9), line('add', null, 10), line('context', 10, 11)];
  assert.deepEqual(rangeFor(lines, 'old', 0, 4), {start_line: 8, end_line: 10});
  assert.deepEqual(rangeFor(lines, 'new', 4, 0), {start_line: 8, end_line: 11});
  assert.equal(rangeFor(lines, 'old', 2, 3), null);
});

test('missing sides and discontinuous or invalid ranges cannot become annotations', () => {
  const lines = [line('context', 1, 1), line('meta', null, null), line('context', 100, 100)];
  assert.equal(rangeFor(lines, 'old', 0, 2), null);
  assert.equal(rangeFor(lines, 'new', 1, 1), null);
  assert.equal(rangeFor(lines, 'other', 0, 0), null);
  assert.equal(rangeFor(lines, 'new', -1, 2), null);
  assert.equal(rangeFor(lines, 'new', 0, 99), null);
});

const changedText = (text, ranges) => ranges.map(([start, end]) => text.slice(start, end));

test('word changes emphasize only differing words and values', () => {
  const before = 'const count = 1;';
  const after = 'const total = 2;';
  const ranges = wordRanges(before, after);
  assert.deepEqual(changedText(before, ranges.old), ['count', '1']);
  assert.deepEqual(changedText(after, ranges.new), ['total', '2']);
  assert.deepEqual(wordRanges(after, after), {old: [], new: []});
});

test('word ranges retain repeated words, punctuation, spaces and Unicode offsets', () => {
  for (const [before, after, old, added] of [
    ['foo(foo);', 'foo(bar);', ['foo'], ['bar']],
    ['a+b', 'a-b', ['+'], ['-']],
    ['a  b', 'a b', ['  '], [' ']],
    ['const 名 = "😀";', 'const 名 = "😎";', ['😀'], ['😎']],
    ['<img src=x>', '<img src=y>', ['x'], ['y']],
    ['', 'new', [], ['new']],
    ['old', '', ['old'], []],
  ]) {
    const ranges = wordRanges(before, after);
    assert.deepEqual(changedText(before, ranges.old), old);
    assert.deepEqual(changedText(after, ranges.new), added);
    for (const [text, spans] of [[before, ranges.old], [after, ranges.new]]) {
      assert.ok(spans.every(([start, end], i) => start >= 0 && end <= text.length && end > start && (!i || start > spans[i - 1][1])));
    }
  }
});

test('oversized word comparisons fall back without truncated text or partial ranges', () => {
  assert.equal(wordRanges('x '.repeat(400), 'y '.repeat(400)), null);
  assert.deepEqual(wordRanges('', ''), {old: [], new: []});
});

test('keyboard navigation moves and extends existing same-side source lines', () => {
  const lines = [line('meta', null, null), line('context', 8, 8), line('remove', 9, null),
    line('add', null, 9), line('context', 10, 10), line('meta', null, null), line('context', 100, 100)];
  const first = moveSelection(lines, null, 'ArrowDown');
  assert.deepEqual(first, {side: 'new', from: 1, to: 1});
  const next = moveSelection(lines, first, 'ArrowDown', true);
  assert.deepEqual(next, {side: 'new', from: 1, to: 3});
  assert.deepEqual(rangeFor(lines, next.side, next.from, next.to), {start_line: 8, end_line: 9});
  assert.deepEqual(moveSelection(lines, next, 'ArrowUp', true), first);
  assert.deepEqual(moveSelection(lines, first, 'ArrowLeft'), {side: 'old', from: 1, to: 1});
  assert.equal(moveSelection(lines, {side: 'old', from: 4, to: 4}, 'ArrowDown', true), null);
  assert.deepEqual(moveSelection(lines, {side: 'old', from: 4, to: 4}, 'ArrowDown'), {side: 'old', from: 6, to: 6});
});

test('keyboard side changes follow visual pairs and cannot select blank sides', () => {
  const lines = [line('remove', 1, null), line('remove', 2, null), line('add', null, 1)];
  const old = {side: 'old', from: 0, to: 0};
  const added = moveSelection(lines, old, 'ArrowRight');
  assert.deepEqual(added, {side: 'new', from: 2, to: 2});
  assert.deepEqual(moveSelection(lines, added, 'ArrowLeft'), old);
  assert.equal(moveSelection(lines, {side: 'old', from: 1, to: 1}, 'ArrowRight'), null);
  assert.deepEqual(moveSelection(lines, null, 'ArrowDown'), old);
  assert.equal(moveSelection(lines, old, 'ArrowUp'), null);
  assert.equal(moveSelection([], null, 'ArrowDown'), null);
  assert.equal(moveSelection([line('meta', null, null)], null, 'ArrowDown'), null);
  assert.equal(moveSelection(lines, old, 'Enter'), null);
  assert.equal(moveSelection(lines, {side: 'old', from: 0.5, to: 0.5}, 'ArrowDown'), null);
});

const pageSource = fs.readFileSync(path.join(__dirname, '../scripts/html_review.py'), 'utf8');
function pageFunction(name) {
  const start = pageSource.indexOf('function ' + name + '(');
  assert.ok(start >= 0, name);
  let depth = 0;
  for (let i = pageSource.indexOf('{', start); i < pageSource.length; i++) {
    depth += pageSource[i] === '{' ? 1 : pageSource[i] === '}' ? -1 : 0;
    if (!depth) return pageSource.slice(start, i + 1);
  }
  throw new Error('Unclosed page function: ' + name);
}

class TextNode {
  constructor(text) { this.nodeType = 3; this.data = text; }
  get textContent() { return this.data; }
  replaceWith(...nodes) {
    const parent = this.parent;
    parent.children.splice(parent.children.indexOf(this), 1, ...nodes);
    nodes.forEach(node => { node.parent = parent; });
  }
}

class Element {
  constructor(tag = 'div') {
    this.nodeType = 1;
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.style = {};
    this.listeners = {};
    this.hidden = false;
    this.scrollTop = 0;
    this.classes = new Set();
    this.classList = {
      contains: name => this.classes.has(name),
      add: name => this.classes.add(name), remove: name => this.classes.delete(name),
      toggle: (name, on) => on ? this.classes.add(name) : this.classes.delete(name),
    };
  }
  set className(value) { this.classes = new Set(value.split(' ')); }
  get className() { return [...this.classes].join(' '); }
  set textContent(value) { this.children = []; if (value) this.appendChild(new TextNode(value)); }
  get textContent() { return this.children.map(child => child.textContent).join(''); }
  get childNodes() { return this.children; }
  get firstElementChild() { return this.children.find(child => child.nodeType === 1) || null; }
  append(...children) { children.forEach(child => this.appendChild(child)); }
  appendChild(child) { child.parent = this; this.children.push(child); }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  getBoundingClientRect() { return this.bounds || {top: 0, bottom: 200}; }
  scrollIntoView() { this.scrolled = true; if (this.onScroll) this.onScroll(); }
  focus() { this.focused = true; }
  matches(selector) {
    const tag = /^[a-z][a-z0-9-]*/i.exec(selector);
    if (tag && this.tagName !== tag[0].toUpperCase()) return false;
    const className = /^\.([\w-]+)/.exec(selector);
    if (className && !this.classes.has(className[1])) return false;
    return [...selector.matchAll(/\[data-([\w-]+)(?:="([^"]*)")?\]/g)]
      .every(([, key, value]) => key in this.dataset && (value === undefined || this.dataset[key] === value));
  }
  closest(selector) { return this.matches(selector) ? this : this.parent?.closest(selector); }
  querySelectorAll(selector) {
    return this.children.filter(child => child.nodeType === 1)
      .flatMap(child => [...(child.matches(selector) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

function page(lines) {
  const ui = Object.fromEntries(['diff', 'files', 'current-file', 'current-file-path', 'current-file-position',
    'view-inline', 'view-split', 'wrap-lines', 'file-filter', 'composer', 'composer-text', 'composer-where', 'help', 'message',
    'previous-change', 'next-change', 'change-position', 'tab-diff', 'tab-guided'].map(id => [id, new Element()]));
  ui.composer.hidden = true;
  ui.help.hidden = true;
  const state = {files: [{repository: '/repo', path: 'src/example.js', status: 'modified', added: 1, removed: 1, lines}],
    threads: [], expanded: new Set([0]), diffView: 'split', reviewView: 'diff', reviewedChapters: new Set(), wrapLines: true, selection: null, painted: [], dragging: false, filter: ''};
  const context = {state, boot: {mode: 'diff', maxLines: 1500}, ReviewDiff: {pairLines, rangeFor, wordRanges, moveSelection},
    el: id => ui[id], document: {createElement: tag => new Element(tag), createTextNode: text => new TextNode(text), querySelector: selector => ui.diff.querySelector(selector)},
    lineTokens: () => null, fileIcon: () => new Element(), statusClass: () => '',
    getComputedStyle: node => ({scrollMarginTop: node.dataset.row === undefined ? '0px' : '44px'}),
    hideComposer() {}, setCommentsCollapsed() {}, renderFiles() {},
    visibleFiles: () => state.files.filter(file => file.path.includes(state.filter))};
  const functions = ['sideNumber', 'pathLabel', 'makeRow', 'makeSideCell', 'diffRow', 'setDiffView', 'renderDiff', 'renderFileDiff',
    'setReviewView', 'onReviewTabKey', 'renderGuideOverview', 'renderGuidedDiff', 'visibleFiles',
    'markThreadedRows', 'lineNumberFor', 'paintSelection', 'onRowPress', 'extendDiffSelection', 'selectionTarget',
    'jumpToThread', 'trackFile', 'markCodeChanges', 'readingPosition', 'restoreReadingPosition', 'setWrapLines',
    'onDiffKey', 'onSelectionEnter', 'showComposer', 'say', 'collectChangeStops', 'changeElement', 'trackChanges', 'stepChange'];
  vm.createContext(context);
  vm.runInContext(functions.map(pageFunction).join('\n'), context);
  context.renderDiff();
  return {context, state, ui};
}

test('clicks, shift selection and drags create side-specific annotations', () => {
  const {context, state} = page([line('context', 8, 8), line('remove', 9, null), line('add', null, 9)]);
  const old = context.diffRow(0, 0, 'old');
  old.listeners.mousedown({target: old.children[2], button: 0});
  assert.equal(context.selectionTarget().side, 'old');
  const removed = context.diffRow(0, 1, 'old');
  context.extendDiffSelection({target: removed.children[2], buttons: 1});
  assert.equal(context.selectionTarget().end_line, 9);
  const added = context.diffRow(0, 2, 'new');
  context.extendDiffSelection({target: added.children[2], buttons: 1});
  assert.equal(context.selectionTarget().side, 'old');
  added.listeners.mousedown({target: added.children[2], button: 0, shiftKey: true});
  assert.equal(context.selectionTarget().side, 'new');
  assert.equal(context.selectionTarget().start_line, 9);
  assert.equal(state.painted.length, 1);
  assert.equal(state.painted[0].dataset.side, 'new');
});

test('word emphasis crosses syntax spans safely without changing rendered code', () => {
  const source = '<img src=x>😀';
  const code = new Element('span');
  const syntax = new Element('span');
  syntax.className = 'hljs-string';
  syntax.textContent = 'img src=x';
  code.append(new TextNode('<'), syntax, new TextNode('>😀'));
  const context = {document: {createElement: tag => new Element(tag), createTextNode: text => new TextNode(text)}};
  vm.createContext(context);
  vm.runInContext(pageFunction('markCodeChanges'), context);
  context.markCodeChanges(code, [[1, 10], [11, 13]]);
  assert.equal(code.textContent, source);
  assert.equal(code.querySelectorAll('.word-change').map(mark => mark.textContent).join(''), 'img src=x😀');
  assert.equal(code.querySelector('.hljs-string'), syntax);
  assert.ok(code.querySelectorAll('.word-change').every(mark => mark.tagName === 'MARK'));
});

test('both rendered layouts emphasize changed words while retaining code and coordinates', () => {
  const before = 'const count = 1;';
  const after = 'const total = 2;';
  const {context, state, ui} = page([line('remove', 4, null, before), line('add', null, 4, after)]);
  for (const layout of ['split', 'inline']) {
    context.setDiffView(layout);
    assert.equal(context.diffRow(0, 0, 'old').querySelector('.code').textContent, before);
    assert.equal(context.diffRow(0, 1, 'new').querySelector('.code').textContent, after);
    assert.deepEqual(ui.diff.querySelectorAll('.word-change').map(mark => mark.textContent), ['count', '1', 'total', '2']);
    state.selection = {fileIndex: 0, side: 'old', from: 0, to: 0};
    assert.equal(context.selectionTarget().start_line, 4);
  }
});

test('wrapping preference and annotations survive reading-control changes', () => {
  const {context, state, ui} = page([line('context', 1, 1)]);
  state.pendingTarget = {side: 'new', start_line: 1};
  ui['composer-text'].value = 'Draft';
  context.setWrapLines(false);
  assert.ok(ui.diff.querySelector('.file').classes.has('nowrap'));
  context.setDiffView('inline');
  assert.equal(state.wrapLines, false);
  assert.ok(ui.diff.querySelector('.file').classes.has('nowrap'));
  context.setWrapLines(true);
  assert.equal(state.pendingTarget.start_line, 1);
  assert.equal(ui['composer-text'].value, 'Draft');
  context.boot.mode = 'document';
  context.setWrapLines(false);
  assert.equal(state.wrapLines, true);
});

test('real frontend keyboard handling targets source lines and guards other controls', () => {
  const {context, state, ui} = page([line('context', 1, 1), line('remove', 2, null), line('add', null, 2)]);
  let prevented = 0;
  const key = (key, extra = {}) => ({key, target: ui.diff, preventDefault() { prevented++; }, ...extra});
  context.onDiffKey(key('ArrowDown'));
  context.onDiffKey(key('ArrowLeft'));
  context.onDiffKey(key('ArrowDown', {shiftKey: true}));
  assert.equal(context.selectionTarget().side, 'old');
  assert.equal(context.selectionTarget().end_line, 2);
  assert.match(ui.message.textContent, /Before.*1.*2/);
  assert.ok(context.diffRow(0, 1, 'old').scrolled);
  const selection = JSON.stringify(state.selection);
  for (const extra of [{target: new Element('input')}, {ctrlKey: true}, {altKey: true}, {metaKey: true}]) {
    context.onDiffKey(key('ArrowDown', extra));
    assert.equal(JSON.stringify(state.selection), selection);
  }
  for (const guard of ['submitted', 'dialog']) {
    state[guard] = true;
    context.onDiffKey(key('ArrowUp'));
    assert.equal(JSON.stringify(state.selection), selection);
    state[guard] = false;
  }
  ui.composer.hidden = false;
  context.onDiffKey(key('ArrowUp'));
  assert.equal(JSON.stringify(state.selection), selection);
  ui.composer.hidden = true;
  ui.help.hidden = false;
  context.onDiffKey(key('ArrowUp'));
  assert.equal(JSON.stringify(state.selection), selection);
  ui.help.hidden = true;
  context.boot.mode = 'document';
  context.onDiffKey(key('ArrowDown'));
  assert.equal(JSON.stringify(state.selection), selection);
  assert.equal(prevented, 3);
});

test('Enter comments only in the focused diff pane and preserves parked drafts', () => {
  const {context, state, ui} = page([line('context', 7, 7)]);
  state.selection = {fileIndex: 0, side: 'new', from: 0, to: 0};
  let prevented = 0;
  const enter = extra => ({key: 'Enter', target: ui.diff, preventDefault() { prevented++; }, ...extra});
  for (const extra of [{target: new Element('button')}, {target: new Element('input')},
    {target: new Element('textarea')}, {ctrlKey: true}, {metaKey: true}, {altKey: true}]) {
    assert.equal(context.onSelectionEnter(enter(extra)), false);
  }
  for (const guard of ['submitted', 'dialog']) {
    state[guard] = true;
    assert.equal(context.onSelectionEnter(enter()), false);
    state[guard] = false;
  }
  ui.help.hidden = false;
  assert.equal(context.onSelectionEnter(enter()), false);
  ui.help.hidden = true;
  ui.composer.hidden = false;
  ui['composer-text'].value = 'Keep draft';
  assert.equal(context.onSelectionEnter(enter()), false);
  assert.equal(ui['composer-text'].value, 'Keep draft');
  ui.composer.hidden = true;
  assert.equal(context.onSelectionEnter(enter()), true);
  assert.equal(state.pendingTarget.start_line, 7);
  assert.equal(ui.composer.hidden, false);
  assert.equal(ui['composer-text'].focused, true);
  assert.equal(prevented, 1);
});

test('keyboard selection recovers an existing line after scrolling below the final source row', () => {
  const {context, ui} = page([line('context', 1, 1), line('context', 2, 2)]);
  for (const row of ui.diff.querySelectorAll('.row[data-row]')) row.getBoundingClientRect = () => ({top: -30, bottom: -10});
  context.onDiffKey({key: 'ArrowUp', target: ui.diff, preventDefault() {}});
  assert.equal(context.selectionTarget().start_line, 2);
});

test('view changes preserve saved annotations and unsent comment targets', () => {
  const {context, state, ui} = page([line('context', 1, 1), line('remove', 2, null), line('add', null, 2)]);
  const target = {scope: 'line', repository: '/repo', path: 'src/example.js', side: 'old', start_line: 2, end_line: 2};
  state.threads.push({text: 'Check the old line', target});
  state.pendingTarget = target;
  ui['composer-text'].value = 'Unsent draft';
  const original = JSON.stringify(state.threads);
  context.setDiffView('inline');
  context.setDiffView('split');
  assert.equal(JSON.stringify(state.threads), original);
  assert.equal(state.pendingTarget, target);
  assert.equal(ui['composer-text'].value, 'Unsent draft');
  assert.ok(context.diffRow(0, 1, 'old').classes.has('threaded'));
  assert.ok(!context.diffRow(0, 2, 'new').classes.has('threaded'));
  state.filter = 'hidden-file';
  context.jumpToThread(state.threads[0]);
  assert.equal(state.filter, '');
  assert.equal(context.diffRow(0, 1, 'old').scrolled, true);
});

test('empty cells cannot be selected and unlimited rendering works in both modes', () => {
  const lines = Array.from({length: 1502}, (_, i) => line('add', null, i + 1));
  const {context, ui} = page(lines);
  assert.equal(ui.diff.querySelectorAll('.row[data-row]').length, 1500);
  assert.equal(ui.diff.querySelector('.blank').listeners.mousedown, undefined);
  context.boot.maxLines = 0;
  context.renderDiff();
  assert.equal(ui.diff.querySelectorAll('.row[data-row]').length, lines.length);
  context.setDiffView('inline');
  assert.equal(ui.diff.querySelectorAll('.row[data-row]').length, lines.length);
});

function changePage(layout) {
  const hunk = text => ({type: 'meta', old_line: null, new_line: null, text});
  const fixture = page([hunk('@@ -1 +1 @@'), line('remove', 1, null), line('add', null, 1),
    hunk('@@ -40 +40 @@'), line('remove', 40, null), line('add', null, 40)]);
  const {context, state, ui} = fixture;
  state.files.push({...state.files[0], path: 'src/second.js', lines: [hunk('@@ -4 +4 @@'), line('add', null, 4)]});
  state.expanded.add(1);
  state.diffView = layout;
  context.renderDiff();
  ui.diff.children.forEach((block, file) => { block.bounds = {top: file * 500, bottom: (file + 1) * 500}; });
  for (const row of ui.diff.querySelectorAll('.row[data-row]')) {
    const top = Number(row.dataset.file) * 500 + Number(row.dataset.row) * 50;
    row.bounds = {top, bottom: top + 30};
  }
  context.trackFile();
  return fixture;
}

test('change navigation follows hunks across files in both layouts without wrapping', () => {
  for (const layout of ['inline', 'split']) {
    const {context, state, ui} = changePage(layout);
    assert.equal(ui['change-position'].textContent, 'Change 1 of 3');
    assert.equal(ui['previous-change'].disabled, true);
    context.stepChange(-1);
    assert.equal(ui.diff.querySelector('[data-file="0"][data-row="0"]').scrolled, undefined);
    context.stepChange(1);
    const second = ui.diff.querySelector('[data-file="0"][data-row="3"]');
    assert.equal(second.scrolled, true);
    second.bounds = {top: 44, bottom: 74};
    ui.diff.scrollTop = 106;
    context.trackFile();
    assert.equal(ui['change-position'].textContent, 'Change 2 of 3');
    context.stepChange(1);
    assert.equal(ui.diff.querySelector('[data-file="1"][data-row="0"]').scrolled, true);
    ui.diff.children[0].bounds = {top: -500, bottom: 0};
    ui.diff.children[1].bounds = {top: 0, bottom: 500};
    ui.diff.scrollTop = 500;
    context.trackFile();
    assert.equal(ui['next-change'].disabled, true);
    context.stepChange(1);
    assert.equal(state.currentChange, 2);
    context.stepChange(-1);
    assert.equal(second.scrolled, true);
  }
});

test('change navigation respects filtering and includes files without text hunks', () => {
  const {context, state, ui} = changePage('split');
  state.files.push({...state.files[0], path: 'image.png', binary: true, lines: []});
  state.filter = 'image.png';
  state.expanded.clear();
  context.renderDiff();
  assert.equal(ui['change-position'].textContent, 'Change 1 of 1');
  assert.equal(ui['previous-change'].disabled, true);
  assert.equal(ui['next-change'].disabled, true);
  state.filter = 'missing';
  context.renderDiff();
  assert.equal(ui['change-position'].textContent, '0 changes');
  assert.equal(ui['next-change'].disabled, true);
  context.stepChange(1);
  assert.equal(state.expanded.size, 0);
});

test('change navigation reveals collapsed and truncated hunks without changing drafts or annotations', () => {
  for (const layout of ['inline', 'split']) {
    const {context, state, ui} = changePage(layout);
    state.expanded.clear();
    context.renderDiff();
    context.stepChange(1);
    assert.equal(state.expanded.has(0), true);
    assert.equal(ui.diff.querySelector('[data-file="0"][data-row="0"]').scrolled, true);
    context.boot.maxLines = 3;
    context.renderDiff();
    const target = {scope: 'line', repository: '/repo', path: 'src/example.js', side: 'old', start_line: 1, end_line: 1};
    state.pendingTarget = target;
    state.threads.push({text: 'Keep this comment', target});
    ui['composer-text'].value = 'Keep this draft';
    ui.composer.hidden = false;
    context.stepChange(1);
    assert.equal(ui.diff.querySelector('[data-file="0"][data-row="3"]').scrolled, true);
    assert.equal(state.pendingTarget, target);
    assert.equal(ui['composer-text'].value, 'Keep this draft');
    assert.equal(state.threads[0].text, 'Keep this comment');
  }
});

test('change navigation stays inactive for document reviews and submitted decisions', () => {
  const {context, state, ui} = changePage('inline');
  context.boot.mode = 'document';
  context.stepChange(1);
  const second = ui.diff.querySelector('[data-file="0"][data-row="3"]');
  assert.equal(second.scrolled, undefined);
  context.boot.mode = 'diff';
  state.submitted = true;
  context.stepChange(1);
  assert.equal(second.scrolled, undefined);
});

test('clamped jumps advance the destination until manual scrolling resumes viewport tracking', () => {
  for (const layout of ['inline', 'split']) {
    const {context, state, ui} = changePage(layout);
    state.files.pop();
    context.renderDiff();
    const first = ui.diff.querySelector('[data-file="0"][data-row="0"]');
    const second = ui.diff.querySelector('[data-file="0"][data-row="3"]');
    first.bounds = {top: 0, bottom: 30};
    second.bounds = {top: 300, bottom: 330};
    second.onScroll = () => {
      ui.diff.scrollTop = 180;
      first.bounds = {top: -180, bottom: -150};
      second.bounds = {top: 120, bottom: 150};
    };
    context.trackFile();
    context.stepChange(1);
    assert.equal(ui['change-position'].textContent, 'Change 2 of 2');
    context.trackFile();
    assert.equal(ui['next-change'].disabled, true);
    context.stepChange(1);
    assert.equal(state.currentChange, 1);
    ui.diff.scrollTop = 0;
    first.bounds = {top: 0, bottom: 30};
    second.bounds = {top: 300, bottom: 330};
    context.trackFile();
    assert.equal(ui['change-position'].textContent, 'Change 1 of 2');
    assert.equal(ui['next-change'].disabled, false);
  }
});

function guidedPage(layout = 'split') {
  const fixture = changePage(layout);
  const {state} = fixture;
  state.data = {guide: {authored: true, summary: 'Share external content', before: 'No sharing', after: 'Sharing enabled',
    flow: {before: ['Content'], after: ['Content', 'Inbox', 'Thread']}, chapters: [
      {title: 'Receive content', summary: 'Receive intents first', file_indices: [1]},
      {title: 'Send content', summary: 'Upload and send', file_indices: [0]},
    ]}};
  return fixture;
}

test('Guided reorders one shared diff tree and preserves coordinates, comments, drafts and expansion', () => {
  for (const layout of ['inline', 'split']) {
    const {context, state, ui} = guidedPage(layout);
    const target = {scope: 'line', repository: '/repo', path: 'src/example.js', side: 'old', start_line: 40, end_line: 40};
    state.threads.push({text: 'Check this', target});
    state.pendingTarget = target;
    state.selection = {fileIndex: 0, side: 'old', from: 4, to: 4};
    ui['composer-text'].value = 'Unsent draft';
    const expanded = [...state.expanded];
    ui.diff.scrollTop = 120;
    context.setReviewView('guided');
    assert.equal(ui.diff.scrollTop, 0, 'first Guided visit starts at the overview');
    assert.deepEqual(ui.diff.querySelectorAll('.file').map(block => block.dataset.file), ['1', '0']);
    assert.deepEqual(Array.from(context.collectChangeStops(), stop => stop.fileIndex), [1, 0, 0]);
    assert.equal(context.selectionTarget().start_line, 40);
    assert.equal(context.diffRow(0, 4, 'old').classes.has('threaded'), true);
    assert.equal(ui.diff.attributes['aria-labelledby'], 'tab-guided');
    context.setDiffView(layout === 'split' ? 'inline' : 'split');
    context.jumpToThread(state.threads[0]);
    assert.equal(context.diffRow(0, 4, 'old').scrolled, true);
    context.setReviewView('diff');
    assert.deepEqual(ui.diff.querySelectorAll('.file').map(block => block.dataset.file), ['0', '1']);
    assert.equal(ui.diff.querySelectorAll('.guide-overview').length, 0);
    assert.equal(state.pendingTarget, target);
    assert.equal(ui['composer-text'].value, 'Unsent draft');
    assert.equal(state.threads[0].target, target);
    assert.deepEqual([...state.expanded], expanded);
    assert.equal(ui['tab-diff'].attributes['aria-selected'], 'true');
  }
});

test('Guided filtering, collapsed files and truncation retain navigation and complete source access', () => {
  const {context, state, ui} = guidedPage();
  state.files.push({...state.files[0], repository: '/other', path: 'src/example.js', binary: true, lines: []});
  state.expanded.add(2);
  state.data.guide.chapters.push({title: 'Other changes', summary: 'Review these too', file_indices: [2]});
  context.setReviewView('guided');
  assert.deepEqual(ui.diff.querySelectorAll('.file').map(block => block.dataset.file), ['1', '0', '2']);
  assert.equal(ui.diff.querySelectorAll('.row.meta').some(row => row.textContent.includes('Binary file')), true);
  state.filter = 'example';
  state.expanded.clear();
  context.boot.maxLines = 3;
  context.renderDiff();
  assert.deepEqual(Array.from(context.collectChangeStops(), stop => stop.fileIndex), [0, 0, 2]);
  context.stepChange(1);
  assert.equal(state.expanded.has(0), true);
  context.stepChange(1);
  assert.equal(context.diffRow(0, 5, 'new').dataset.row, '5');
  const target = {scope: 'line', repository: '/repo', path: 'src/second.js', side: 'new', start_line: 4, end_line: 4};
  context.jumpToThread({target});
  assert.equal(state.filter, '');
  assert.equal(context.diffRow(1, 1, 'new').scrolled, true);
  state.filter = 'missing';
  context.renderDiff();
  assert.equal(ui.diff.querySelectorAll('.file').length, 0);
  assert.equal(ui['change-position'].textContent, '0 changes');
});

test('guide text is literal, fallback is honest, and progress changes no comments or decision state', () => {
  const {context, state, ui} = guidedPage();
  const hostile = '<img src=x onerror=alert(1)>';
  state.data.guide.summary = hostile;
  state.data.guide.chapters[0].summary = hostile;
  context.setReviewView('guided');
  assert.ok(ui.diff.textContent.includes(hostile));
  assert.equal(ui.diff.querySelectorAll('.guide-overview')[0].querySelectorAll('img').length, 0);
  const progress = ui.diff.querySelector('.guide-progress').children[0];
  const threads = JSON.stringify(state.threads);
  progress.checked = true;
  progress.listeners.change();
  assert.equal(state.reviewedChapters.has(0), true);
  assert.equal(state.submitted, undefined);
  assert.equal(JSON.stringify(state.threads), threads);
  context.setReviewView('diff');
  context.setReviewView('guided');
  assert.equal(ui.diff.querySelector('.guide-progress').children[0].checked, true);
  state.data.guide.authored = false;
  state.data.guide.summary = 'No agent-authored guide was supplied.';
  context.renderDiff();
  assert.equal(ui.diff.querySelectorAll('.guide-comparison').length, 0);
  assert.ok(ui.diff.textContent.includes('Directory grouping'));
});

test('review tabs support keyboard focus and cannot alter document or submitted reviews', () => {
  const {context, state, ui} = guidedPage();
  let prevented = 0;
  context.onReviewTabKey({key: 'ArrowRight', preventDefault() { prevented++; }});
  assert.equal(state.reviewView, 'guided');
  assert.equal(ui['tab-guided'].focused, true);
  assert.equal(ui['tab-guided'].tabIndex, 0);
  assert.equal(ui['tab-diff'].tabIndex, -1);
  ui.diff.focused = false;
  ui.diff.querySelector('.guide-files').children[0].listeners.click();
  assert.equal(ui.diff.focused, true);
  context.onReviewTabKey({key: 'Home', preventDefault() { prevented++; }});
  assert.equal(state.reviewView, 'diff');
  context.boot.mode = 'document';
  context.setReviewView('guided');
  assert.equal(state.reviewView, 'diff');
  context.boot.mode = 'diff';
  state.submitted = true;
  context.setReviewView('guided');
  assert.equal(state.reviewView, 'diff');
  assert.equal(prevented, 2);
});
