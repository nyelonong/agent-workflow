(function (root) {
  "use strict";

  function pairLines(lines) {
    const rows = [];
    let old = [];
    let added = [];
    const flush = () => {
      for (let i = 0; i < Math.max(old.length, added.length); i++) {
        rows.push({old: old[i] ?? null, new: added[i] ?? null});
      }
      old = [];
      added = [];
    };
    lines.forEach((line, index) => {
      if (line.type === "remove") {
        if (added.length) flush();
        old.push(index);
      } else if (line.type === "add") {
        added.push(index);
      } else {
        flush();
        rows.push(line.type === "context" ? {old: index, new: index} : {meta: index});
      }
    });
    flush();
    return rows;
  }

  function rangeFor(lines, side, from, to) {
    if (!['old', 'new'].includes(side) || !Number.isInteger(from) || !Number.isInteger(to)) return null;
    const first = Math.min(from, to);
    const last = Math.max(from, to);
    if (first < 0 || last >= lines.length) return null;
    const numbers = lines.slice(first, last + 1).map(line => line[side + '_line']).filter(number => number != null);
    if (!numbers.length || numbers.some((number, i) => i > 0 && number !== numbers[i - 1] + 1)) return null;
    return {start_line: numbers[0], end_line: numbers[numbers.length - 1]};
  }

  const api = {pairLines, rangeFor};
  root.ReviewDiff = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
