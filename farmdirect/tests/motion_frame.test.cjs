// Run: node --test tests/motion_frame.test.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/motion_frame.js'), 'utf8');

function setup() {
  const frames = new Map();
  let id = 0;
  const context = {window: {}, requestAnimationFrame: fn => {frames.set(++id, fn); return id;}, cancelAnimationFrame: id => frames.delete(id)};
  vm.runInNewContext(source, context);
  const flush = () => {const callbacks = [...frames.values()]; frames.clear(); callbacks.forEach(fn => fn());};
  return {motion: context.window.FDMotion, frames, flush};
}

test('high-rate pointer events share a single measurement before all writes', () => {
  const {motion, frames, flush} = setup();
  const events = new Map();
  const sequence = [];
  const surface = {isConnected: true,
    getBoundingClientRect() {sequence.push('read'); return {left: 0, top: 0, width: 100, height: 100};},
    addEventListener(name, fn) {if (!events.has(name)) events.set(name, []); events.get(name).push(fn);}
  };
  motion.pointer(surface, (r, x) => sequence.push(`tilt:${x}`));
  motion.pointer(surface, (r, x) => sequence.push(`glow:${x}`));
  for (let x=0; x<100; x++) events.get('pointermove').forEach(fn => fn({clientX:x, clientY:30}));
  assert.equal(frames.size, 1);
  flush();
  assert.deepEqual(sequence, ['read', 'tilt:99', 'glow:99']);
  assert.equal(frames.size, 0);
});

test('leaving before the next frame cancels stale hover work', () => {
  const {motion, frames, flush} = setup();
  const events = {};
  let painted = false, reset = false;
  const surface = {isConnected: true, addEventListener: (name, fn) => events[name] = fn,
    getBoundingClientRect() {throw Error('Unexpected measurement after leave');}};
  motion.pointer(surface, () => painted = true, () => reset = true);
  events.pointermove({clientX:10,clientY:20});
  events.pointerleave();
  flush();
  assert.equal(painted, false);
  assert.equal(reset, true);
  assert.equal(frames.size, 0);
});

test('different surfaces are all measured before any style write', () => {
  const {motion, flush} = setup();
  const sequence = [];
  motion.schedule('a', () => sequence.push('read a'), () => sequence.push('write a'));
  motion.schedule('b', () => sequence.push('read b'), () => sequence.push('write b'));
  flush();
  assert.deepEqual(sequence, ['read a','read b','write a','write b']);
});
