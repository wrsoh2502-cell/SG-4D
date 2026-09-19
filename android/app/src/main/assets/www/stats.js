/*
 * SG 4D — frequency statistics.
 *
 * Read this before you read anything below it:
 *
 *   Draws are independent. A number that has not appeared for forty draws is
 *   exactly as likely to appear tonight as one that came up yesterday. Nothing
 *   computed in this file predicts anything, and the UI says so on every screen
 *   that renders it.
 *
 * What it is for, then: these are the numbers people actually want to look at,
 * and they are genuinely interesting as a description of what has happened. So
 * the arithmetic is honest — real counts over a stated window, with the
 * expected count shown alongside the observed one, so a "hot" digit is visibly
 * only a few appearances away from average rather than looking like a signal.
 */
window.SGStats = (function () {
  'use strict';

  function zeros(n) { var a = new Array(n); for (var i = 0; i < n; i++) a[i] = 0; return a; }

  /** Every 4-digit number a draw produced: 3 prizes + 10 starters + 10 consolations. */
  function allNumbers(draw) {
    return [draw.first, draw.second, draw.third]
      .concat(draw.starter || [], draw.consolation || [])
      .filter(Boolean);
  }

  /** Just the top three, for people who only count "real" wins. */
  function topNumbers(draw) {
    return [draw.first, draw.second, draw.third].filter(Boolean);
  }

  /**
   * Digit frequency by position across `draws`.
   * Returns positions[0..3][digit 0..9] plus an overall tally and the expected
   * count per cell, so the UI can show observed against expected.
   */
  function digitFrequency(draws, scope) {
    var pick = scope === 'top' ? topNumbers : allNumbers;
    var positions = [zeros(10), zeros(10), zeros(10), zeros(10)];
    var overall = zeros(10);
    var numberCount = 0;

    draws.forEach(function (d) {
      pick(d).forEach(function (n) {
        numberCount++;
        for (var p = 0; p < 4; p++) {
          var digit = parseInt(n.charAt(p), 10);
          positions[p][digit]++;
          overall[digit]++;
        }
      });
    });

    return {
      positions: positions,
      overall: overall,
      numberCount: numberCount,
      expectedPerPosition: numberCount / 10,
      expectedOverall: (numberCount * 4) / 10
    };
  }

  /**
   * How often each full 4-digit number has appeared, and how many draws ago it
   * last did. Only numbers that have actually appeared are returned — the other
   * ~9,000 are all tied at zero and listing them is noise.
   */
  function numberTally(draws, scope) {
    var pick = scope === 'top' ? topNumbers : allNumbers;
    var seen = {};
    draws.forEach(function (d, index) {          // draws arrive newest-first
      pick(d).forEach(function (n) {
        if (!seen[n]) seen[n] = { number: n, count: 0, lastIndex: index, lastDate: d.date };
        seen[n].count++;
        if (index < seen[n].lastIndex) {
          seen[n].lastIndex = index;
          seen[n].lastDate = d.date;
        }
      });
    });
    return Object.keys(seen).map(function (k) { return seen[k]; });
  }

  /** Draws since `number` last appeared, or null if it never has in this window. */
  function drawsSince(draws, number, scope) {
    var pick = scope === 'top' ? topNumbers : allNumbers;
    for (var i = 0; i < draws.length; i++) {
      if (pick(draws[i]).indexOf(String(number)) !== -1) return i;
    }
    return null;
  }

  /** Every past appearance of one number, newest first. */
  function appearances(draws, number) {
    var n = String(number);
    var out = [];
    draws.forEach(function (d) {
      var where = [];
      if (d.first === n) where.push('1st Prize');
      if (d.second === n) where.push('2nd Prize');
      if (d.third === n) where.push('3rd Prize');
      (d.starter || []).forEach(function (x) { if (x === n) where.push('Starter'); });
      (d.consolation || []).forEach(function (x) { if (x === n) where.push('Consolation'); });
      if (where.length) out.push({ draw: d.draw, date: d.date, where: where });
    });
    return out;
  }

  /* A random pick. Entertainment, and labelled as such where it is used — it is
   * not smarter than any other four digits. */
  function randomFourD() {
    var s = '';
    for (var i = 0; i < 4; i++) s += Math.floor(Math.random() * 10);
    return s;
  }

  return {
    allNumbers: allNumbers,
    topNumbers: topNumbers,
    digitFrequency: digitFrequency,
    numberTally: numberTally,
    drawsSince: drawsSince,
    appearances: appearances,
    randomFourD: randomFourD
  };
})();
