const fs = require('fs');
const path = require('path');

// Minimal PDF file header (PDF 1.4)
const minimalPdf = Buffer.from(
  '%PDF-1.4\n' +
  '1 0 obj\n' +
  '<<\n' +
  '/Type /Catalog\n' +
  '/Pages 2 0 R\n' +
  '>>\n' +
  'endobj\n' +
  '2 0 obj\n' +
  '<<\n' +
  '/Type /Pages\n' +
  '/Kids [3 0 R]\n' +
  '/Count 1\n' +
  '>>\n' +
  'endobj\n' +
  '3 0 obj\n' +
  '<<\n' +
  '/Type /Page\n' +
  '/Parent 2 0 R\n' +
  '/MediaBox [0 0 612 792]\n' +
  '/Contents 4 0 R\n' +
  '>>\n' +
  'endobj\n' +
  '4 0 obj\n' +
  '<<\n' +
  '/Length 44\n' +
  '>>\n' +
  'stream\n' +
  'BT\n' +
  '/F1 12 Tf\n' +
  '50 700 Td\n' +
  '(Sample Proposal) Tj\n' +
  'ET\n' +
  'endstream\n' +
  'endobj\n' +
  'xref\n' +
  '0 5\n' +
  '0000000000 65535 f\n' +
  '0000000009 00000 n\n' +
  '0000000058 00000 n\n' +
  '0000000115 00000 n\n' +
  '0000000202 00000 n\n' +
  'trailer\n' +
  '<<\n' +
  '/Size 5\n' +
  '/Root 1 0 R\n' +
  '>>\n' +
  'startxref\n' +
  '299\n' +
  '%%EOF\n'
);

const outputPath = path.join(__dirname, '../tests/fixtures/commands/input-valid/sample.pdf');
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, minimalPdf);
console.log(`Created test PDF: ${outputPath}`);
