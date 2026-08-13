import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

import { buildSlide01 } from "./grid/slide-01.mjs";
import { buildSlide03 } from "./grid/slide-03.mjs";
import { buildSlide06 } from "./grid/slide-06.mjs";
import { buildSlide09 } from "./grid/slide-09.mjs";
import { buildSlide11 } from "./grid/slide-11.mjs";
import { buildSlide14 } from "./grid/slide-14.mjs";
import { buildSlide17 } from "./grid/slide-17.mjs";
import { buildSlide18 } from "./grid/slide-18.mjs";
import { buildSlide19 } from "./grid/slide-19.mjs";
import { buildSlide20 } from "./grid/slide-20.mjs";
import { buildSlide26 } from "./grid/slide-26.mjs";

const BUILD_DIR = "C:/Users/SJameel/Poission/.tmp/simulator_presentation";
const FINAL_PPTX = "C:/Users/SJameel/Poission/outputs/av_scenario_simulator_project_presentation.pptx";
const PLOT_PATH = "C:/Users/SJameel/Poission/version 6/plots/cumulative_episodes.png";
const FONT = "Helvetica Neue";
const INK = "#000000";
const MUTED = "#4B5563";
const PANEL = "#F2F2F2";
const RULE = "#B8BCC4";
const ACCENT = "#3D8DFF";
const ACCENT_LIGHT = "#D0EDFA";

function para(text, fontSize = 24, options = {}) {
  return {
    runs: [{
      run: text,
      textStyle: {
        fontSize: `${fontSize}px`,
        typeface: FONT,
        color: options.color || INK,
        bold: Boolean(options.bold),
      },
    }],
    spaceAfter: options.spaceAfter ?? 600,
    paragraphStyle: { lineSpacingPercent: options.lineSpacingPercent ?? 110000 },
  };
}

function title(text) {
  return para(text, 48, { bold: true, spaceAfter: 0, lineSpacingPercent: 90000 });
}

function pair(heading, body, bodySize = 22) {
  return {
    titleHere: para(heading, 26, { bold: true, color: ACCENT, spaceAfter: 600 }),
    loremIpsumDolorSitAmetConsecteturAdipiscing: para(body, bodySize, { spaceAfter: 0, lineSpacingPercent: 112000 }),
  };
}

function callout(heading, body) {
  return {
    titleHere: para(heading, 24, { bold: true, color: ACCENT, spaceAfter: 500 }),
    loremIpsumDolorSitAmetConsecteturAdipiscing: para(body, 20, { spaceAfter: 0, lineSpacingPercent: 110000 }),
  };
}

function notes(slide, sourceLines, presenterLines = []) {
  const content = [
    ...presenterLines,
    "",
    "[Sources]",
    ...sourceLines.map((line) => `- ${line}`),
  ].join("\n");
  slide.speakerNotes.textFrame.setText(content);
  slide.speakerNotes.setVisible(true);
}

