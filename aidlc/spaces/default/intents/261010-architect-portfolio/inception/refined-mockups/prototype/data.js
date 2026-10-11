// Prototype content for the Refined Mockups R5 revision.
// Narrative copy is DRAFTED from each project's public README and live page and is not
// owner-approved (FR10.1). Risk's repository is private: nothing here is drawn from it,
// and its live URL is withheld (FR10.7, D-15, D-22). Monopoly and Risk titles are
// provisional pending a trademark and artwork review (FR10.6).
window.PORTFOLIO = (() => {
  "use strict";

  const categories = [
    { id: "games", name: "Games & AI Arenas", sub: "Play them, or watch the bots", icon: "i-gamepad",
      image: { src: "assets/draft/dice-hero.jpg", kind: "draft", alt: "" } },
    { id: "astronomy", name: "Astronomy & Exploration", sub: "Instruments for the night sky", icon: "i-telescope",
      image: { src: "assets/live/stars.jpg", kind: "live", alt: "" } },
    { id: "woodworking", name: "Woodworking", sub: "Drawings, builds, and shop work", icon: "i-hammer",
      image: { src: "assets/draft/cat-wood.jpg", kind: "draft", alt: "" } },
    { id: "software", name: "Software & Tools", sub: "Clone, build, or download", icon: "i-code",
      image: { src: "assets/draft/cat-code.jpg", kind: "draft", alt: "" } },
  ];

  // Badges are derived from access metadata only (FR4.10) — never typed freehand.
  function badges(p) {
    const out = [];
    if (p.access.liveUrl && p.access.requirement === "open") out.push({ text: "In browser", tone: "live" });
    if (!p.access.liveUrl && p.access.liveWithheld) out.push({ text: "Live link pending approval", tone: "pending" });
    if (p.access.phone === "desktop") out.push({ text: "Best on desktop", tone: "plain" });
    for (const r of p.repos) {
      if (r.visibility === "private") out.push({ text: "Source private", tone: "plain" });
      else if (r.licence) out.push({ text: `Open source · ${r.licence}`, tone: "plain" });
      else out.push({ text: "Source available", tone: "plain" });
    }
    return out;
  }

  const projects = [
    {
      slug: "stars", title: "STARS", category: "astronomy", featured: 1, provisional: false,
      icon: "i-star",
      meta: ["Astronomy", "3D", "Runs in your browser"],
      summary: "Fly through the real galaxy — 123,000 stars at their true 3D positions, with instruments no planetarium ships.",
      lead: { src: "assets/live/stars.jpg", kind: "live", pos: "50% 50%",
        alt: "STARS: a 3D atlas of real stars around the Sun, with Sirius, Procyon and Altair labelled" },
      access: { liveUrl: "https://stars.xaminisalamini.com/", requirement: "open", phone: "suitable" },
      repos: [{ visibility: "public", licence: null, url: "https://github.com/mbroadfo/stars" }],
      narrative: {
        inspiration: "Everyone builds maps; nobody builds instruments. STARS starts from that thesis: a navigable atlas of the real solar neighbourhood that lets you measure it, not only look at it.",
        challenges: "Rendering more than a hundred thousand real stars smoothly in a browser, and keeping the data honest: real data is rendered as real, and anything procedural is labelled.",
        decisions: "A Python pipeline packs the AT-HYG catalogue into a compact binary star buffer. A Vite, React and Three.js viewer flies through it with SketchUp-style orbit, pan and zoom, in a galactic frame with the Sun at the origin and one unit per light-year.",
        implementation: "Measurement tethers give the true 3D separation of any two stars; closure rates come from real velocity vectors; relativistic mission briefs give ship time, Earth time and peak γ at constant 1 g; intercept navigation aims where a star will be; deep-time scrubbing runs ±100,000 years. It ships as a static site built by GitHub Actions.",
        outcomes: "Live in the browser, showing 123,018 catalogue stars and 145,128 far-field stars.",
        lessons: "",
      },
      gallery: [
        { src: "assets/live/stars.jpg", kind: "live", alt: "The atlas centred on the Sun, with nearby stars and constellation lines labelled", caption: "The solar neighbourhood, one unit per light-year" },
        { src: "assets/live/stars-controls.jpg", kind: "live", alt: "STARS instrument panels: view, visibility, time, travel-time view, infection lab, universes and radiosphere", caption: "The instrument panels" },
        { src: "assets/live/stars-phone.jpg", kind: "live", alt: "STARS running on a phone-sized screen", caption: "On a phone", pos: "50% 0%" },
      ],
      files: [],
    },
    {
      slug: "baduk", title: "Baduk", category: "games", featured: 2, provisional: false,
      icon: "i-stones",
      meta: ["Go", "AI coach", "Runs in your browser"],
      summary: "Learn Go by playing it — four bots with distinct personalities, and a coach that explains every move.",
      lead: { src: "assets/live/baduk-board.jpg", kind: "live", pos: "50% 40%",
        alt: "A 9×9 Go game in progress between two bots" },
      access: { liveUrl: "https://baduk.xaminisalamini.com/", requirement: "open", phone: "suitable" },
      repos: [{ visibility: "public", licence: "MIT", url: "https://github.com/mbroadfo/baduk" }],
      narrative: {
        inspiration: "A superhuman opponent teaches a beginner almost nothing. Baduk is a place where someone who has never played can sit down, understand what is happening, and enjoy it.",
        challenges: "Making bot strength honest. Levels are measured in bot-versus-bot arenas rather than guessed, and nothing claims a calibrated human rank.",
        decisions: "The bots and the coach reason from the same evaluator, so the advice a learner reads is the reasoning the opponent actually used. Facts about the position are kept apart from opinions about what to play. It is a static build with no backend; bots run in a Web Worker.",
        implementation: "A rules engine with ko and superko, area and territory scoring, handicap and SGF; four opponents from random play to Monte Carlo tree search; graduated hints; a 15-concept curriculum and post-game review; 170 tests.",
        outcomes: "Measured on 9×9: Sprout beats Pebble 9–0, Kaze beats Sprout 9–3, and Tenuki beats Kaze 5–3 at 600 ms of thinking time.",
        lessons: "Learners bond with characters more readily than with a difficulty slider, so each opponent has a name, a face and an honest blind spot.",
      },
      gallery: [
        { src: "assets/live/baduk.jpg", kind: "live", alt: "A bot-versus-bot Go game with the move log explaining each move", caption: "Every move comes with its reasoning" },
        { src: "assets/live/baduk-lessons.jpg", kind: "live", alt: "The Baduk game panel with opponents, settings and the lessons list beside an empty board", caption: "Opponents, settings and lessons" },
        { src: "assets/live/baduk-phone.jpg", kind: "live", alt: "Baduk running on a phone-sized screen", caption: "On a phone", pos: "50% 0%" },
      ],
      files: [],
    },
    {
      slug: "monopoly-arena", title: "Monopoly Arena", category: "games", featured: 3, provisional: true,
      icon: "i-dice",
      meta: ["AI bots", "Simulation", "Runs in your browser"],
      summary: "A full rules engine and animated board for pitting AI strategies against each other — or training new ones.",
      lead: { src: "assets/draft/dice-hero.jpg", kind: "draft", pos: "30% 50%",
        alt: "Two dice on a green gaming table" },
      access: { liveUrl: "https://arena.xaminisalamini.com/", requirement: "open", phone: "desktop" },
      repos: [{ visibility: "public", licence: null, url: "https://github.com/mbroadfo/monopoly-arena" }],
      narrative: {
        inspiration: "Finding the strongest strategies by pitting AI bots against each other — or against you.",
        challenges: "",
        decisions: "Two packages with one hard boundary: a UI-free rules engine and a web app that treats it as a black box. Bots are pure functions of the game state, and every random outcome goes through an injectable random-number generator, so the same seed always replays the same game.",
        implementation: "The full ruleset — buying, auctions, trading, building, mortgages, jail and bankruptcy — with four reference bots, live bankroll and log panels, a scrubbable turn-by-turn timeline, and a training mode that evolves bots across eight games at once.",
        outcomes: "",
        lessons: "",
      },
      gallery: [],
      galleryNote: "Screenshots are withheld until the trademark and artwork review is complete (FR10.6).",
      files: [],
    },
    {
      slug: "risk", title: "Risk", category: "games", featured: 0, provisional: true,
      icon: "i-flag",
      meta: [],
      summary: "",
      lead: null,
      access: { liveUrl: null, liveWithheld: true, requirement: "open", phone: "desktop" },
      repos: [{ visibility: "private", licence: null, url: null }],
      narrative: {},
      gallery: [],
      files: [],
      pending: true, // not published: content, rights, URL and publication approvals outstanding
    },
  ];

  const narrativeOrder = [
    ["inspiration", "Inspiration"],
    ["challenges", "Design challenges"],
    ["decisions", "Architectural decisions"],
    ["implementation", "Implementation"],
    ["outcomes", "Outcomes"],
    ["lessons", "Lessons learned"],
  ];

  const byCategory = (id) => projects.filter((p) => p.category === id);
  return { categories, projects, badges, narrativeOrder, byCategory,
    find: (slug) => projects.find((p) => p.slug === slug),
    cat: (id) => categories.find((c) => c.id === id) };
})();
