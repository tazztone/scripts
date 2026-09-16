const parsePrice = str => {
  if (!str) return 0;

  // Replace terminal dashes with .00 (e.g. 12.- -> 12.00)
  let clean = str.replace(/[.–\-]\s*$/g, '.00');

  // Remove spaces and apostrophes (always grouping separators) and extract valid chars
  clean = clean.replace(/[^\d,.]/g, '').replace(/['’\s]/g, '');

  const lastComma = clean.lastIndexOf(',');
  const lastDot = clean.lastIndexOf('.');

  const lastSeparator = Math.max(lastComma, lastDot);

  if (lastSeparator === -1) {
      return parseFloat(clean) || 0;
  }

  const digitsAfterSeparator = clean.length - lastSeparator - 1;

  if (digitsAfterSeparator === 3) {
      // It's a grouping separator (e.g., 1,385 or 1.385.900)
      clean = clean.replace(/[.,]/g, '');
  } else {
      // It's a decimal separator. Remove all separators before it, replace the last one with '.'
      const before = clean.substring(0, lastSeparator).replace(/[.,]/g, '');
      const after = clean.substring(lastSeparator + 1);
      clean = before + '.' + after;
  }

  return parseFloat(clean) || 0;
};

const tests = [
  ["1.385.90", 1385.90],
  ["1,385.90", 1385.90],
  ["1.385,90", 1385.90],
  ["1,385,900", 1385900],
  ["1.385.900", 1385900],
  ["1,385", 1385],
  ["1.385", 1385],
  ["1'385.90", 1385.90],
  ["CHF 1'433.00", 1433],
  ["12.-", 12],
  ["Gratis", 0]
];

tests.forEach(([input, expected]) => {
    const parsed = parsePrice(input);
    console.log(`Input: ${input.padEnd(15)} | Parsed: ${parsed} | Expected: ${expected} | ${parsed === expected ? 'PASS' : 'FAIL'}`);
});
