// Build an Anki-style deck tree from flat decks whose names use "::" separators.
// Each node aggregates its own counts plus all descendants' counts (what the
// parent row displays).

const SEP = "::";

export function buildDeckTree(decks) {
  const byPath = {};
  const roots = [];

  // Sort so parents are created before children.
  const sorted = [...decks].sort((a, b) => a.name.localeCompare(b.name));

  for (const d of sorted) {
    const parts = d.name.split(SEP);
    let path = "";
    let parentChildren = roots;
    parts.forEach((part, i) => {
      path = i === 0 ? part : `${path}${SEP}${part}`;
      let node = byPath[path];
      if (!node) {
        node = { fullName: path, label: part, depth: i, children: [], deck: null };
        byPath[path] = node;
        parentChildren.push(node);
      }
      if (i === parts.length - 1) node.deck = d; // the real deck for this path
      parentChildren = node.children;
    });
  }

  // Aggregate counts bottom-up.
  function agg(node) {
    let n = node.deck?.new || 0;
    let l = node.deck?.learning || 0;
    let due = node.deck?.due || 0;
    for (const c of node.children) {
      const cc = agg(c);
      n += cc.new; l += cc.learning; due += cc.due;
    }
    node.counts = { new: n, learning: l, due };
    return node.counts;
  }
  roots.forEach(agg);
  return roots;
}
