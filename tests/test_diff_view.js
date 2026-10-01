const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {pairLines, rangeFor} = require('../assets/review-diff.js');

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

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.style = {};
    this.listeners = {};
    this.hidden = false;
    this.classes = new Set();
    this.classList = {
      contains: name => this.classes.has(name),
      add: name => this.classes.add(name), remove: name => this.classes.delete(name),
      toggle: (name, on) => on ? this.classes.add(name) : this.classes.delete(name),
    };
  }
  set className(value) { this.classes = new Set(value.split(' ')); }
  get className() { return [...this.classes].join(' '); }
  set textContent(value) { this.text = value; this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(child => child.textContent).join(''); }
  append(...children) { children.forEach(child => this.appendChild(child)); }
  appendChild(child) { child.parent = this; this.children.push(child); }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  getBoundingClientRect() { return {top: 0, bottom: 200}; }
  scrollIntoView() { this.scrolled = true; }
  matches(selector) {
    const className = /^\.([\w-]+)/.exec(selector);
    if (className && !this.classes.has(className[1])) return false;
    return [...selector.matchAll(/\[data-([\w-]+)(?:="([^"]*)")?\]/g)]
      .every(([, key, value]) => key in this.dataset && (value === undefined || this.dataset[key] === value));
  }
  closest(selector) { return this.matches(selector) ? this : this.parent?.closest(selector); }
  querySelectorAll(selector) {
    return this.children.flatMap(child => [...(child.matches(selector) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

function page(lines) {
  const ui = Object.fromEntries(['diff', 'files', 'current-file', 'current-file-path', 'current-file-position',
    'view-inline', 'view-split', 'file-filter', 'composer-text'].map(id => [id, new Element()]));
  const state = {files: [{repository: '/repo', path: 'src/example.js', status: 'modified', added: 1, removed: 1, lines}],
    threads: [], expanded: new Set([0]), diffView: 'split', selection: null, painted: [], dragging: false, filter: ''};
  const context = {state, boot: {mode: 'diff', maxLines: 1500}, ReviewDiff: {pairLines, rangeFor},
    el: id => ui[id], document: {createElement: () => new Element(), querySelector: selector => ui.diff.querySelector(selector)},
    lineTokens: () => null, fileIcon: () => new Element(), statusClass: () => '',
    hideComposer() {}, setCommentsCollapsed() {}, renderFiles() {},
    visibleFiles: () => state.filter ? [] : state.files};
  const functions = ['sideNumber', 'pathLabel', 'makeRow', 'makeSideCell', 'diffRow', 'setDiffView', 'renderDiff',
    'markThreadedRows', 'lineNumberFor', 'paintSelection', 'onRowPress', 'extendDiffSelection', 'selectionTarget',
    'jumpToThread', 'trackFile'];
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
