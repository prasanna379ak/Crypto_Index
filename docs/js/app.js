document.addEventListener("DOMContentLoaded", async () => {

  const container = document.getElementById("chart-container");
  let fullData = [];

  const chart = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: container.clientHeight - 40,
    layout: {
      background: { color: "transparent" },
      textColor: "#848e9c",
    },

    grid: {
      vertLines: { color: "rgba(255,255,255,0.04)" },
      horzLines: { color: "rgba(255,255,255,0.05)" },
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      borderVisible: false,
      tickMarkFormatter: (time) => {
        const d = new Date(time * 1000);
       return d.toUTCString().slice(5, 16); // "26 Jan 10:30"
      }
    },
    rightPriceScale: {
      scaleMargins: { top: 0.2, bottom: 0.2 },
    },
  });


  const series = chart.addSeries(LightweightCharts.AreaSeries, {
    lineColor: "#4fd1c5",
    topColor: "rgba(79,209,197,0.18)",
    bottomColor: "rgba(79,209,197,0.0)",
    lineWidth: 2,
  });

  new ResizeObserver(entries => {
    const r = entries[0].contentRect;
    chart.applyOptions({ width: r.width, height: r.height });
  }).observe(container);

  async function loadIndex() {
    const res = await fetch("./data/index_timeseries.json");
    const json = await res.json();

    fullData = json.data.map(p => ({
      time: Math.floor(new Date(p.time).getTime() / 1000),
      value: p.value,
    }));

    applyTimeframe("1m");

    document.getElementById("snapValue").innerText =
      fullData.at(-1).value.toFixed(2);

    document.getElementById("snapUpdated").innerText =
      "Updated · " + new Date(json.last_updated).toUTCString();
  }

  function applyTimeframe(range) {
    const now = Math.floor(Date.now() / 1000);
    let from;

    switch (range) {
      case "30m": from = now - 1800; break;
      case "4h": from = now - 14400; break;
      case "1d": from = now - 86400; break;
      case "1m": from = now - 2592000; break;
      case "3m": from = now - 7776000; break;
      case "1y": from = now - 31536000; break;
    }

    const filtered = fullData.filter(p => p.time >= from);
    series.setData(filtered);

    const first = filtered[0].value;
    const last = filtered.at(-1).value;
    updatePerformance(((last - first) / first) * 100, range);
  }

  function updatePerformance(pct, range) {
    const el = document.getElementById("pctChange");
    el.textContent = `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}% (${range.toUpperCase()})`;
    el.className = pct >= 0 ? "pct positive" : "pct negative";
  }

  document.querySelectorAll(".chart-filters span").forEach(btn => {
   btn.addEventListener("click", () => {

    // remove active from all
    document.querySelectorAll(".chart-filters span")
      .forEach(b => b.classList.remove("active"));

    // activate clicked one
    btn.classList.add("active");

    // update chart
    applyTimeframe(btn.dataset.range);
    });
  });


  async function loadConstituents() {
    const res = await fetch("./data/constituents.json");
    const json = await res.json();
    const tbody = document.getElementById("constituentsBody");
    tbody.innerHTML = "";

    json.constituents.forEach(c => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${c.symbol}</td><td>${(c.weight * 100).toFixed(2)}%</td>`;
      tbody.appendChild(tr);
    });
  }

  // ===== PIE LOGIC (FINAL) =====

  async function loadPie() {
    const res = await fetch("./data/constituents.json");
    const json = await res.json();

    const sorted = [...json.constituents]
      .sort((a, b) => b.market_cap - a.market_cap);

    const top3 = sorted.slice(0, 3);
    const others = sorted.slice(3);

    const othersCap = others.reduce((s, c) => s + c.market_cap, 0);

    const pieData = [
      ...top3.map(c => ({ label: c.symbol, market_cap: c.market_cap })),
      { label: "Others", market_cap: othersCap }
    ];

    renderPie(pieData);
  }

  function renderPie(data) {
    const size = 90;
    const r = size / 2;
    const colors = ["#49c9bc", "#4096ff", "#51379e", "#798342"];

    const total = data.reduce((s, d) => s + d.market_cap, 0);
    let angle = 0;

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${size} ${size}`);

    const legend = document.getElementById("pieLegend");
    legend.innerHTML = "";

    data.forEach((d, i) => {
      const slice = (d.market_cap / total) * Math.PI * 2;

      const x1 = r + r * Math.cos(angle);
      const y1 = r + r * Math.sin(angle);
      angle += slice;
      const x2 = r + r * Math.cos(angle);
      const y2 = r + r * Math.sin(angle);

      const large = slice > Math.PI ? 1 : 0;

      const path = document.createElementNS(svg.namespaceURI, "path");
      path.setAttribute(
        "d",
        `M ${r} ${r} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
      );

      path.setAttribute("fill", colors[i]);

      const title = document.createElementNS(svg.namespaceURI, "title");
      title.textContent = `${d.label}: $${d.market_cap.toLocaleString("en-US")}`;
      path.appendChild(title);

      svg.appendChild(path);

      const li = document.createElement("li");
      const dot = document.createElement("span");
      dot.className = "dot";
      dot.style.background = colors[i];

      li.appendChild(dot);
      li.appendChild(document.createTextNode(d.label));
      legend.appendChild(li);
    });

    const container = document.getElementById("pieChart");
    container.innerHTML = "";
    container.appendChild(svg);
  }

  await loadIndex();
  await loadConstituents();
  await loadPie();
});
