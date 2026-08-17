/* The hypercube in the header.

   Sixteen corners at every combination of plus and minus one, joined by
   thirty-two edges. Each corner turns in three planes of four-space. The
   result goes to three-space, and then to the screen. */

(function () {
  "use strict";

  var root = document.documentElement;

  var canvas = document.getElementById("tesseract");
  var ctx = canvas.getContext("2d");
  
  var D4 = 3.1;   // How far the camera stands along the w axis.
  var D3 = 4.4;   // How far the camera stands along the z axis.
  
  var corners = [];
  for (var i = 0; i < 16; i++) {
    corners.push([
      (i & 1) ? 1 : -1,
      (i & 2) ? 1 : -1,
      (i & 4) ? 1 : -1,
      (i & 8) ? 1 : -1
    ]);
  }
  
  // An edge joins two corners that differ in exactly one coordinate.
  var edges = [];
  for (var a = 0; a < 16; a++) {
    for (var bit = 0; bit < 4; bit++) {
      var b = a ^ (1 << bit);
      if (b > a) edges.push([a, b]);
    }
  }
  
  function turn(p, i, j, angle) {
    var c = Math.cos(angle), s = Math.sin(angle);
    var out = p.slice();
    out[i] = p[i] * c - p[j] * s;
    out[j] = p[i] * s + p[j] * c;
    return out;
  }
  
  function project(time) {
    var out = [];
    for (var n = 0; n < corners.length; n++) {
      var p = corners[n];
      p = turn(p, 0, 3, time * 0.00024);   // the x-w plane
      p = turn(p, 1, 2, time * 0.00015);   // the y-z plane
      p = turn(p, 0, 2, time * 0.00008);   // the x-z plane
  
      var w = 1 / (D4 - p[3]);             // four-space to three-space
      var d = 1 / (D3 - p[2] * w);         // three-space to the screen
      out.push({ x: p[0] * w * d, y: p[1] * w * d, near: w });
    }
    return out;
  }
  
  // Measure the widest reach once. After this the shape cannot clip.
  var reach = 0;
  for (var t = 0; t < 600000; t += 450) {
    var sample = project(t);
    for (var s = 0; s < sample.length; s++) {
      var r = Math.sqrt(sample[s].x * sample[s].x + sample[s].y * sample[s].y);
      if (r > reach) reach = r;
    }
  }
  reach *= 1.02;
  
  // The nearest and the furthest a corner can sit along the w axis.
  var far = 1 / (D4 + Math.SQRT2), close = 1 / (D4 - Math.SQRT2);
  
  function draw(time) {
    var size = canvas.clientWidth || 300;
    var dpr = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(size * dpr)) {
      canvas.width = canvas.height = Math.round(size * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);
  
    var style = getComputedStyle(root);
    var ink = style.getPropertyValue("--ink").trim();
    var accent = style.getPropertyValue("--accent-hi").trim();
  
    var scale = (size / 2 - 7) / reach;
    var pts = project(time);
    for (var n = 0; n < pts.length; n++) {
      pts[n].sx = size / 2 + pts[n].x * scale;
      pts[n].sy = size / 2 + pts[n].y * scale;
      pts[n].k = Math.max(0, Math.min(1, (pts[n].near - far) / (close - far)));
    }
  
    // The furthest edges go down first, so the nearest sit on top.
    var order = edges.slice().sort(function (e1, e2) {
      return (pts[e1[0]].k + pts[e1[1]].k) - (pts[e2[0]].k + pts[e2[1]].k);
    });
  
    ctx.lineCap = "round";
    for (var e = 0; e < order.length; e++) {
      var u = pts[order[e][0]], v = pts[order[e][1]];
      var k = (u.k + v.k) / 2;
      ctx.globalAlpha = 0.14 + k * 0.8;
      ctx.strokeStyle = k > 0.55 ? accent : ink;
      ctx.lineWidth = 0.8 + k * 1.2;
      ctx.beginPath();
      ctx.moveTo(u.sx, u.sy);
      ctx.lineTo(v.sx, v.sy);
      ctx.stroke();
    }
  
    for (var c = 0; c < pts.length; c++) {
      ctx.globalAlpha = 0.3 + pts[c].k * 0.65;
      ctx.fillStyle = pts[c].k > 0.55 ? accent : ink;
      ctx.beginPath();
      ctx.arc(pts[c].sx, pts[c].sy, 0.9 + pts[c].k * 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  
  var still = window.matchMedia("(prefers-reduced-motion: reduce)");
  function loop(t) { draw(t); if (!still.matches) requestAnimationFrame(loop); }
  if (still.matches) { draw(9000); } else { requestAnimationFrame(loop); }
  window.addEventListener("resize", function () { if (still.matches) draw(9000); });
})();