async function imageBytes(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function styleTable(table, rows, columns) {
  table.borders.assign({ style: "solid", fill: RULE, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: rows, columnCount: columns }).assign({
    textStyle: { fontSize: 17, color: INK },
    margins: { left: 10, right: 10, top: 7, bottom: 7 },
    anchor: "middle",
  });
}

async function main() {
  await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
  await fs.mkdir(path.join(BUILD_DIR, "preview"), { recursive: true });

  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  // 1 — Cover
  {
    const slide = buildSlide01(presentation, {
      title: para("PROJECT EXPLAINER", 24, { bold: true, color: ACCENT }),
      title2: {
        runs: [{ run: "Autonomous-Vehicle\nScenario Simulator", textStyle: { fontSize: "80px", typeface: FONT, color: INK, bold: true } }],
        paragraphStyle: { lineSpacingPercent: 90000 },
      },
      title3: para("A reproducible, event-driven model of layered driving scenarios and exact rare-combination episodes", 28, { color: MUTED, lineSpacingPercent: 108000 }),
    });
    notes(slide, ["README.md", "DOCUMENTATION.md"], ["Open by framing the system as a joint-state simulator, not a conventional Poisson arrival generator."]);
  }

  // 2 — Core idea
  {
    const slide = buildSlide06(presentation, {
      title: title("Six concurrent layers form one evolving scenario"),
      body1: pair("Parallel state", "One active element per layer defines the current state."),
      body2: pair("Independent clocks", "Each element holds for a sampled Gamma duration."),
      body3: pair("Joint classification", "The full state is checked against exact rare-element rules."),
      footer1: "2",
    });
    notes(slide, ["simulator.py:42-52", "simulator.py:1118-1164"], ["The model is best understood as six asynchronous renewal processes whose current values form one scenario."]);
  }

  // 3 — Six layers
  {
    const slide = buildSlide03(presentation, {
      title: title("The six layers describe complementary context"),
      body1: "",
      footer1: "3",
    });
    const values = [
      ["01", "Street — persistent road and lane context"],
      ["02", "Temporal modifications — work zones and temporary traffic management"],
      ["03", "Ego maneuver — the autonomous vehicle's current maneuver class"],
      ["04", "Road-user maneuver — surrounding vehicle and road-user behavior"],
      ["05", "Environmental conditions — weather, visibility, and ambient context"],
      ["06", "Triggering conditions — unexpected conditions that can complete a rare scenario"],
    ];
    const table = slide.tables.items[0];
    for (let r = 0; r < values.length; r += 1) {
      for (let c = 0; c < 2; c += 1) table.cells.set(r, c, values[r][c]);
      table.getCell(r, 0).fill = r === 5 ? ACCENT_LIGHT : PANEL;
      table.getCell(r, 0).text.style = { fontSize: 20, bold: true, color: r === 5 ? ACCENT : INK };
      table.getCell(r, 1).text.style = { fontSize: 20, color: INK };
    }
    table.borders.assign({ style: "solid", fill: RULE, width: 1 });
    notes(slide, ["config.yaml:85-119", "simulator.py:42-52"], ["Emphasize that layers run simultaneously rather than as sequential processing stages."]);
  }

  // 4 — Generated population
  {
    const slide = buildSlide14(presentation, {
      title: title("Generated elements preserve the target class mix"),
      body1: {
        topic: para("CURRENT SEEDED CONFIGURATION", 20, { bold: true, color: ACCENT, spaceAfter: 350 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing: para("Largest-remainder allocation converts 70% common / 20% rare / 10% unknown targets into exact integer counts.", 19, { spaceAfter: 0 }),
      },
      body2: "",
      footer1: "4",
    });
    const values = [
      ["Layer", "Total", "Common", "Rare", "Unknown"],
      ["Street", "12", "9", "2", "1"],
      ["Temporal modifications", "45", "32", "9", "4"],
      ["Ego maneuver", "20", "14", "4", "2"],
      ["Road-user maneuver", "22", "16", "4", "2"],
      ["Environmental conditions", "22", "16", "4", "2"],
      ["Triggering conditions", "83", "58", "17", "8"],
      ["All layers", "204", "145", "40", "19"],
      ["Configured target", "100%", "70%", "20%", "10%"],
    ];
    const table = slide.tables.items[0];
    for (let r = 0; r < values.length; r += 1) {
      for (let c = 0; c < values[r].length; c += 1) table.cells.set(r, c, values[r][c]);
    }
    styleTable(table, 9, 5);
    for (let c = 0; c < 5; c += 1) {
      table.getCell(0, c).fill = INK;
      table.getCell(0, c).text.style = { fontSize: 17, bold: true, color: "#FFFFFF" };
      table.getCell(7, c).fill = ACCENT_LIGHT;
      table.getCell(7, c).text.style = { fontSize: 17, bold: true, color: INK };
      table.getCell(8, c).fill = PANEL;
      table.getCell(8, c).text.style = { fontSize: 17, bold: true, color: ACCENT };
    }
    notes(slide, ["config.yaml:45-119", "simulator.py:549-557", "simulator.py:703-749"], ["Counts shown are reproducible with the current element-count and rarity-assignment seeds."]);
  }

  // 5 — Probability mass
  {
    const slide = buildSlide19(presentation, {
      title: title("Selection mass is exact; time occupancy is not"),
      body1: {
        topic: para("TWO DIFFERENT PERCENTAGE CONTROLS", 20, { bold: true, color: ACCENT, spaceAfter: 350 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing: para("Element percentages set class counts. Selection percentages set total transition mass. A Dirichlet draw only redistributes probability within each class.", 20, { spaceAfter: 0 }),
      },
      stat1: para("70%", 46, { bold: true }),
      stat2: para("20%", 46, { bold: true }),
      stat3: para("10%", 46, { bold: true }),
      body2: para("common transition mass", 20, { color: MUTED }),
      body3: para("rare transition mass", 20, { color: MUTED }),
      body4: para("unknown transition mass", 20, { color: MUTED }),
      footer1: "5",
    });
    notes(slide, ["DOCUMENTATION.md:24-63", "simulator.py:718-735"], ["Selection share is not occupancy share because rarity classes have different duration distributions."]);
  }

  // 6 — Duration law
  {
    const slide = buildSlide20(presentation, {
      title: title("Gamma clocks vary by element"),
      body1: { titleGoesHere: para("Common", 25, { bold: true, color: ACCENT }), loremIpsumDolorSitAmetConsecteturAdipiscing: para("Longest band\n1.50× layer mean", 20) },
      body2: { titleGoesHere: para("Rare", 25, { bold: true, color: ACCENT }), loremIpsumDolorSitAmetConsecteturAdipiscing: para("Middle band\n0.75× layer mean", 20) },
      body3: { titleGoesHere: para("Unknown", 25, { bold: true, color: ACCENT }), loremIpsumDolorSitAmetConsecteturAdipiscing: para("Shortest band\n0.25× layer mean", 20) },
      footer1: "6",
    });
    const chart = slide.charts.items[0];
    chart.categories = ["Common", "Rare", "Unknown"];
    const minSeries = chart.series.getItemAt(0);
    minSeries.name = "Minimum mean";
    minSeries.categories = ["Common", "Rare", "Unknown"];
    minSeries.values = [405, 202.5, 75];
    minSeries.fill = ACCENT_LIGHT;
    const maxSeries = chart.series.getItemAt(1);
    maxSeries.name = "Maximum mean";
    maxSeries.categories = ["Common", "Rare", "Unknown"];
    maxSeries.values = [495, 247.5, 75];
    maxSeries.fill = ACCENT;
    chart.yAxis = {
      visible: true,
      max: 550,
      majorUnit: 100,
      title: { text: "Street mean duration (seconds)", textStyle: { fontSize: 14, fill: MUTED } },
      majorGridlines: { style: "solid", width: 1, fill: "#EDEDED" },
      line: { style: "solid", width: 0, fill: "#FFFFFF" },
      textStyle: { typeface: FONT, fontSize: 13, fill: MUTED },
    };
    chart.dataLabels = { showValue: true, position: "outEnd", textStyle: { fontSize: 12, fill: INK, bold: true } };
    notes(slide, ["config.yaml:67-79", "simulator.py:673-700"], ["The chart uses the street layer to make the configured non-overlapping mean bands concrete."]);
  }

  // 7 — Event loop
  {
    const slide = buildSlide18(presentation, {
      title: title("The engine jumps from one expiry to the next"),
      body1: pair("Initialize", "Select one element and sample one duration for all six layers.", 20),
      body2: pair("Advance", "Jump by the smallest remaining duration and derive mileage from elapsed time.", 20),
      body3: pair("Replace + classify", "Resample expired layers, then open, continue, or close the matching episode.", 20),
      label1: para("t = 0", 22, { bold: true }),
      label2: para("next expiry", 22, { bold: true }),
      label3: para("repeat", 22, { bold: true }),
      footer1: "7",
    });
    notes(slide, ["simulator.py:1167-1252", "simulator.py:1284-1462"], ["No fixed time step is used. Multiple layers expiring together are handled at the same event time."]);
  }

  // 8 — Exact combination rules
  {
    const slide = buildSlide09(presentation, {
      title: title("An unknown episode requires an exact rare set"),
      body1: {
        topic: para("EXAMPLE SELECTED C3 RULE", 20, { bold: true, color: ACCENT, spaceAfter: 400 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing: para("street_000 + temporal_001 + trigger_032", 27, { bold: true, spaceAfter: 350 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing2: para("The remaining three layers must all be common.", 20, { color: MUTED }),
      },
      body2: callout("Exact rare set", "No additional rare element may be active."),
      body3: callout("Trigger required", "Every C3–C6 rule includes a rare triggering condition."),
      body4: callout("Unknown disqualifies", "Any unknown-rarity element prevents a match."),
      footer1: "8",
    });
    notes(slide, ["config.yaml:81-91", "simulator.py:974-1039", "simulator.py:1150-1164"], ["The current configuration selects 40 C3, 30 C4, 20 C5, and 10 C6 rules without replacement."]);
  }

  // 9 — Semantic distinction
  {
    const slide = buildSlide11(presentation, {
      title: title("“Unknown” means two different things"),
      body1: {
        topic: para("THE DISTINCTION PREVENTS MISREADING THE RESULTS", 20, { bold: true, color: ACCENT, spaceAfter: 350 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing: para("Unknown-rarity elements participate in ordinary selection and duration statistics. Only exact rare combinations create reportable episodes.", 20, { spaceAfter: 0 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing2: para("", 18),
      },
      body2: para("Unknown-rarity element", 27, { bold: true }),
      body3: para("Unknown scenario episode", 27, { bold: true }),
      body4: {
        detailGoesHere: para("• One generated element class", 19),
        detailGoesHere2: para("• Has its own probability and Gamma law", 19),
        detailGoesHere3: para("• Does not open an episode", 19),
      },
      body5: {
        detailGoesHere: para("• One selected C3–C6 rare rule", 19),
        detailGoesHere2: para("• Starts when the full joint state matches", 19),
        detailGoesHere3: para("• Ends when that exact match breaks", 19),
      },
      footer1: "9",
    });
    notes(slide, ["README.md:44-57", "simulator.py:1045-1065", "simulator.py:1244-1251"], ["This is the most important semantic change in simulator version 6."]);
  }

  // 10 — Reproducibility
  {
    const slide = buildSlide19(presentation, {
      title: title("Seeds and boundary rules make runs repeatable"),
      body1: {
        topic: para("DESIGNED FOR CONTROLLED EXPERIMENTS", 20, { bold: true, color: ACCENT, spaceAfter: 350 }),
        loremIpsumDolorSitAmetConsecteturAdipiscing: para("Independent random streams isolate model decisions, while checkpointing preserves generator state for bit-identical resumed execution.", 20, { spaceAfter: 0 }),
      },
      stat1: para("20,000 h", 42, { bold: true }),
      stat2: para("7", 46, { bold: true }),
      stat3: para("0 s", 46, { bold: true }),
      body2: para("configured time horizon", 20, { color: MUTED }),
      body3: para("independent RNG streams", 20, { color: MUTED }),
      body4: para("intentional overshoot", 20, { color: MUTED }),
      footer1: "10",
    });
    notes(slide, ["config.yaml:9-27", "simulator.py:1121-1148", "simulator.py:1358-1377", "run_simulation.py:682-717"], ["At 50 mph, 20,000 simulated hours correspond to one million derived miles."]);
  }

  // 11 — Outputs with repository plot
  {
    const slide = presentation.slides.add();
    slide.background.fill = "#FFFFFF";
    const t = slide.shapes.add({ geometry: "textbox", name: "slide-11-title", position: { left: 41.33, top: 36.12, width: 1197.33, height: 72 }, fill: "none", line: { width: 0, fill: "none" } });
    t.text = "Outputs turn episodes into measurable evidence";
    t.text.style = { fontSize: 48, bold: true, color: INK, typeface: FONT };
    const body = slide.shapes.add({ geometry: "textbox", name: "slide-11-body", position: { left: 41.33, top: 170, width: 415, height: 400 }, fill: "none", line: { width: 0, fill: "none" } });
    body.text = "The runner produces:\n\n• episodes.csv — start, end, duration, inter-arrival\n• windows.csv — starts per complete mileage window\n• stats.json — rates, occupancy, composition, diagnostics\n• summary.md and plots — review-ready evidence\n\nCurrent seeded run: 495 episodes across 1,000,000 derived miles.";
    body.text.style = { fontSize: 22, color: INK, typeface: FONT };
    slide.shapes.add({ geometry: "rect", name: "plot-frame", position: { left: 500, top: 145, width: 739, height: 478 }, fill: "#FFFFFF", line: { style: "solid", fill: RULE, width: 1 } });
    slide.images.add({
      blob: await imageBytes(PLOT_PATH),
      contentType: "image/png",
      alt: "Cumulative unknown episodes over one million simulated miles",
      fit: "contain",
      position: { left: 512, top: 157, width: 715, height: 454 },
    });
    const footer = slide.shapes.add({ geometry: "textbox", name: "slide-11-footer", position: { left: 1184.18, top: 659.24, width: 54.48, height: 25.33 }, fill: "none", line: { width: 0, fill: "none" } });
    footer.text = "11";
    footer.text.style = { fontSize: 13.33, color: INK, alignment: "right", typeface: FONT };
    notes(slide, ["run_simulation.py:30-63", "run_simulation.py:336-382", "version 6/stats.json", "version 6/plots/cumulative_episodes.png"], ["The cumulative line is a realized output from the current seeded configuration, not a theoretical curve."]);
  }

  // 12 — Close
  {
    const slide = buildSlide26(presentation, {
      title: para("CORE TAKEAWAY", 24, { bold: true, color: ACCENT }),
      title2: {
        runs: [{ run: "A reproducible joint-state engine—\nnot a Poisson clock", textStyle: { fontSize: "72px", typeface: FONT, color: INK, bold: true } }],
        paragraphStyle: { lineSpacingPercent: 90000 },
      },
      title3: {
        loremIpsumDetails: para("Six asynchronous layers", 25, { bold: true }),
        loremIpsumDetails2: para("Element-specific Gamma sojourns", 25, { bold: true }),
        loremIpsumDetails3: para("Exact C3–C6 episode rules", 25, { bold: true }),
      },
    });
    notes(slide, ["DOCUMENTATION.md", "simulator.py:1-18"], ["Close by reinforcing the interpretation: Poisson-style statistics are outputs used for analysis, not the mechanism that drives the simulation."]);
  }

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await fs.writeFile(path.join(BUILD_DIR, "preview", `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(BUILD_DIR, "preview", `${stem}.layout.json`), await layout.text());
  }

  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await fs.writeFile(path.join(BUILD_DIR, "deck-montage.webp"), new Uint8Array(await montage.arrayBuffer()));
  const inspection = await presentation.inspect({ kind: "slide,textbox,shape,image,table,chart,notes", maxChars: 50000 });
  await fs.writeFile(path.join(BUILD_DIR, "deck.inspect.ndjson"), inspection.ndjson, "utf8");

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(FINAL_PPTX);
  console.log(FINAL_PPTX);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
